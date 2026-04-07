"""Classificatore intent/sentiment — spaCy rule-based + TextCategorizer.

Principio Script-First: regex pattern per intent comuni,
spaCy per sentiment. Se confidence < soglia, flag per review LLM (Piano 3).
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum

from tiro_core.config import settings

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    RICHIESTA_INFO = "richiesta_info"
    PROPOSTA = "proposta"
    RECLAMO = "reclamo"
    CONFERMA = "conferma"
    ANNULLAMENTO = "annullamento"
    URGENZA = "urgenza"
    SALUTO = "saluto"
    AGGIORNAMENTO = "aggiornamento"
    SCONOSCIUTO = "sconosciuto"


class Sentiment(str, Enum):
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"


@dataclass(frozen=True)
class Classificazione:
    intent: Intent
    sentiment: Sentiment
    confidence: float  # 0.0 - 1.0
    richiede_review_llm: bool  # True se confidence < soglia


# Pattern regex per intent deterministici
PATTERN_INTENT: list[tuple[re.Pattern, Intent, float]] = [
    (re.compile(r"\b(?:urgente|urgenza|asap|immediatamente|subito)\b", re.I), Intent.URGENZA, 0.9),
    (re.compile(r"\b(?:annull|cancel|disdic|recedere|revoc)\w*\b", re.I), Intent.ANNULLAMENTO, 0.85),
    (re.compile(r"\b(?:reclamo|lament|protest|insoddisfatt)\w*\b", re.I), Intent.RECLAMO, 0.85),
    (re.compile(r"\b(?:propon|proposta|offerta|preventivo|quotazione)\w*\b", re.I), Intent.PROPOSTA, 0.8),
    (re.compile(r"\b(?:conferm|approv|accett|ok|perfetto|d'accordo)\w*\b", re.I), Intent.CONFERMA, 0.75),
    (re.compile(r"\b(?:informazion|dettagli|sapere|chieder|domand)\w*\b", re.I), Intent.RICHIESTA_INFO, 0.7),
    (re.compile(r"\b(?:aggiorn|update|stato|progress|avanzamento)\w*\b", re.I), Intent.AGGIORNAMENTO, 0.7),
    (re.compile(r"\b(?:ciao|salve|buongiorno|buonasera|saluti)\b", re.I), Intent.SALUTO, 0.6),
]

# Pattern per sentiment
PATTERN_SENTIMENT_POSITIVO = re.compile(
    r"\b(?:grazie|ottimo|perfetto|eccellente|fantastico|bene|contento|soddisfatt)\w*\b", re.I
)
PATTERN_SENTIMENT_NEGATIVO = re.compile(
    r"\b(?:problema|errore|sbagliato|pessimo|deluso|inaccettabil|vergogn|schifo)\w*\b", re.I
)


def classifica_intent_regex(testo: str) -> tuple[Intent, float]:
    """Classifica intent con pattern regex.

    Returns:
        Tuple (intent, confidence). Se nessun pattern matcha: (SCONOSCIUTO, 0.0).
    """
    for pattern, intent, confidence in PATTERN_INTENT:
        if pattern.search(testo):
            return intent, confidence
    return Intent.SCONOSCIUTO, 0.0


def classifica_sentiment_regex(testo: str) -> Sentiment:
    """Classifica sentiment con conteggio pattern positivi/negativi."""
    positivi = len(PATTERN_SENTIMENT_POSITIVO.findall(testo))
    negativi = len(PATTERN_SENTIMENT_NEGATIVO.findall(testo))

    if positivi > negativi:
        return Sentiment.POSITIVO
    elif negativi > positivi:
        return Sentiment.NEGATIVO
    return Sentiment.NEUTRO


def classifica(testo: str, nlp=None) -> Classificazione:
    """Pipeline classificazione completa: regex -> spaCy -> flag LLM.

    Args:
        testo: Contenuto da classificare.
        nlp: Modello spaCy opzionale (per TextCategorizer se disponibile).

    Returns:
        Classificazione immutabile con intent, sentiment, confidence.
    """
    if not testo:
        return Classificazione(
            intent=Intent.SCONOSCIUTO,
            sentiment=Sentiment.NEUTRO,
            confidence=0.0,
            richiede_review_llm=True,
        )

    intent, confidence = classifica_intent_regex(testo)
    sentiment = classifica_sentiment_regex(testo)

    # Se confidence bassa, prova spaCy TextCategorizer
    if confidence < settings.classification_confidence_threshold and nlp is not None:
        try:
            doc = nlp(testo[:5000])
            if doc.cats:
                # spaCy TextCategorizer ritorna dict {label: score}
                best_cat = max(doc.cats, key=doc.cats.get)
                spacy_conf = doc.cats[best_cat]
                if spacy_conf > confidence:
                    # Mappa categoria spaCy a Intent TIRO se possibile
                    confidence = spacy_conf
        except Exception:
            logger.warning("spaCy TextCategorizer non disponibile")

    soglia = settings.classification_confidence_threshold
    return Classificazione(
        intent=intent,
        sentiment=sentiment,
        confidence=confidence,
        richiede_review_llm=confidence < soglia,
    )
