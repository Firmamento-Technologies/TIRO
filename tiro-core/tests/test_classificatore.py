"""Test per il classificatore intent/sentiment."""
import pytest
from tiro_core.elaborazione.classificatore import (
    classifica,
    classifica_intent_regex,
    classifica_sentiment_regex,
    Classificazione,
    Intent,
    Sentiment,
)


class TestClassificaIntentRegex:
    def test_urgenza(self):
        intent, conf = classifica_intent_regex("Questo e URGENTE, servono risposte subito")
        assert intent == Intent.URGENZA
        assert conf >= 0.8

    def test_proposta(self):
        intent, conf = classifica_intent_regex("Vi propongo una collaborazione")
        assert intent == Intent.PROPOSTA

    def test_reclamo(self):
        intent, conf = classifica_intent_regex("Devo fare un reclamo formale")
        assert intent == Intent.RECLAMO

    def test_annullamento(self):
        intent, conf = classifica_intent_regex("Vorrei annullare l'ordine")
        assert intent == Intent.ANNULLAMENTO

    def test_conferma(self):
        intent, conf = classifica_intent_regex("Confermo la riunione di domani")
        assert intent == Intent.CONFERMA

    def test_richiesta_info(self):
        intent, conf = classifica_intent_regex("Vorrei avere informazioni sui vostri servizi")
        assert intent == Intent.RICHIESTA_INFO

    def test_sconosciuto(self):
        intent, conf = classifica_intent_regex("Lorem ipsum dolor sit amet")
        assert intent == Intent.SCONOSCIUTO
        assert conf == 0.0


class TestClassificaSentimentRegex:
    def test_positivo(self):
        assert classifica_sentiment_regex("Ottimo lavoro, grazie!") == Sentiment.POSITIVO

    def test_negativo(self):
        assert classifica_sentiment_regex("C'e un problema grave, pessimo servizio") == Sentiment.NEGATIVO

    def test_neutro(self):
        assert classifica_sentiment_regex("Confermo la riunione alle 10") == Sentiment.NEUTRO


class TestClassifica:
    def test_testo_vuoto(self):
        risultato = classifica("")
        assert risultato.intent == Intent.SCONOSCIUTO
        assert risultato.richiede_review_llm is True

    def test_alta_confidence_no_review(self):
        risultato = classifica("URGENTE: serve risposta immediata")
        assert risultato.intent == Intent.URGENZA
        assert risultato.confidence >= 0.6
        assert risultato.richiede_review_llm is False

    def test_bassa_confidence_richiede_review(self):
        risultato = classifica("Lorem ipsum dolor sit amet")
        assert risultato.richiede_review_llm is True

    def test_risultato_immutabile(self):
        risultato = classifica("Grazie per la proposta")
        assert isinstance(risultato, Classificazione)
        with pytest.raises(AttributeError):
            risultato.intent = Intent.RECLAMO  # frozen dataclass
