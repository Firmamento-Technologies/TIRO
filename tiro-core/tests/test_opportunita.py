import pytest


@pytest.mark.asyncio
async def test_crea_opportunita(client, token_admin):
    response = await client.post(
        "/api/opportunita",
        json={"titolo": "Consulenza CFD", "fase": "contatto", "valore_eur": 15000.0, "probabilita": 0.5},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titolo"] == "Consulenza CFD"
    assert data["fase"] == "contatto"


@pytest.mark.asyncio
async def test_lista_opportunita(client, token_admin):
    await client.post(
        "/api/opportunita",
        json={"titolo": "Deal 1", "fase": "contatto"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    response = await client.get("/api/opportunita", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
    assert len(response.json()) >= 1
