from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.config import settings
from tiro_core.modelli.sistema import Configurazione, RegolaRischio, Utente

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

REGOLE_DEFAULT = [
    ("aggiorna_fascicolo", "basso", "Aggiornamento fascicolo interno", True),
    ("crea_task_interna", "basso", "Creazione task per team", True),
    ("annota_soggetto", "basso", "Annotazione su soggetto", True),
    ("genera_report_interno", "basso", "Generazione report interno", True),
    ("aggiorna_memoria_agente", "basso", "Aggiornamento memoria agente", True),
    ("invia_email", "medio", "Invio email a contatto esterno", False),
    ("modifica_fase_opportunita", "medio", "Cambio fase opportunita commerciale", False),
    ("crea_soggetto", "medio", "Creazione nuovo soggetto", False),
    ("invia_messaggio_gruppo", "medio", "Messaggio in gruppo WhatsApp", False),
    ("pianifica_meeting", "medio", "Pianificazione meeting", False),
    ("invia_proposta_commerciale", "alto", "Invio proposta commerciale", False),
    ("modifica_budget", "alto", "Modifica budget sopra 500 EUR", False),
    ("contatta_istituzione", "alto", "Contatto diretto con istituzione", False),
    ("modifica_dati_ente", "alto", "Modifica dati ente", False),
    ("modifica_contratto", "critico", "Modifica contrattuale", False),
    ("comunicazione_legale", "critico", "Comunicazione a valenza legale", False),
    ("operazione_finanziaria", "critico", "Operazione finanziaria sopra 5000 EUR", False),
    ("elimina_soggetto", "critico", "Eliminazione soggetto", False),
]


async def seed_database(db: AsyncSession) -> None:
    result = await db.execute(select(Utente).where(Utente.email == settings.admin_email))
    if result.scalar_one_or_none() is None:
        admin = Utente(
            email=settings.admin_email,
            nome="Amministratore",
            password_hash=pwd_context.hash(settings.admin_password),
            ruolo="titolare",
            perimetro={},
            attivo=True,
        )
        db.add(admin)

    result = await db.execute(select(RegolaRischio))
    if not result.scalars().all():
        for pattern, livello, desc, auto in REGOLE_DEFAULT:
            db.add(
                RegolaRischio(
                    pattern_azione=pattern,
                    livello_rischio=livello,
                    descrizione=desc,
                    approvazione_automatica=auto,
                )
            )

    result = await db.execute(
        select(Configurazione).where(Configurazione.chiave == "provider_llm")
    )
    if result.scalar_one_or_none() is None:
        db.add(
            Configurazione(
                chiave="provider_llm",
                valore={
                    "direzione": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
                    "tecnologia": {"provider": "groq", "modello": "llama-4-scout-17b"},
                    "mercato": {"provider": "groq", "modello": "llama-4-scout-17b"},
                    "finanza": {"provider": "locale", "modello": "qwen3-8b"},
                    "risorse": {"provider": "locale", "modello": "qwen3-8b"},
                    "fascicoli": {"provider": "openrouter", "modello": "anthropic/claude-sonnet-4-6"},
                    "embedding": {"provider": "locale", "modello": "nomic-embed-text"},
                    "fallback": {"provider": "openrouter", "modello": "anthropic/claude-haiku-4-5"},
                },
            )
        )

    await db.commit()
