import pytest
from tiro_core.modelli.core import Soggetto, Flusso


@pytest.mark.asyncio
async def test_lista_flussi_per_soggetto(client, token_admin, db_session):
    soggetto = Soggetto(tipo="membro", nome="Flow", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    for i in range(3):
        db_session.add(
            Flusso(
                soggetto_id=soggetto.id,
                canale="messaggio",
                direzione="entrata",
                contenuto=f"Messaggio {i}",
                dati_grezzi={},
            )
        )
    await db_session.commit()

    response = await client.get(
        f"/api/flussi?soggetto_id={soggetto.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_lista_flussi_per_canale(client, token_admin, db_session):
    soggetto = Soggetto(tipo="esterno", nome="Chan", cognome="Test", email=[], telefono=[])
    db_session.add(soggetto)
    await db_session.commit()

    db_session.add(
        Flusso(
            soggetto_id=soggetto.id,
            canale="posta",
            direzione="entrata",
            contenuto="Email",
            dati_grezzi={},
        )
    )
    db_session.add(
        Flusso(
            soggetto_id=soggetto.id,
            canale="messaggio",
            direzione="entrata",
            contenuto="WA",
            dati_grezzi={},
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/flussi?canale=posta",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(f["canale"] == "posta" for f in data)
