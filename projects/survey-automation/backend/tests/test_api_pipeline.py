"""Тесты API: пайплайн обработки."""
import pytest


@pytest.mark.asyncio
async def test_pipeline_status(client):
    """GET /api/projects/{id}/pipeline/status returns pipeline status for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "Пайплайн тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/projects/{project_id}/pipeline/status"
    )
    assert response.status_code == 200
    data = response.json()
    # PipelineStatusResponse fields
    assert "stage" in data or "current_stage" in data or "completed_stages" in data


@pytest.mark.asyncio
async def test_pipeline_status_not_found(client):
    """GET /api/projects/{id}/pipeline/status for nonexistent project returns 404."""
    response = await client.get(
        "/api/projects/nonexistent_id_12345/pipeline/status"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_transcribe_endpoint(client):
    """POST /api/projects/{id}/pipeline/transcribe returns 202 for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "Транскрипция тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/pipeline/transcribe"
    )
    assert response.status_code == 202
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_pipeline_transcribe_not_found(client):
    """POST /api/projects/{id}/pipeline/transcribe for nonexistent project returns 404."""
    response = await client.post(
        "/api/projects/nonexistent_id_12345/pipeline/transcribe"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_extract_endpoint(client):
    """POST /api/projects/{id}/pipeline/extract returns 202 for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "Извлечение тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/pipeline/extract"
    )
    assert response.status_code == 202
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_pipeline_generate_bpmn_endpoint(client):
    """POST /api/projects/{id}/pipeline/generate-bpmn returns 202 for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "BPMN тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/pipeline/generate-bpmn"
    )
    assert response.status_code == 202
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_pipeline_gap_analysis_endpoint(client):
    """POST /api/projects/{id}/pipeline/gap-analysis returns 202 for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "GAP тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/pipeline/gap-analysis"
    )
    assert response.status_code == 202
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_pipeline_generate_docs_endpoint(client):
    """POST /api/projects/{id}/pipeline/generate-docs returns 202 for existing project."""
    create_resp = await client.post(
        "/api/projects/", json={"name": "Документы тест"}
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/pipeline/generate-docs"
    )
    assert response.status_code == 202
    data = response.json()
    assert "message" in data
