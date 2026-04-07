import pytest


@pytest.mark.asyncio
async def test_crea_task(client, token_admin):
    response = await client.post(
        "/api/task",
        json={"titolo": "Test task", "descrizione": "Descrizione test", "priorita": "alta"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titolo"] == "Test task"
    assert data["stato"] == "aperta"
    assert data["priorita"] == "alta"
    assert data["descrizione"] == "Descrizione test"
    assert "id" in data
    assert "creato_il" in data


@pytest.mark.asyncio
async def test_lista_task(client, token_admin):
    # Create 2 tasks
    for i in range(2):
        await client.post(
            "/api/task",
            json={"titolo": f"Task {i}", "priorita": "media"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

    response = await client.get(
        "/api/task",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_lista_task_filtro_stato(client, token_admin):
    # Create a task with default stato "aperta"
    await client.post(
        "/api/task",
        json={"titolo": "Task filtro", "priorita": "bassa"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    # Filter by stato aperta — should find it
    response = await client.get(
        "/api/task?stato=aperta",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["stato"] == "aperta" for t in data)

    # Filter by stato completata — should not find just-created task
    response = await client.get(
        "/api/task?stato=completata",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["stato"] == "completata" for t in data)


@pytest.mark.asyncio
async def test_crea_task_richiede_autenticazione(client):
    response = await client.post(
        "/api/task",
        json={"titolo": "No auth"},
    )
    assert response.status_code in (401, 403)
