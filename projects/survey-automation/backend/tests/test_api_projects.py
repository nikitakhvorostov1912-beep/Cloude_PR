"""Тесты API: управление проектами (CRUD)."""
import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    """POST /api/projects/ creates a project and returns 201."""
    response = await client.post(
        "/api/projects/",
        json={"name": "Тестовый проект", "description": "Описание"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Тестовый проект"
    assert data["description"] == "Описание"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_project_minimal(client):
    """POST /api/projects/ with only required 'name' field."""
    response = await client.post("/api/projects/", json={"name": "Минимальный"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Минимальный"
    assert data["description"] == ""


@pytest.mark.asyncio
async def test_create_project_validation_error(client):
    """POST /api/projects/ with empty name returns 422."""
    response = await client.post("/api/projects/", json={"name": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_projects_empty(client):
    """GET /api/projects/ with no projects returns empty list."""
    response = await client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_projects_after_create(client):
    """GET /api/projects/ after creating a project returns it in the list."""
    await client.post("/api/projects/", json={"name": "Проект 1"})
    await client.post("/api/projects/", json={"name": "Проект 2"})
    response = await client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["projects"]) >= 1


@pytest.mark.asyncio
async def test_get_project(client):
    """GET /api/projects/{id} returns the created project."""
    create_resp = await client.post("/api/projects/", json={"name": "Проект"})
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Проект"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    """GET /api/projects/{id} for nonexistent project returns 404."""
    response = await client.get("/api/projects/nonexistent_id_12345")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(client):
    """DELETE /api/projects/{id} removes the project."""
    create_resp = await client.post("/api/projects/", json={"name": "Удаляемый"})
    project_id = create_resp.json()["id"]

    # Delete
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    # Verify deleted
    get_resp = await client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_not_found(client):
    """DELETE /api/projects/{id} for nonexistent project returns 404."""
    response = await client.delete("/api/projects/nonexistent_id_12345")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_project_returns_pipeline_state(client):
    """Created project contains pipeline_state in response."""
    response = await client.post(
        "/api/projects/", json={"name": "С пайплайном"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "pipeline_state" in data
