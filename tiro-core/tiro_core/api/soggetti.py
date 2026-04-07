from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from tiro_core.api.dipendenze import get_utente_corrente, richiedi_ruolo
from tiro_core.database import get_db
from tiro_core.modelli.core import Flusso, Soggetto
from tiro_core.modelli.sistema import Utente
from tiro_core.schemi.core import SoggettoCrea, SoggettoAggiorna, SoggettoResponse

router = APIRouter(prefix="/soggetti", tags=["soggetti"])


@router.get("", response_model=list[SoggettoResponse])
async def lista_soggetti(
    tipo: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    query = select(Soggetto).order_by(Soggetto.id)
    if tipo:
        query = query.where(Soggetto.tipo == tipo)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{soggetto_id}", response_model=SoggettoResponse)
async def leggi_soggetto(
    soggetto_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return soggetto


@router.post("", response_model=SoggettoResponse, status_code=status.HTTP_201_CREATED)
async def crea_soggetto(
    dati: SoggettoCrea,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    soggetto = Soggetto(**dati.model_dump())
    db.add(soggetto)
    await db.commit()
    await db.refresh(soggetto)
    return soggetto


@router.patch("/{soggetto_id}", response_model=SoggettoResponse)
async def aggiorna_soggetto(
    soggetto_id: int,
    dati: SoggettoAggiorna,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if soggetto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for campo, valore in dati.model_dump(exclude_unset=True).items():
        setattr(soggetto, campo, valore)
    await db.commit()
    await db.refresh(soggetto)
    return soggetto


@router.get("/{soggetto_id}/export")
async def esporta_soggetto(
    soggetto_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    """GDPR Art. 15 — export all data for a soggetto."""
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if not soggetto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    flussi_result = await db.execute(select(Flusso).where(Flusso.soggetto_id == soggetto_id))
    flussi = flussi_result.scalars().all()

    from tiro_core.modelli.commerciale import Opportunita, Fascicolo
    opp_result = await db.execute(select(Opportunita).where(Opportunita.soggetto_id == soggetto_id))
    opportunita = opp_result.scalars().all()

    fasc_result = await db.execute(select(Fascicolo).where(Fascicolo.soggetto_id == soggetto_id))
    fascicoli = fasc_result.scalars().all()

    return {
        "soggetto": {
            "id": soggetto.id,
            "tipo": soggetto.tipo,
            "nome": soggetto.nome,
            "cognome": soggetto.cognome,
            "email": soggetto.email,
            "telefono": soggetto.telefono,
            "ruolo": soggetto.ruolo,
            "tag": soggetto.tag,
            "profilo": soggetto.profilo,
        },
        "flussi": [
            {"id": f.id, "canale": f.canale, "contenuto": f.contenuto, "ricevuto_il": str(f.ricevuto_il)}
            for f in flussi
        ],
        "opportunita": [
            {"id": o.id, "titolo": o.titolo, "fase": o.fase, "valore_eur": o.valore_eur}
            for o in opportunita
        ],
        "fascicoli": [
            {"id": fc.id, "sintesi": fc.sintesi, "generato_il": str(fc.generato_il)}
            for fc in fascicoli
        ],
        "esportato_il": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{soggetto_id}/cancella")
async def anonimizza_soggetto(
    soggetto_id: int,
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(richiedi_ruolo("titolare")),
):
    """GDPR Art. 17 — right to erasure. Anonymizes soggetto and cascades."""
    import hashlib
    result = await db.execute(select(Soggetto).where(Soggetto.id == soggetto_id))
    soggetto = result.scalar_one_or_none()
    if not soggetto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Anonymize soggetto
    soggetto.nome = "RIMOSSO"
    soggetto.cognome = "RIMOSSO"
    soggetto.email = [hashlib.sha256(e.encode()).hexdigest()[:16] + "@anonimo" for e in soggetto.email]
    soggetto.telefono = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in soggetto.telefono]
    soggetto.ruolo = None
    soggetto.tag = []
    soggetto.profilo = {"anonimizzato": True, "anonimizzato_il": datetime.now(timezone.utc).isoformat()}

    # Cascade: remove content from flussi
    flussi = (await db.execute(select(Flusso).where(Flusso.soggetto_id == soggetto_id))).scalars().all()
    for f in flussi:
        f.contenuto = None
        f.oggetto = None
        f.dati_grezzi = {"anonimizzato": True}
        f.vettore = None

    # Cascade: delete fascicoli
    from tiro_core.modelli.commerciale import Fascicolo
    await db.execute(delete(Fascicolo).where(Fascicolo.soggetto_id == soggetto_id))

    # Cascade: anonymize opportunita references
    from tiro_core.modelli.commerciale import Opportunita
    opps = (await db.execute(select(Opportunita).where(Opportunita.soggetto_id == soggetto_id))).scalars().all()
    for o in opps:
        o.dettagli = {"anonimizzato": True}

    # Log in registro
    from tiro_core.modelli.sistema import Registro
    db.add(Registro(tipo_evento="gdpr_anonimizzazione", origine="api", dati={"soggetto_id": soggetto_id}))

    await db.commit()
    return {"stato": "anonimizzato", "soggetto_id": soggetto_id}
