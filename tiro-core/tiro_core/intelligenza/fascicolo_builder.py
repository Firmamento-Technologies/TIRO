"""Generazione fascicoli — SQL queries + template Markdown + LLM solo per sintesi.

Livello 1: deterministico al 95%. LLM solo per la sintesi narrativa finale.
Se LLM non disponibile, fallback a concatenazione sezioni strutturate.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.config import settings
from tiro_core.intelligenza.scoring import (
    calcola_indice_opportunita,
    calcola_indice_rischio,
    calcola_scoring_soggetto,
)
from tiro_core.modelli.commerciale import Ente, Fascicolo, Opportunita
from tiro_core.modelli.core import Flusso, Soggetto

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatiFascicolo:
    """Dati raccolti dal DB per la generazione del fascicolo."""
    soggetto_id: int
    soggetto_nome: str
    soggetto_tipo: str
    soggetto_email: list[str]
    soggetto_telefono: list[str]
    soggetto_tag: list[str]
    totale_flussi: int
    flussi_recenti: list[dict]
    opportunita: list[dict]
    ente_nome: str | None
    indice_rischio: float
    indice_opportunita: float


async def raccogli_dati_fascicolo(
    session: AsyncSession,
    soggetto_id: int,
) -> DatiFascicolo | None:
    """Raccoglie tutti i dati dal DB per generare un fascicolo.

    Queries:
    1. Soggetto (anagrafica)
    2. Flussi recenti (ultimi N, ordinati per data)
    3. Opportunita associate
    4. Ente associato
    5. Scoring (via calcola_scoring_soggetto)
    """
    # Soggetto
    result = await session.execute(
        select(Soggetto).where(Soggetto.id == soggetto_id)
    )
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        return None

    # Flussi recenti
    result = await session.execute(
        select(Flusso)
        .where(Flusso.soggetto_id == soggetto_id)
        .order_by(Flusso.ricevuto_il.desc())
        .limit(settings.fascicolo_max_flussi_recenti)
    )
    flussi = result.scalars().all()

    # Conteggio totale flussi
    result = await session.execute(
        select(func.count(Flusso.id)).where(Flusso.soggetto_id == soggetto_id)
    )
    totale_flussi = result.scalar() or 0

    # Opportunita
    result = await session.execute(
        select(Opportunita).where(Opportunita.soggetto_id == soggetto_id)
    )
    opportunita_lista = result.scalars().all()

    # Ente (dal primo opportunita, se presente)
    ente_nome = None
    if opportunita_lista:
        ente_id = opportunita_lista[0].ente_id
        if ente_id:
            result = await session.execute(select(Ente).where(Ente.id == ente_id))
            ente = result.scalar_one_or_none()
            if ente:
                ente_nome = ente.nome

    # Scoring
    scoring = await calcola_scoring_soggetto(session, soggetto_id)

    # Indice rischio (usa dati da profilo soggetto se disponibili)
    ritardo = soggetto.profilo.get("ritardo_pagamento_giorni", 0)
    importo = soggetto.profilo.get("importo_scoperto_eur", 0.0)
    indice_rischio = calcola_indice_rischio(ritardo, importo, scoring.frequenza)

    # Indice opportunita
    probabilita_media = 0.0
    valore_tot = scoring.valore_pipeline
    if opportunita_lista:
        probs = [o.probabilita for o in opportunita_lista if o.probabilita]
        probabilita_media = sum(probs) / len(probs) if probs else 0.0
    indice_opportunita = calcola_indice_opportunita(
        valore_tot, probabilita_media, scoring.frequenza,
    )

    return DatiFascicolo(
        soggetto_id=soggetto_id,
        soggetto_nome=f"{soggetto.nome} {soggetto.cognome}",
        soggetto_tipo=soggetto.tipo,
        soggetto_email=list(soggetto.email or []),
        soggetto_telefono=list(soggetto.telefono or []),
        soggetto_tag=list(soggetto.tag or []),
        totale_flussi=totale_flussi,
        flussi_recenti=[
            {
                "canale": f.canale,
                "oggetto": f.oggetto,
                "data": f.ricevuto_il.strftime("%Y-%m-%d") if f.ricevuto_il else "",
                "contenuto_troncato": (f.contenuto or "")[:200],
            }
            for f in flussi
        ],
        opportunita=[
            {
                "titolo": o.titolo,
                "fase": o.fase,
                "valore_eur": o.valore_eur,
                "probabilita": o.probabilita,
            }
            for o in opportunita_lista
        ],
        ente_nome=ente_nome,
        indice_rischio=indice_rischio,
        indice_opportunita=indice_opportunita,
    )


def genera_sezioni_markdown(dati: DatiFascicolo) -> dict[str, str]:
    """Genera sezioni Markdown deterministiche dal template.

    Nessun LLM. Puro template con dati strutturati.
    """
    # Anagrafica
    emails = ", ".join(dati.soggetto_email) if dati.soggetto_email else "N/D"
    telefoni = ", ".join(dati.soggetto_telefono) if dati.soggetto_telefono else "N/D"
    tags = ", ".join(dati.soggetto_tag) if dati.soggetto_tag else "Nessuno"
    anagrafica = (
        f"## Anagrafica\n\n"
        f"- **Nome:** {dati.soggetto_nome}\n"
        f"- **Tipo:** {dati.soggetto_tipo}\n"
        f"- **Email:** {emails}\n"
        f"- **Telefono:** {telefoni}\n"
        f"- **Tag:** {tags}\n"
    )
    if dati.ente_nome:
        anagrafica += f"- **Ente:** {dati.ente_nome}\n"

    # Flussi
    if dati.flussi_recenti:
        righe = [f"| {f['data']} | {f['canale']} | {f['oggetto'] or '—'} |"
                 for f in dati.flussi_recenti[:10]]
        tabella = "| Data | Canale | Oggetto |\n|------|--------|--------|\n" + "\n".join(righe)
        flussi_md = (
            f"## Flussi\n\n"
            f"**Totale:** {dati.totale_flussi} flussi registrati.\n\n"
            f"**Ultimi {min(10, len(dati.flussi_recenti))}:**\n\n{tabella}\n"
        )
    else:
        flussi_md = "## Flussi\n\nNessun flusso registrato.\n"

    # Opportunita
    if dati.opportunita:
        righe_opp = [
            f"| {o['titolo']} | {o['fase']} | {o.get('valore_eur', 0):.0f} EUR | "
            f"{(o.get('probabilita', 0) or 0) * 100:.0f}% |"
            for o in dati.opportunita
        ]
        tabella_opp = (
            "| Titolo | Fase | Valore | Prob. |\n"
            "|--------|------|--------|-------|\n"
            + "\n".join(righe_opp)
        )
        opportunita_md = f"## Opportunita\n\n{tabella_opp}\n"
    else:
        opportunita_md = "## Opportunita\n\nNessuna opportunita registrata.\n"

    # Indici
    indici_md = (
        f"## Indici\n\n"
        f"- **Indice Rischio:** {dati.indice_rischio:.2f}\n"
        f"- **Indice Opportunita:** {dati.indice_opportunita:.2f}\n"
    )

    return {
        "anagrafica": anagrafica,
        "flussi": flussi_md,
        "opportunita": opportunita_md,
        "indici": indici_md,
    }


async def genera_sintesi_llm(sezioni: dict[str, str]) -> str:
    """Chiama LLM (OpenRouter) per generare sintesi narrativa.

    Unico punto di contatto con LLM in tutto il fascicolo builder.
    Se fallisce, il chiamante deve gestire il fallback.
    """
    testo_completo = "\n\n".join(sezioni.values())
    prompt = (
        "Sei un analista business. Leggi il fascicolo seguente e scrivi "
        "una sintesi narrativa di massimo 200 parole in italiano. "
        "Concentrati su: chi e il soggetto, stato delle opportunita, "
        "livello di rischio, azioni consigliate.\n\n"
        f"{testo_completo}"
    )

    async with httpx.AsyncClient(timeout=settings.fascicolo_llm_timeout_sec) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def genera_fascicolo(
    session: AsyncSession,
    soggetto_id: int,
    ente_id: int | None = None,
    usa_llm: bool = True,
) -> Fascicolo | None:
    """Genera un fascicolo completo per soggetto.

    Flow:
    1. Raccogli dati dal DB (deterministico)
    2. Genera sezioni Markdown (deterministico)
    3. Genera sintesi LLM (opzionale, con fallback)
    4. Calcola indici (deterministico)
    5. Salva Fascicolo nel DB

    Args:
        session: Sessione database.
        soggetto_id: ID del soggetto.
        ente_id: ID ente opzionale.
        usa_llm: Se True, chiama LLM per sintesi. Se False, fallback deterministico.

    Returns:
        Fascicolo creato, o None se soggetto non esiste.
    """
    dati = await raccogli_dati_fascicolo(session, soggetto_id)
    if dati is None:
        return None

    sezioni = genera_sezioni_markdown(dati)

    # Sintesi: LLM con fallback deterministico
    sintesi = None
    if usa_llm:
        try:
            sintesi = await genera_sintesi_llm(sezioni)
        except Exception:
            logger.warning(
                "LLM non disponibile per fascicolo soggetto %d, uso fallback",
                soggetto_id,
            )

    if sintesi is None:
        # Fallback: concatena titoli sezioni
        sintesi = (
            f"Fascicolo per {dati.soggetto_nome} ({dati.soggetto_tipo}). "
            f"Flussi totali: {dati.totale_flussi}. "
            f"Opportunita: {len(dati.opportunita)}. "
            f"Rischio: {dati.indice_rischio:.2f}. "
            f"Opportunita: {dati.indice_opportunita:.2f}."
        )

    fascicolo = Fascicolo(
        soggetto_id=soggetto_id,
        ente_id=ente_id,
        sintesi=sintesi,
        indice_rischio=dati.indice_rischio,
        indice_opportunita=dati.indice_opportunita,
        sezioni=sezioni,
    )
    session.add(fascicolo)
    await session.flush()
    return fascicolo
