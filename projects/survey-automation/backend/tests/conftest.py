"""Фикстуры для тестов."""
import json
import pytest
import pytest_asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.config import AppConfig, AppSettings, TranscriptionConfig, AnalysisConfig, ExportConfig

TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"


@pytest.fixture
def app(tmp_path):
    """Create test FastAPI app with patched config pointing to tmp_path."""
    data_dir = tmp_path / "data" / "projects"
    data_dir.mkdir(parents=True)

    test_settings = AppSettings(
        title="Survey Automation Test",
        version="1.0.0-test",
        host="0.0.0.0",
        port=8000,
        data_dir=str(data_dir),
    )
    test_config = AppConfig(
        app=test_settings,
        transcription=TranscriptionConfig(model_size="tiny", device="cpu"),
        analysis=AnalysisConfig(model="claude-sonnet-4-20250514", max_tokens=4096),
        export=ExportConfig(),
    )

    # Clear the lru_cache before patching
    from app.config import get_config
    get_config.cache_clear()

    with patch("app.config.get_config", return_value=test_config):
        from main import create_app
        application = create_app()
        yield application

    # Clear again after test
    get_config.cache_clear()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_transcript():
    """Load sample transcript from test_data."""
    with open(TEST_DATA_DIR / "transcript_sales.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_processes():
    """Load sample processes from test_data."""
    with open(TEST_DATA_DIR / "processes_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_gaps():
    """Load sample GAP analysis from test_data."""
    with open(TEST_DATA_DIR / "gap_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)
