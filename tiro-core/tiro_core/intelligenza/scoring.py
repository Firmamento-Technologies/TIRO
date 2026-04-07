"""Scoring deterministico per soggetti, rischio e opportunita.

Livello 1 — sempre attivo, nessun LLM. Formule numeriche pure
basate su metriche aggregate dal database.
"""
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.modelli.commerciale import Opportunita


@dataclass(frozen=True)
class ScoringSoggetto:
    """Risultato scoring immutabile per un soggetto."""
    soggetto_id: int
    frequenza: int  # numero flussi totali
    recency_giorni: float | None  # giorni dall'ultimo flusso
    valore_pipeline: float  # somma(valore_eur * probabilita) opportunita aperte
    score_totale: float  # formula combinata 0.0 - 1.0


def calcola_indice_rischio(
    ritardo_pagamento_giorni: int,
    importo_eur: float,
    frequenza_interazione: int,
) -> float:
    """Calcola indice rischio deterministico [0.0, 1.0].

    Formula: sigmoid(ritardo_norm * importo_norm * inattivita_factor)
    - ritardo_norm: ritardo_giorni / 90 (normalizzato su 3 mesi)
    - importo_norm: log(1 + importo) / log(1 + 100000) (normalizzato log)
    - inattivita_factor: 1.0 se freq==0, 0.5 se freq<5, 0.2 se freq>=5
    """
    if ritardo_pagamento_giorni == 0 and importo_eur == 0.0:
        return 0.0

    ritardo_norm = min(ritardo_pagamento_giorni / 90.0, 3.0)
    importo_norm = math.log(1 + importo_eur) / math.log(1 + 100_000)
    if frequenza_interazione == 0:
        inattivita = 1.0
    elif frequenza_interazione < 5:
        inattivita = 0.5
    else:
        inattivita = 0.2

    raw = ritardo_norm * importo_norm * inattivita
    # Sigmoid: 2/(1+e^(-2*raw)) - 1, mappato in [0,1]
    return min(max(2.0 / (1.0 + math.exp(-2.0 * raw)) - 1.0, 0.0), 1.0)


def calcola_indice_opportunita(
    valore_pipeline_eur: float,
    probabilita_media: float,
    engagement_recente: int,
) -> float:
    """Calcola indice opportunita deterministico [0.0, 1.0].

    Formula: weighted sum normalizzata:
    - 40% valore_norm: log(1 + valore) / log(1 + 500000)
    - 30% probabilita_media (gia in [0,1])
    - 30% engagement_norm: min(engagement / 20, 1.0)
    """
    if valore_pipeline_eur == 0.0 and probabilita_media == 0.0 and engagement_recente == 0:
        return 0.0

    valore_norm = math.log(1 + valore_pipeline_eur) / math.log(1 + 500_000)
    engagement_norm = min(engagement_recente / 20.0, 1.0)

    raw = 0.4 * valore_norm + 0.3 * probabilita_media + 0.3 * engagement_norm
    return min(max(raw, 0.0), 1.0)


async def calcola_scoring_soggetto(
    session: AsyncSession,
    soggetto_id: int,
) -> ScoringSoggetto:
    """Calcola scoring completo per un singolo soggetto.

    Queries:
    1. COUNT flussi totali
    2. MAX ricevuto_il (per recency)
    3. SUM(valore_eur * probabilita) da opportunita aperte
    """
    # Frequenza: conteggio flussi
    result = await session.execute(
        select(func.count(Flusso.id)).where(Flusso.soggetto_id == soggetto_id)
    )
    frequenza = result.scalar() or 0

    # Recency: data ultimo flusso
    result = await session.execute(
        select(func.max(Flusso.ricevuto_il)).where(Flusso.soggetto_id == soggetto_id)
    )
    ultimo_flusso = result.scalar()
    recency_giorni = None
    if ultimo_flusso is not None:
        if ultimo_flusso.tzinfo is None:
            ultimo_flusso = ultimo_flusso.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ultimo_flusso
        recency_giorni = delta.total_seconds() / 86400.0

    # Valore pipeline: somma (valore * probabilita) su opportunita non chiuse
    fasi_aperte = ("contatto", "qualificato", "proposta", "trattativa")
    result = await session.execute(
        select(
            func.coalesce(
                func.sum(Opportunita.valore_eur * Opportunita.probabilita), 0.0
            )
        ).where(
            Opportunita.soggetto_id == soggetto_id,
            Opportunita.fase.in_(fasi_aperte),
        )
    )
    valore_pipeline = float(result.scalar() or 0.0)

    # Score totale: formula combinata
    freq_norm = min(frequenza / 50.0, 1.0)
    recency_norm = 0.0
    if recency_giorni is not None:
        # Piu recente = score piu alto: e^(-giorni/30)
        recency_norm = math.exp(-recency_giorni / 30.0)
    valore_norm = math.log(1 + valore_pipeline) / math.log(1 + 100_000) if valore_pipeline > 0 else 0.0

    score_totale = min(
        0.3 * freq_norm + 0.3 * recency_norm + 0.4 * min(valore_norm, 1.0),
        1.0,
    )

    return ScoringSoggetto(
        soggetto_id=soggetto_id,
        frequenza=frequenza,
        recency_giorni=recency_giorni,
        valore_pipeline=valore_pipeline,
        score_totale=score_totale,
    )


async def calcola_scoring_batch(
    session: AsyncSession,
    soggetto_ids: list[int] | None = None,
) -> list[ScoringSoggetto]:
    """Calcola scoring per una lista di soggetti o tutti.

    Args:
        session: Sessione database.
        soggetto_ids: Lista ID. Se None, calcola per tutti.

    Returns:
        Lista di ScoringSoggetto ordinata per score_totale desc.
    """
    if soggetto_ids is None:
        result = await session.execute(select(Soggetto.id))
        soggetto_ids = [row[0] for row in result.all()]

    risultati = []
    for sid in soggetto_ids:
        score = await calcola_scoring_soggetto(session, sid)
        risultati.append(score)

    return sorted(risultati, key=lambda s: s.score_totale, reverse=True)
