import pytest
from tiro_core.modelli.core import Soggetto, Flusso


@pytest.mark.asyncio
async def test_esporta_soggetto(client, token_admin, db_session):
    s = Soggetto(tipo="esterno", nome="Export", cognome="Test", email=["ex@test.com"], telefono=[])
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    response = await client.get(
        f"/api/soggetti/{s.id}/export",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["soggetto"]["nome"] == "Export"
    assert "flussi" in data
    assert "opportunita" in data
    assert "fascicoli" in data
    assert "esportato_il" in data


@pytest.mark.asyncio
async def test_esporta_soggetto_not_found(client, token_admin):
    response = await client.get(
        "/api/soggetti/999999/export",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_anonimizza_soggetto(client, token_admin, db_session):
    s = Soggetto(tipo="esterno", nome="Cancella", cognome="Me", email=["del@test.com"], telefono=["+39111"])
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    f = Flusso(
        soggetto_id=s.id,
        canale="posta",
        direzione="entrata",
        contenuto="Dati sensibili",
        dati_grezzi={},
    )
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)

    response = await client.delete(
        f"/api/soggetti/{s.id}/cancella",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["stato"] == "anonimizzato"

    # Verify anonymization
    await db_session.refresh(s)
    assert s.nome == "RIMOSSO"
    assert s.cognome == "RIMOSSO"
    assert all("@anonimo" in e for e in s.email)
    assert s.tag == []
    assert s.profilo.get("anonimizzato") is True

    await db_session.refresh(f)
    assert f.contenuto is None
    assert f.dati_grezzi.get("anonimizzato") is True


@pytest.mark.asyncio
async def test_anonimizza_richiede_titolare(client, db_session):
    """Non-titolare users cannot anonymize."""
    from passlib.context import CryptContext
    from tiro_core.modelli.sistema import Utente
    from tiro_core.api.auth import crea_token

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    u = Utente(
        email="op@test.com",
        nome="Op",
        password_hash=pwd.hash("test"),
        ruolo="operativo",
        perimetro={},
        attivo=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    token = crea_token(u.id)

    s = Soggetto(tipo="esterno", nome="No", cognome="Delete", email=[], telefono=[])
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    response = await client.delete(
        f"/api/soggetti/{s.id}/cancella",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
