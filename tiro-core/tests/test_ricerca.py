import pytest
from sqlalchemy import text
from tiro_core.modelli.core import Soggetto, Flusso


@pytest.mark.asyncio
async def test_ricerca_flussi_per_vettore(db_session):
    soggetto = Soggetto(tipo="esterno", nome="Vec", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    flusso1 = Flusso(
        soggetto_id=soggetto.id,
        canale="posta",
        direzione="entrata",
        contenuto="Proposta di consulenza ingegneristica",
        dati_grezzi={},
    )
    flusso2 = Flusso(
        soggetto_id=soggetto.id,
        canale="messaggio",
        direzione="entrata",
        contenuto="Richiesta informazioni su stampa 3D",
        dati_grezzi={},
    )
    db_session.add_all([flusso1, flusso2])
    await db_session.commit()

    vec1 = [0.1] * 1536
    vec2 = [0.9] * 1536
    await db_session.execute(
        text("UPDATE core.flussi SET vettore = :v WHERE id = :id"),
        {"v": str(vec1), "id": flusso1.id},
    )
    await db_session.execute(
        text("UPDATE core.flussi SET vettore = :v WHERE id = :id"),
        {"v": str(vec2), "id": flusso2.id},
    )
    await db_session.commit()

    query_vec = str([0.1] * 1536)
    result = await db_session.execute(
        text(
            "SELECT id, contenuto FROM core.flussi "
            "WHERE vettore IS NOT NULL ORDER BY vettore <-> :qv LIMIT 1"
        ),
        {"qv": query_vec},
    )
    row = result.first()
    assert row is not None
    assert row.id == flusso1.id
    assert "consulenza" in row.contenuto
