"""Test strumenti CrewAI — mock DB sessions per test isolati."""
import pytest
from unittest.mock import MagicMock, patch


# Helper: crea uno strumento con session mock iniettata
def make_tool_with_mock_session(tool_class, session_mock, db_url="postgresql+asyncpg://test:test@localhost/test"):
    """Crea un'istanza tool con _make_sync_session mockato."""
    tool = tool_class(database_url=db_url)
    return tool, session_mock


class TestCercaSoggetti:
    """Test per CercaSoggetti tool."""

    def test_cerca_soggetti_per_tipo(self):
        """Verifica che il filtro per tipo funzioni."""
        from tiro_core.intelligenza.strumenti import CercaSoggetti
        from tiro_core.modelli.core import Soggetto

        mock_soggetto = MagicMock(spec=Soggetto)
        mock_soggetto.id = 1
        mock_soggetto.nome = "Mario"
        mock_soggetto.cognome = "Rossi"
        mock_soggetto.tipo = "esterno"
        mock_soggetto.email = ["mario@test.com"]
        mock_soggetto.tag = ["cliente"]

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_soggetto]

        tool = CercaSoggetti(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(tipo="esterno")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["tipo"] == "esterno"
        assert result[0]["nome"] == "Mario Rossi"

    def test_cerca_soggetti_lista_vuota(self):
        """Senza soggetti restituisce lista vuota."""
        from tiro_core.intelligenza.strumenti import CercaSoggetti

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        tool = CercaSoggetti(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run()

        assert result == []

    def test_cerca_soggetti_session_chiusa(self):
        """La sessione viene sempre chiusa dopo il run."""
        from tiro_core.intelligenza.strumenti import CercaSoggetti

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        tool = CercaSoggetti(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            tool._run()

        mock_session.close.assert_called_once()


class TestCercaFlussi:
    """Test per CercaFlussi tool."""

    def test_cerca_flussi_per_soggetto(self):
        """Verifica il filtro per soggetto_id."""
        from tiro_core.intelligenza.strumenti import CercaFlussi
        from tiro_core.modelli.core import Flusso
        from datetime import datetime, timezone

        mock_flusso = MagicMock(spec=Flusso)
        mock_flusso.id = 10
        mock_flusso.soggetto_id = 5
        mock_flusso.canale = "posta"
        mock_flusso.oggetto = "Test email"
        mock_flusso.ricevuto_il = datetime(2026, 4, 6, tzinfo=timezone.utc)
        mock_flusso.contenuto = "Contenuto di prova per il test"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_flusso]

        tool = CercaFlussi(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(soggetto_id=5)

        assert len(result) == 1
        assert result[0]["soggetto_id"] == 5
        assert result[0]["canale"] == "posta"


class TestCercaOpportunita:
    """Test per CercaOpportunita tool."""

    def test_cerca_opportunita_per_fase(self):
        """Verifica filtro per fase pipeline."""
        from tiro_core.intelligenza.strumenti import CercaOpportunita
        from tiro_core.modelli.commerciale import Opportunita

        mock_opp = MagicMock(spec=Opportunita)
        mock_opp.id = 3
        mock_opp.titolo = "Progetto Alpha"
        mock_opp.fase = "proposta"
        mock_opp.valore_eur = 15000.0
        mock_opp.probabilita = 0.6
        mock_opp.ente_id = 2
        mock_opp.soggetto_id = 1

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_opp]

        tool = CercaOpportunita(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(fase="proposta")

        assert len(result) == 1
        assert result[0]["fase"] == "proposta"
        assert result[0]["valore_eur"] == 15000.0


class TestLeggiFascicolo:
    """Test per LeggiFascicolo tool."""

    def test_leggi_fascicolo_trovato(self):
        """Ritorna dizionario con dati fascicolo."""
        from tiro_core.intelligenza.strumenti import LeggiFascicolo
        from tiro_core.modelli.commerciale import Fascicolo

        mock_fascicolo = MagicMock(spec=Fascicolo)
        mock_fascicolo.id = 7
        mock_fascicolo.soggetto_id = 1
        mock_fascicolo.sintesi = "Sintesi di prova"
        mock_fascicolo.indice_rischio = 0.3
        mock_fascicolo.indice_opportunita = 0.7
        mock_fascicolo.sezioni = {"anagrafica": "## Anagrafica..."}

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_fascicolo

        tool = LeggiFascicolo(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(soggetto_id=1)

        assert result is not None
        assert result["sintesi"] == "Sintesi di prova"
        assert result["indice_rischio"] == 0.3

    def test_leggi_fascicolo_non_trovato(self):
        """Ritorna None se fascicolo non esiste."""
        from tiro_core.intelligenza.strumenti import LeggiFascicolo

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        tool = LeggiFascicolo(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(soggetto_id=999)

        assert result is None


class TestCreaProposta:
    """Test per CreaProposta tool."""

    def test_crea_proposta_successo(self):
        """Proposta creata correttamente."""
        from tiro_core.intelligenza.strumenti import CreaProposta
        from tiro_core.modelli.decisionale import Proposta

        mock_proposta = MagicMock(spec=Proposta)
        mock_proposta.id = 42
        mock_proposta.stato = "in_attesa"

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()

        def side_effect_refresh(obj):
            obj.id = 42
            obj.stato = "in_attesa"

        mock_session.refresh.side_effect = side_effect_refresh

        tool = CreaProposta(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            result = tool._run(
                ruolo_agente="tecnologia",
                tipo_azione="crea_task_interna",
                titolo="Analisi tecnica Q2",
                descrizione="Analisi completa del mercato tech",
                livello_rischio="basso",
            )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result["tipo_azione"] == "crea_task_interna"
        assert result["livello_rischio"] == "basso"

    def test_crea_proposta_rollback_su_errore(self):
        """In caso di errore viene fatto rollback."""
        from tiro_core.intelligenza.strumenti import CreaProposta

        mock_session = MagicMock()
        mock_session.commit.side_effect = RuntimeError("DB error")

        tool = CreaProposta(database_url="postgresql+asyncpg://test:test@localhost/test")
        with patch("tiro_core.intelligenza.strumenti._make_sync_session", return_value=mock_session):
            with pytest.raises(RuntimeError):
                tool._run(
                    ruolo_agente="tecnologia",
                    tipo_azione="crea_task_interna",
                    titolo="Test errore",
                )

        mock_session.rollback.assert_called_once()
