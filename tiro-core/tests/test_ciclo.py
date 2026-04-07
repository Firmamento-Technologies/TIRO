"""Test ciclo agentico 4 fasi — mock Crew.kickoff() e agenti."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def make_mock_agenti():
    """Crea un dizionario di agenti mock."""
    return {
        ruolo: MagicMock(name=f"agente_{ruolo}")
        for ruolo in ("direzione", "tecnologia", "mercato", "finanza", "risorse")
    }


def make_crew_output(raw_text: str) -> MagicMock:
    """Crea un mock CrewOutput."""
    mock = MagicMock()
    mock.raw = raw_text
    mock.tasks_output = []
    return mock


class TestEseguiCiclo:
    """Test per esegui_ciclo."""

    @pytest.mark.asyncio
    async def test_ciclo_completo_4_fasi(self, db_session):
        """Il ciclo completo esegue tutte e 4 le fasi."""
        from tiro_core.intelligenza.ciclo import esegui_ciclo
        from tiro_core.modelli.sistema import Configurazione, RegolaRischio

        # Seed config rischio necessaria per _estrai_e_crea_proposte
        db_session.add(RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        ))
        await db_session.flush()

        agenti = make_mock_agenti()
        crew_calls = []

        # Output predefiniti per ogni fase
        outputs = [
            make_crew_output("Priorità: 1. Crescita commerciale — Alta"),
            make_crew_output("Tech: focus su AI pipeline"),
            make_crew_output("## Proposte di Azione\n- Aggiorna fascicoli clienti key\n\n## Conflitti\nNessuno"),
            make_crew_output("Risorse: assumere 1 backend developer"),
        ]
        output_iter = iter(outputs)

        def mock_kickoff(self_crew=None, inputs=None, input_files=None):
            return next(output_iter)

        mock_task = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.side_effect = lambda **kw: next(output_iter) if False else mock_kickoff()

        # Counter per kickoff calls
        kickoff_count = [0]
        fixed_outputs = [
            make_crew_output("Priorità strategiche"),
            make_crew_output("Analisi dipartimenti"),
            make_crew_output("## Proposte di Azione\n- Migliora pipeline\n\n## Conflitti"),
            make_crew_output("Piano risorse umane"),
        ]

        def make_crew_factory(*args, **kwargs):
            mock = MagicMock()
            idx = kickoff_count[0]
            out = fixed_outputs[min(idx, len(fixed_outputs) - 1)]
            kickoff_count[0] += 1
            mock.kickoff.return_value = out
            return mock

        with patch("tiro_core.intelligenza.ciclo.Crew", side_effect=make_crew_factory), \
             patch("tiro_core.intelligenza.ciclo.Task", return_value=MagicMock()):
            result = await esegui_ciclo(
                session=db_session,
                agenti=agenti,
                contesto_aziendale="Test aziendale",
            )

        assert "ciclo" in result
        assert "sessione_id" in result
        assert "output_fase1" in result
        assert "output_fase2" in result
        assert "output_fase3" in result
        assert "output_fase4" in result
        assert result["ciclo"] >= 1

    @pytest.mark.asyncio
    async def test_sessione_decisionale_salvata(self, db_session):
        """La sessione decisionale viene salvata nel DB."""
        from tiro_core.intelligenza.ciclo import esegui_ciclo
        from tiro_core.modelli.decisionale import SessioneDecisionale
        from tiro_core.modelli.sistema import RegolaRischio
        from sqlalchemy import select

        db_session.add(RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        ))
        await db_session.flush()

        agenti = make_mock_agenti()
        kickoff_count = [0]
        outputs = [
            make_crew_output("Output fase 1"),
            make_crew_output("Output fase 2"),
            make_crew_output("Deliberazione finale"),
            make_crew_output("Output fase 4"),
        ]

        def make_crew_factory(*args, **kwargs):
            mock = MagicMock()
            idx = kickoff_count[0]
            out = outputs[min(idx, len(outputs) - 1)]
            kickoff_count[0] += 1
            mock.kickoff.return_value = out
            return mock

        with patch("tiro_core.intelligenza.ciclo.Crew", side_effect=make_crew_factory), \
             patch("tiro_core.intelligenza.ciclo.Task", return_value=MagicMock()):
            result = await esegui_ciclo(session=db_session, agenti=agenti)

        # Verifica che la sessione esista nel DB
        sessione_id = result["sessione_id"]
        res = await db_session.execute(
            select(SessioneDecisionale).where(SessioneDecisionale.id == sessione_id)
        )
        sessione = res.scalar_one_or_none()
        assert sessione is not None
        assert len(sessione.partecipanti) == 5
        assert "deliberazione" in sessione.consenso

    @pytest.mark.asyncio
    async def test_crew_chiamata_4_volte(self, db_session):
        """Crew viene istanziata 4 volte (una per fase)."""
        from tiro_core.intelligenza.ciclo import esegui_ciclo
        from tiro_core.modelli.sistema import RegolaRischio

        db_session.add(RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        ))
        await db_session.flush()

        agenti = make_mock_agenti()
        crew_instances = []
        call_count = [0]

        def make_crew_factory(*args, **kwargs):
            mock = MagicMock()
            mock.kickoff.return_value = make_crew_output(f"Output fase {len(crew_instances) + 1}")
            crew_instances.append(mock)
            return mock

        with patch("tiro_core.intelligenza.ciclo.Crew", side_effect=make_crew_factory), \
             patch("tiro_core.intelligenza.ciclo.Task", return_value=MagicMock()):
            await esegui_ciclo(session=db_session, agenti=agenti)

        assert len(crew_instances) == 4

    @pytest.mark.asyncio
    async def test_proposte_create_da_deliberazione(self, db_session):
        """Le proposte vengono create dal testo di deliberazione."""
        from tiro_core.intelligenza.ciclo import esegui_ciclo
        from tiro_core.modelli.decisionale import Proposta
        from tiro_core.modelli.sistema import RegolaRischio
        from sqlalchemy import select

        db_session.add(RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        ))
        await db_session.flush()

        agenti = make_mock_agenti()
        call_count = [0]
        # Fase 3 ha una proposta nella deliberazione
        outputs_map = {
            0: "Priorità stabilite",
            1: "Analisi completata",
            2: "## Proposte di Azione\n- Aggiorna fascicolo clienti principali\n\n## Altro",
            3: "Piano HR definito",
        }

        def make_crew_factory(*args, **kwargs):
            mock = MagicMock()
            idx = call_count[0]
            mock.kickoff.return_value = make_crew_output(outputs_map.get(idx, "Output"))
            call_count[0] += 1
            return mock

        with patch("tiro_core.intelligenza.ciclo.Crew", side_effect=make_crew_factory), \
             patch("tiro_core.intelligenza.ciclo.Task", return_value=MagicMock()):
            result = await esegui_ciclo(session=db_session, agenti=agenti)

        # Deve aver creato almeno 1 proposta
        res = await db_session.execute(select(Proposta))
        proposte = res.scalars().all()
        assert len(proposte) >= 1
        assert len(result["proposte_ids"]) >= 1


class TestCreaTaskFasi:
    """Test per le funzioni di creazione task."""

    def test_crea_task_direzione_async_false(self):
        """Il task direzione e sincrono (async_execution=False)."""
        from tiro_core.intelligenza.ciclo import _crea_task_direzione

        agente_mock = MagicMock()
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_direzione(agente_mock, "contesto test")

        assert captured.get("async_execution") is False

    def test_crea_task_tecnologia_async_true(self):
        """Il task tecnologia è parallelo (async_execution=True)."""
        from tiro_core.intelligenza.ciclo import _crea_task_tecnologia

        agente_mock = MagicMock()
        task_dir_mock = MagicMock()
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_tecnologia(agente_mock, task_dir_mock)

        assert captured.get("async_execution") is True

    def test_crea_task_mercato_async_true(self):
        """Il task mercato è parallelo."""
        from tiro_core.intelligenza.ciclo import _crea_task_mercato

        agente_mock = MagicMock()
        task_dir_mock = MagicMock()
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_mercato(agente_mock, task_dir_mock)

        assert captured.get("async_execution") is True

    def test_crea_task_finanza_async_true(self):
        """Il task finanza è parallelo."""
        from tiro_core.intelligenza.ciclo import _crea_task_finanza

        agente_mock = MagicMock()
        task_dir_mock = MagicMock()
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_finanza(agente_mock, task_dir_mock)

        assert captured.get("async_execution") is True

    def test_crea_task_deliberazione_ha_contesto_4_task(self):
        """Il task deliberazione ha contesto da tutte e 4 le fasi."""
        from tiro_core.intelligenza.ciclo import _crea_task_deliberazione

        agente_mock = MagicMock()
        task_mocks = [MagicMock() for _ in range(4)]
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_deliberazione(agente_mock, *task_mocks)

        assert len(captured.get("context", [])) == 4

    def test_crea_task_risorse_sequenziale(self):
        """Il task risorse è sequenziale."""
        from tiro_core.intelligenza.ciclo import _crea_task_risorse

        agente_mock = MagicMock()
        task_delib_mock = MagicMock()
        captured = {}

        with patch("tiro_core.intelligenza.ciclo.Task", side_effect=lambda **kw: captured.update(kw) or MagicMock()):
            _crea_task_risorse(agente_mock, task_delib_mock)

        assert captured.get("async_execution") is False


class TestEstraiECreaProposte:
    """Test per _estrai_e_crea_proposte."""

    @pytest.mark.asyncio
    async def test_estrai_proposte_da_deliberazione(self, db_session):
        """Estrae proposte dal testo di deliberazione."""
        from tiro_core.intelligenza.ciclo import _estrai_e_crea_proposte
        from tiro_core.modelli.sistema import RegolaRischio
        from tiro_core.modelli.decisionale import Proposta
        from sqlalchemy import select

        db_session.add(RegolaRischio(
            pattern_azione="aggiorna_fascicolo",
            livello_rischio="basso",
            descrizione="Test",
            approvazione_automatica=True,
        ))
        await db_session.flush()

        agenti = make_mock_agenti()
        testo = (
            "## Proposte di Azione\n"
            "- Pianifica riunione con clienti key\n"
            "- Aggiorna pipeline commerciale\n"
            "\n## Conflitti\n"
            "Nessuno."
        )

        proposte = await _estrai_e_crea_proposte(
            session=db_session,
            agenti=agenti,
            testo_deliberazione=testo,
        )

        assert len(proposte) == 2

    @pytest.mark.asyncio
    async def test_deliberazione_senza_sezione_proposte(self, db_session):
        """Senza sezione proposte non crea nulla."""
        from tiro_core.intelligenza.ciclo import _estrai_e_crea_proposte

        agenti = make_mock_agenti()
        testo = "Deliberazione senza proposte formali."

        proposte = await _estrai_e_crea_proposte(
            session=db_session,
            agenti=agenti,
            testo_deliberazione=testo,
        )

        assert proposte == []
