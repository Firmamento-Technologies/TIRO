import pytest


@pytest.mark.asyncio
async def test_crea_soggetto(client, token_admin):
    response = await client.post(
        "/api/soggetti",
        json={"tipo": "esterno", "nome": "Mario", "cognome": "Rossi", "email": ["mario@example.com"], "tag": ["cliente"]},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Mario"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_lista_soggetti(client, token_admin):
    for nome in ["Alice", "Bob"]:
        await client.post(
            "/api/soggetti",
            json={"tipo": "membro", "nome": nome, "cognome": "Test"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
    response = await client.get("/api/soggetti", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_leggi_soggetto(client, token_admin):
    create_resp = await client.post(
        "/api/soggetti",
        json={"tipo": "partner", "nome": "Test", "cognome": "Read"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    soggetto_id = create_resp.json()["id"]
    response = await client.get(f"/api/soggetti/{soggetto_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
    assert response.json()["nome"] == "Test"


@pytest.mark.asyncio
async def test_aggiorna_soggetto(client, token_admin):
    create_resp = await client.post(
        "/api/soggetti",
        json={"tipo": "esterno", "nome": "Old", "cognome": "Name"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    soggetto_id = create_resp.json()["id"]
    response = await client.patch(
        f"/api/soggetti/{soggetto_id}",
        json={"nome": "New"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert response.json()["nome"] == "New"
