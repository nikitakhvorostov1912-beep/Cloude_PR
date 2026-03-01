"""Shared test fixtures for interview-to-bpmn."""
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config():
    """Load test config from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_raw_transcription():
    """Sample raw transcription result from transcriber."""
    return {
        "segments": [
            {"start": 0.0, "end": 5.2, "text": "Добрый день, расскажите о вашем отделе.", "speaker": "SPEAKER_00"},
            {"start": 5.5, "end": 12.0, "text": "Здравствуйте, наш отдел занимается закупками.", "speaker": "SPEAKER_01"},
            {"start": 12.5, "end": 20.0, "text": "Какие основные процессы?", "speaker": "SPEAKER_00"},
            {"start": 21.0, "end": 35.0, "text": "Основной процесс — это оформление заявки на закупку.", "speaker": "SPEAKER_01"},
        ],
        "language": "ru",
        "audio_path": "/tmp/test.wav",
    }


@pytest.fixture
def sample_formatted_transcript(sample_raw_transcription):
    """Sample formatted transcript."""
    from src.transcription.formatter import format_transcript
    return format_transcript(sample_raw_transcription)


@pytest.fixture
def sample_processes():
    """Sample extracted processes."""
    return {
        "processes": [
            {
                "id": "proc_1",
                "name": "Оформление заявки на закупку",
                "type": "as_is",
                "trigger": "Потребность подразделения в товарах/услугах",
                "result": "Утверждённая заявка на закупку",
                "frequency": "Ежедневно",
                "participants": [
                    {"role": "Инициатор", "department": "Любой отдел"},
                    {"role": "Менеджер по закупкам", "department": "Отдел закупок"},
                ],
                "steps": [
                    {"name": "Формирование заявки", "performer": "Инициатор"},
                    {"name": "Согласование с руководителем", "performer": "Руководитель"},
                    {"name": "Обработка заявки", "performer": "Менеджер по закупкам"},
                ],
                "pain_points": [
                    {"description": "Ручной ввод данных", "severity": "high"},
                ],
            }
        ],
        "automation_requests": [],
    }


@pytest.fixture
def sample_bpmn_json():
    """Sample BPMN JSON for conversion."""
    return {
        "process_id": "Process_1",
        "process_name": "Заявка на закупку",
        "elements": [
            {"id": "start_1", "type": "startEvent", "name": "Потребность"},
            {"id": "task_1", "type": "userTask", "name": "Формирование заявки",
             "incoming": ["flow_1"], "outgoing": ["flow_2"]},
            {"id": "gw_1", "type": "exclusiveGateway", "name": "Утверждено?",
             "incoming": ["flow_2"], "outgoing": ["flow_3", "flow_4"]},
            {"id": "task_2", "type": "userTask", "name": "Обработка заявки",
             "incoming": ["flow_3"], "outgoing": ["flow_5"]},
            {"id": "end_1", "type": "endEvent", "name": "Готово",
             "incoming": ["flow_5"]},
        ],
        "flows": [
            {"id": "flow_1", "source": "start_1", "target": "task_1"},
            {"id": "flow_2", "source": "task_1", "target": "gw_1"},
            {"id": "flow_3", "source": "gw_1", "target": "task_2", "name": "Да"},
            {"id": "flow_4", "source": "gw_1", "target": "end_1", "name": "Нет",
             "condition": "rejected"},
            {"id": "flow_5", "source": "task_2", "target": "end_1"},
        ],
        "pools": [],
    }


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create temporary project directory structure."""
    for subdir in ["audio", "transcripts", "processes", "bpmn", "output"]:
        (tmp_path / subdir).mkdir()
    return tmp_path
