import pytest


@pytest.mark.asyncio
async def test_login_corretto(client, utente_admin):
    response = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "test123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["tipo"] == "bearer"


@pytest.mark.asyncio
async def test_login_password_errata(client, utente_admin):
    response = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "sbagliata"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_protetto_senza_token(client):
    response = await client.get("/api/soggetti")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_endpoint_protetto_con_token(client, token_admin):
    response = await client.get("/api/soggetti", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
