"""Parser strutturato — estrazione dati da contenuto grezzo.

Strategia a due livelli:
1. Regex deterministici per pattern noti (email, telefono, URL, firma email)
2. spaCy NER per entita non catturate (persone, organizzazioni, luoghi)
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Pattern regex ---

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_TELEFONO = re.compile(r"(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
RE_URL = re.compile(r"https?://[^\s<>\"']+")
RE_PARTITA_IVA = re.compile(r"\b(?:IT)?\d{11}\b")
RE_CODICE_FISCALE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")
RE_IMPORTO_EUR = re.compile(r"(?:EUR|€)\s?[\d.,]+|\d[\d.,]+\s?(?:EUR|€|euro)", re.IGNORECASE)
RE_DATA_IT = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")

# Firma email: blocco dopo "---" o pattern comuni
RE_FIRMA_SEPARATORE = re.compile(r"\n[-_]{2,}\s*\n")


@dataclass(frozen=True)
class DatiEstratti:
    """Risultato del parsing strutturato."""
    email_trovate: tuple[str, ...] = ()
    telefoni_trovati: tuple[str, ...] = ()
    url_trovati: tuple[str, ...] = ()
    importi_eur: tuple[str, ...] = ()
    date_menzionate: tuple[str, ...] = ()
    partite_iva: tuple[str, ...] = ()
    codici_fiscali: tuple[str, ...] = ()
    entita_ner: tuple[dict, ...] = ()  # [{"testo": "...", "tipo": "PER|ORG|LOC"}]
    firma_email: str = ""


def estrai_con_regex(testo: str) -> dict:
    """Estrae dati strutturati dal testo con regex deterministici.

    Returns:
        Dict con liste di match per ogni categoria.
    """
    return {
        "email_trovate": tuple(set(RE_EMAIL.findall(testo))),
        "telefoni_trovati": tuple(set(RE_TELEFONO.findall(testo))),
        "url_trovati": tuple(set(RE_URL.findall(testo))),
        "importi_eur": tuple(set(RE_IMPORTO_EUR.findall(testo))),
        "date_menzionate": tuple(set(RE_DATA_IT.findall(testo))),
        "partite_iva": tuple(set(RE_PARTITA_IVA.findall(testo))),
        "codici_fiscali": tuple(set(RE_CODICE_FISCALE.findall(testo))),
    }


def estrai_firma_email(testo: str) -> str:
    """Estrae la firma email (blocco dopo separatore --- o simile)."""
    match = RE_FIRMA_SEPARATORE.search(testo)
    if match:
        return testo[match.end():].strip()
    return ""


def estrai_con_spacy(testo: str, nlp=None) -> tuple[dict, ...]:
    """Estrae entita con spaCy NER.

    Args:
        testo: Testo da analizzare.
        nlp: Modello spaCy precaricato (lazy-loaded se None).

    Returns:
        Tuple di dict con entita trovate.
    """
    if nlp is None:
        try:
            import spacy
            nlp = spacy.load(settings_spacy_model())
        except (ImportError, OSError):
            logger.warning("spaCy non disponibile, skip NER")
            return ()

    doc = nlp(testo[:10000])  # Limita a 10k chars per performance
    entita = []
    visti = set()
    for ent in doc.ents:
        if ent.label_ in ("PER", "ORG", "LOC", "MISC") and ent.text not in visti:
            entita.append({"testo": ent.text, "tipo": ent.label_})
            visti.add(ent.text)
    return tuple(entita)


def settings_spacy_model() -> str:
    """Helper per evitare import circolare con settings."""
    from tiro_core.config import settings
    return settings.spacy_model


def parsa_contenuto(testo: str, nlp=None) -> DatiEstratti:
    """Pipeline completa di parsing: regex + spaCy NER.

    Args:
        testo: Contenuto grezzo (email body, messaggio, trascrizione).
        nlp: Modello spaCy opzionale (per evitare reload in batch).

    Returns:
        DatiEstratti immutabile con tutti i dati estratti.
    """
    if not testo:
        return DatiEstratti()

    regex_result = estrai_con_regex(testo)
    firma = estrai_firma_email(testo)
    entita_ner = estrai_con_spacy(testo, nlp=nlp)

    return DatiEstratti(
        email_trovate=regex_result["email_trovate"],
        telefoni_trovati=regex_result["telefoni_trovati"],
        url_trovati=regex_result["url_trovati"],
        importi_eur=regex_result["importi_eur"],
        date_menzionate=regex_result["date_menzionate"],
        partite_iva=regex_result["partite_iva"],
        codici_fiscali=regex_result["codici_fiscali"],
        entita_ner=entita_ner,
        firma_email=firma,
    )
