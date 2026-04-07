"""Test generazione fascicoli — logica deterministica, LLM solo per sintesi."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.modelli.core import Soggetto, Flusso
from tiro_core.modelli.commerciale import Ente, Opportunita, Fascicolo


class TestRaccogliDatiFascicolo:
    """Test raccolta dati SQL per fascicolo."""

    @pytest.mark.asyncio
    async def test_raccolta_soggetto_con_flussi(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Luca", cognome="Verdi",
            email=["luca@test.com"], telefono=[], tag=["vip"], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        for i in range(3):
            db_session.add(Flusso(
                soggetto_id=soggetto.id, canale="posta", direzione="entrata",
                oggetto=f"Oggetto {i}", contenuto=f"Contenuto {i}",
                dati_grezzi={"classificazione": {"intent": "richiesta_info"}},
                ricevuto_il=now - timedelta(days=i),
            ))
        await db_session.flush()

        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=soggetto.id)

        assert dati.soggetto_nome == "Luca Verdi"
        assert len(dati.flussi_recenti) == 3
        assert dati.totale_flussi == 3

    @pytest.mark.asyncio
    async def test_raccolta_con_opportunita(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Anna", cognome="Bianchi",
            email=["anna@test.com"], telefono=[], tag=[], profilo={},
        )
        ente = Ente(nome="Beta Srl", profilo={})
        db_session.add(soggetto)
        db_session.add(ente)
        await db_session.flush()

        db_session.add(Opportunita(
            ente_id=ente.id, soggetto_id=soggetto.id,
            titolo="Deal Beta", fase="trattativa",
            valore_eur=25000.0, probabilita=0.6, dettagli={},
        ))
        await db_session.flush()

        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=soggetto.id)

        assert len(dati.opportunita) == 1
        assert dati.opportunita[0]["valore_eur"] == 25000.0

    @pytest.mark.asyncio
    async def test_raccolta_soggetto_inesistente(self, db_session):
        from tiro_core.intelligenza.fascicolo_builder import raccogli_dati_fascicolo
        dati = await raccogli_dati_fascicolo(db_session, soggetto_id=99999)
        assert dati is None


class TestGeneraSezioniMarkdown:
    """Test generazione sezioni Markdown deterministiche."""

    def test_sezioni_con_dati_completi(self):
        from tiro_core.intelligenza.fascicolo_builder import (
            DatiFascicolo, genera_sezioni_markdown,
        )
        dati = DatiFascicolo(
            soggetto_id=1,
            soggetto_nome="Mario Rossi",
            soggetto_tipo="esterno",
            soggetto_email=["mario@test.com"],
            soggetto_telefono=["+393331234567"],
            soggetto_tag=["vip", "partner"],
            totale_flussi=15,
            flussi_recenti=[
                {"canale": "posta", "oggetto": "Richiesta info", "data": "2026-04-01"},
                {"canale": "messaggio", "oggetto": None, "data": "2026-04-02"},
            ],
            opportunita=[
                {"titolo": "Deal Alpha", "fase": "proposta", "valore_eur": 10000.0},
            ],
            ente_nome="Alpha Srl",
            indice_rischio=0.3,
            indice_opportunita=0.7,
        )
        sezioni = genera_sezioni_markdown(dati)

        assert "anagrafica" in sezioni
        assert "Mario Rossi" in sezioni["anagrafica"]
        assert "flussi" in sezioni
        assert "opportunita" in sezioni
        assert "Deal Alpha" in sezioni["opportunita"]
        assert "indici" in sezioni

    def test_sezioni_senza_opportunita(self):
        from tiro_core.intelligenza.fascicolo_builder import (
            DatiFascicolo, genera_sezioni_markdown,
        )
        dati = DatiFascicolo(
            soggetto_id=2,
            soggetto_nome="Vuoto Test",
            soggetto_tipo="membro",
            soggetto_email=[],
            soggetto_telefono=[],
            soggetto_tag=[],
            totale_flussi=0,
            flussi_recenti=[],
            opportunita=[],
            ente_nome=None,
            indice_rischio=0.0,
            indice_opportunita=0.0,
        )
        sezioni = genera_sezioni_markdown(dati)

        assert "anagrafica" in sezioni
        assert "Nessuna opportunita" in sezioni["opportunita"]


class TestGeneraFascicolo:
    """Test generazione completa fascicolo con LLM mock."""

    @pytest.mark.asyncio
    async def test_genera_fascicolo_completo(self, db_session):
        soggetto = Soggetto(
            tipo="esterno", nome="Test", cognome="Fascicolo",
            email=["test@fasc.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="posta", direzione="entrata",
            contenuto="Test contenuto", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        mock_sintesi = AsyncMock(return_value="Sintesi generata dal mock LLM.")

        from tiro_core.intelligenza.fascicolo_builder import genera_fascicolo
        with patch(
            "tiro_core.intelligenza.fascicolo_builder.genera_sintesi_llm",
            mock_sintesi,
        ):
            fascicolo = await genera_fascicolo(db_session, soggetto_id=soggetto.id)

        assert fascicolo is not None
        assert fascicolo.soggetto_id == soggetto.id
        assert fascicolo.sintesi == "Sintesi generata dal mock LLM."
        assert fascicolo.indice_rischio is not None
        assert fascicolo.indice_opportunita is not None
        assert "anagrafica" in fascicolo.sezioni

    @pytest.mark.asyncio
    async def test_genera_fascicolo_senza_llm_fallback(self, db_session):
        """Se LLM fallisce, sintesi = concatenazione sezioni."""
        soggetto = Soggetto(
            tipo="esterno", nome="Fallback", cognome="Test",
            email=["fall@test.com"], telefono=[], tag=[], profilo={},
        )
        db_session.add(soggetto)
        await db_session.flush()

        db_session.add(Flusso(
            soggetto_id=soggetto.id, canale="messaggio", direzione="entrata",
            contenuto="Ciao", dati_grezzi={},
            ricevuto_il=datetime.now(timezone.utc),
        ))
        await db_session.flush()

        mock_sintesi = AsyncMock(side_effect=Exception("LLM non disponibile"))

        from tiro_core.intelligenza.fascicolo_builder import genera_fascicolo
        with patch(
            "tiro_core.intelligenza.fascicolo_builder.genera_sintesi_llm",
            mock_sintesi,
        ):
            fascicolo = await genera_fascicolo(db_session, soggetto_id=soggetto.id)

        assert fascicolo is not None
        assert fascicolo.sintesi is not None  # fallback deterministico
        assert len(fascicolo.sintesi) > 0
