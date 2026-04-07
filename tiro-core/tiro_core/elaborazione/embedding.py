"""Generazione embedding vettoriali per flussi e risorse.

Pattern Open Notebook: se testo corto embed direttamente,
se lungo chunk -> batch embed -> mean pool.
"""
import logging
from dataclasses import dataclass

import httpx
import numpy as np

from tiro_core.config import settings

logger = logging.getLogger(__name__)

DIMENSIONE_VETTORE = 1536
CHUNK_SIZE = 1200  # caratteri per chunk
OVERLAP = 200
MAX_TENTATIVI = 3
RITARDO_TENTATIVI_SEC = 2


def chunk_testo(testo: str, dimensione: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Divide testo in chunk con overlap.

    Args:
        testo: Testo da dividere.
        dimensione: Dimensione massima per chunk.
        overlap: Sovrapposizione tra chunk consecutivi.

    Returns:
        Lista di chunk. Se testo < dimensione, ritorna [testo].
    """
    if len(testo) <= dimensione:
        return [testo] if testo.strip() else []

    chunks = []
    inizio = 0
    while inizio < len(testo):
        fine = inizio + dimensione
        chunk = testo[inizio:fine]
        if chunk.strip():
            chunks.append(chunk)
        inizio += dimensione - overlap

    return chunks


def mean_pool(vettori: list[list[float]]) -> list[float]:
    """Media dei vettori (mean pooling).

    Args:
        vettori: Lista di vettori embedding.

    Returns:
        Vettore medio normalizzato.
    """
    if not vettori:
        return [0.0] * DIMENSIONE_VETTORE
    if len(vettori) == 1:
        return vettori[0]

    arr = np.array(vettori)
    media = np.mean(arr, axis=0)
    # Normalizza L2
    norma = np.linalg.norm(media)
    if norma > 0:
        media = media / norma
    return media.tolist()


async def _embed_locale(testi: list[str]) -> list[list[float]]:
    """Genera embedding via Ollama API locale (nomic-embed-text).

    Args:
        testi: Lista di testi da embedded.

    Returns:
        Lista di vettori.
    """
    risultati = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for testo in testi:
            for tentativo in range(MAX_TENTATIVI):
                try:
                    risposta = await client.post(
                        settings.embedding_api_url,
                        json={"model": settings.embedding_model, "prompt": testo},
                    )
                    risposta.raise_for_status()
                    vettore = risposta.json().get("embedding", [])
                    risultati.append(vettore)
                    break
                except Exception as e:
                    if tentativo == MAX_TENTATIVI - 1:
                        logger.error("Embedding fallito dopo %d tentativi: %s", MAX_TENTATIVI, e)
                        risultati.append([0.0] * DIMENSIONE_VETTORE)
                    else:
                        import asyncio
                        await asyncio.sleep(RITARDO_TENTATIVI_SEC)
    return risultati


async def _embed_openai(testi: list[str]) -> list[list[float]]:
    """Genera embedding via OpenAI API (text-embedding-ada-002).

    Args:
        testi: Lista di testi da embedded.

    Returns:
        Lista di vettori.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        risposta = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": "text-embedding-ada-002", "input": testi},
        )
        risposta.raise_for_status()
        data = risposta.json()
        return [item["embedding"] for item in data["data"]]


async def genera_embedding(testo: str) -> list[float]:
    """Genera embedding per un testo, con chunking automatico se lungo.

    Strategia (da Open Notebook):
    - Testo <= CHUNK_SIZE: embed direttamente
    - Testo > CHUNK_SIZE: chunk -> batch embed -> mean pool

    Args:
        testo: Testo da embedded.

    Returns:
        Vettore embedding di dimensione DIMENSIONE_VETTORE.
    """
    if not testo or not testo.strip():
        return [0.0] * DIMENSIONE_VETTORE

    chunks = chunk_testo(testo)
    if not chunks:
        return [0.0] * DIMENSIONE_VETTORE

    # Scegli provider
    if settings.embedding_provider == "openai":
        embed_fn = _embed_openai
    else:
        embed_fn = _embed_locale

    vettori = await embed_fn(chunks)

    if len(vettori) == 1:
        return vettori[0]
    return mean_pool(vettori)
