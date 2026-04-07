"""Test equipaggio CrewAI — mock Agent e LLM."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# Config LLM di test
CONFIG_LLM_TEST = {
    "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
    "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
    "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
    "finanza": {"provider": "locale", "modello": "qwen3-8b"},
    "risorse": {"provider": "locale", "modello": "qwen3-8b"},
}

DB_URL = "postgresql+asyncpg://test:test@localhost/test"


class TestCreaAgente:
    """Test per la factory crea_agente."""

    def _patch_crewai(self):
        """Patch per Agent e LLM in crewai.equipaggio."""
        return (
            patch("tiro_core.intelligenza.equipaggio.LLM"),
            patch("tiro_core.intelligenza.equipaggio.Agent"),
        )

    def test_crea_agente_ruolo_valido(self):
        """Crea agente con ruolo valido."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        mock_llm = MagicMock()
        mock_agent = MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", return_value=mock_llm) as mock_llm_class, \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=mock_agent) as mock_agent_class:
            result = crea_agente("direzione", CONFIG_LLM_TEST)

        mock_llm_class.assert_called_once()
        mock_agent_class.assert_called_once()
        assert result is mock_agent

    def test_crea_agente_model_string_openrouter(self):
        """Verifica che il model string sia corretto per openrouter."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        captured_model = {}

        def capture_llm(model=None, **kwargs):
            captured_model["model"] = model
            return MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", side_effect=capture_llm), \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=MagicMock()):
            crea_agente("direzione", CONFIG_LLM_TEST)

        assert captured_model["model"] == "openrouter/anthropic/claude-sonnet-4-6"

    def test_crea_agente_model_string_groq(self):
        """Verifica model string per groq."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        captured_model = {}

        def capture_llm(model=None, **kwargs):
            captured_model["model"] = model
            return MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", side_effect=capture_llm), \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=MagicMock()):
            crea_agente("tecnologia", CONFIG_LLM_TEST)

        assert captured_model["model"] == "groq/llama-4-scout-17b"

    def test_crea_agente_model_string_locale_ollama(self):
        """Provider 'locale' viene mappato su 'ollama'."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        captured_model = {}

        def capture_llm(model=None, **kwargs):
            captured_model["model"] = model
            return MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", side_effect=capture_llm), \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=MagicMock()):
            crea_agente("finanza", CONFIG_LLM_TEST)

        assert captured_model["model"] == "ollama/qwen3-8b"

    def test_crea_agente_ruolo_invalido_raise(self):
        """Ruolo sconosciuto solleva ValueError."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        with pytest.raises(ValueError, match="Ruolo 'inesistente' non valido"):
            crea_agente("inesistente", CONFIG_LLM_TEST)

    def test_crea_agente_con_strumenti(self):
        """L'agente viene creato con i tool passati."""
        from tiro_core.intelligenza.equipaggio import crea_agente

        mock_tool = MagicMock()
        captured_kwargs = {}

        def capture_agent(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.equipaggio.Agent", side_effect=capture_agent):
            crea_agente("mercato", CONFIG_LLM_TEST, strumenti=[mock_tool])

        assert captured_kwargs["tools"] == [mock_tool]

    def test_crea_agente_role_in_italiano(self):
        """Il ruolo dell'agente e in italiano."""
        from tiro_core.intelligenza.equipaggio import crea_agente, DESCRIZIONI_RUOLI

        captured_kwargs = {}

        def capture_agent(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.equipaggio.Agent", side_effect=capture_agent):
            crea_agente("direzione", CONFIG_LLM_TEST)

        assert captured_kwargs["role"] == DESCRIZIONI_RUOLI["direzione"]["role"]
        assert "Direttore" in captured_kwargs["role"]


class TestCreaEquipaggio:
    """Test per crea_equipaggio."""

    def test_crea_equipaggio_5_agenti(self):
        """crea_equipaggio ritorna dizionario con 5 agenti."""
        from tiro_core.intelligenza.equipaggio import crea_equipaggio

        # Mock tutti i tool e Agent/LLM
        mock_agent = MagicMock()
        mock_tool = MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=mock_agent), \
             patch("tiro_core.intelligenza.strumenti.CercaSoggetti", return_value=mock_tool), \
             patch("tiro_core.intelligenza.strumenti.CercaFlussi", return_value=mock_tool), \
             patch("tiro_core.intelligenza.strumenti.CercaOpportunita", return_value=mock_tool), \
             patch("tiro_core.intelligenza.strumenti.LeggiFascicolo", return_value=mock_tool), \
             patch("tiro_core.intelligenza.strumenti.CreaProposta", return_value=mock_tool):
            agenti = crea_equipaggio(CONFIG_LLM_TEST, DB_URL)

        assert len(agenti) == 5
        assert set(agenti.keys()) == {"direzione", "tecnologia", "mercato", "finanza", "risorse"}

    def test_crea_equipaggio_tutti_agenti_creati(self):
        """Tutti i ruoli sono presenti nell'equipaggio."""
        from tiro_core.intelligenza.equipaggio import crea_equipaggio, RUOLI

        mock_agent = MagicMock()

        with patch("tiro_core.intelligenza.equipaggio.LLM", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.equipaggio.Agent", return_value=mock_agent), \
             patch("tiro_core.intelligenza.strumenti.CercaSoggetti", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.strumenti.CercaFlussi", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.strumenti.CercaOpportunita", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.strumenti.LeggiFascicolo", return_value=MagicMock()), \
             patch("tiro_core.intelligenza.strumenti.CreaProposta", return_value=MagicMock()):
            agenti = crea_equipaggio(CONFIG_LLM_TEST, DB_URL)

        for ruolo in RUOLI:
            assert ruolo in agenti


class TestLeggiConfigLlm:
    """Test per leggi_config_llm."""

    @pytest.mark.asyncio
    async def test_leggi_config_da_db(self, db_session):
        """Legge configurazione LLM dalla tabella configurazione."""
        from tiro_core.intelligenza.equipaggio import leggi_config_llm
        from tiro_core.modelli.sistema import Configurazione

        config = Configurazione(
            chiave="provider_llm",
            valore=CONFIG_LLM_TEST,
        )
        db_session.add(config)
        await db_session.flush()

        result = await leggi_config_llm(db_session)
        assert result["direzione"]["modello"] == "anthropic/claude-sonnet-4-6"
        assert result["tecnologia"]["provider"] == "groq"

    @pytest.mark.asyncio
    async def test_leggi_config_fallback_default(self, db_session):
        """Senza config nel DB usa valori default."""
        from tiro_core.intelligenza.equipaggio import leggi_config_llm, CONFIG_LLM_DEFAULT

        result = await leggi_config_llm(db_session)
        assert result == CONFIG_LLM_DEFAULT


class TestCostruisciModelString:
    """Test per _costruisci_model_string."""

    def test_openrouter(self):
        from tiro_core.intelligenza.equipaggio import _costruisci_model_string
        s = _costruisci_model_string("openrouter", "anthropic/claude-sonnet-4-6")
        assert s == "openrouter/anthropic/claude-sonnet-4-6"

    def test_groq(self):
        from tiro_core.intelligenza.equipaggio import _costruisci_model_string
        s = _costruisci_model_string("groq", "llama-4-scout-17b")
        assert s == "groq/llama-4-scout-17b"

    def test_locale_diventa_ollama(self):
        from tiro_core.intelligenza.equipaggio import _costruisci_model_string
        s = _costruisci_model_string("locale", "qwen3-8b")
        assert s == "ollama/qwen3-8b"

    def test_provider_sconosciuto_passato_diretto(self):
        from tiro_core.intelligenza.equipaggio import _costruisci_model_string
        s = _costruisci_model_string("custom", "my-model")
        assert s == "custom/my-model"
