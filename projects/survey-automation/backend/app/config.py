"""Конфигурация приложения Survey Automation.

Загружает настройки из config.yaml и предоставляет типизированный доступ
к параметрам приложения, транскрипции, анализа и экспорта.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator


# Корневая директория backend (где лежит main.py и config.yaml)
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent


class TranscriptionConfig(BaseModel, frozen=True):
    """Настройки транскрипции аудио через faster-whisper."""

    model_size: str = Field(default="medium", description="Размер модели Whisper")
    language: str = Field(default="ru", description="Язык распознавания")
    device: str = Field(default="cuda", description="Устройство для инференса (cuda/cpu)")
    compute_type: str = Field(default="float16", description="Тип вычислений")
    beam_size: int = Field(default=5, ge=1, description="Размер луча для beam search")


class AnalysisConfig(BaseModel, frozen=True):
    """Настройки LLM-анализа через Anthropic API."""

    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Идентификатор модели Claude",
    )
    max_tokens: int = Field(default=8192, ge=1, description="Максимум токенов в ответе")
    temperature: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Температура генерации"
    )


class ExportConfig(BaseModel, frozen=True):
    """Настройки экспорта в Visio и Word."""

    visio_template: Path | None = Field(
        default=None, description="Путь к шаблону Visio (.vstx)"
    )
    word_template: Path | None = Field(
        default=None, description="Путь к шаблону Word (.docx)"
    )

    @model_validator(mode="after")
    def _resolve_template_paths(self) -> Self:
        """Преобразует относительные пути шаблонов в абсолютные от BACKEND_DIR."""
        for field_name in ("visio_template", "word_template"):
            value = getattr(self, field_name)
            if value is not None and not value.is_absolute():
                object.__setattr__(self, field_name, BACKEND_DIR / value)
        return self


class AppSettings(BaseModel, frozen=True):
    """Основные настройки приложения."""

    title: str = Field(default="Survey Automation", description="Название приложения")
    version: str = Field(default="1.0.0", description="Версия приложения")
    host: str = Field(default="0.0.0.0", description="Хост для запуска сервера")
    port: int = Field(default=8000, ge=1, le=65535, description="Порт сервера")
    data_dir: str = Field(
        default="data/projects", description="Директория хранения проектов"
    )


class AppConfig(BaseModel, frozen=True):
    """Главная конфигурация приложения, объединяющая все секции."""

    app: AppSettings = Field(default_factory=AppSettings)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    @property
    def data_dir(self) -> Path:
        """Абсолютный путь к директории данных проектов."""
        data_path = Path(self.app.data_dir)
        if data_path.is_absolute():
            return data_path
        return BACKEND_DIR / data_path


class ProjectDir:
    """Управление структурой директорий одного проекта.

    Каждый проект имеет фиксированную структуру:
        <project_root>/
            audio/          - исходные аудиофайлы интервью
            transcripts/    - результаты транскрипции (.txt, .json)
            processes/      - извлечённые бизнес-процессы (.json)
            bpmn/           - BPMN-диаграммы (.bpmn)
            visio/          - Visio-файлы (.vsdx)
            output/         - итоговые документы и отчёты
    """

    __slots__ = ("_root",)

    SUBDIRS: tuple[str, ...] = (
        "audio",
        "transcripts",
        "processes",
        "bpmn",
        "visio",
        "output",
    )

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def __repr__(self) -> str:
        return f"ProjectDir(root={self._root!r})"

    # ------------------------------------------------------------------
    # Директории
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """Корневая директория проекта."""
        return self._root

    @property
    def audio(self) -> Path:
        """Директория с аудиофайлами."""
        return self._root / "audio"

    @property
    def transcripts(self) -> Path:
        """Директория с транскрипциями."""
        return self._root / "transcripts"

    @property
    def processes(self) -> Path:
        """Директория с извлечёнными процессами."""
        return self._root / "processes"

    @property
    def bpmn(self) -> Path:
        """Директория с BPMN-диаграммами."""
        return self._root / "bpmn"

    @property
    def visio(self) -> Path:
        """Директория с Visio-файлами."""
        return self._root / "visio"

    @property
    def output(self) -> Path:
        """Директория с итоговыми документами."""
        return self._root / "output"

    # ------------------------------------------------------------------
    # Методы управления
    # ------------------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Создаёт все поддиректории проекта, если они не существуют."""
        self._root.mkdir(parents=True, exist_ok=True)
        for subdir in self.SUBDIRS:
            (self._root / subdir).mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        """Проверяет, существует ли корневая директория проекта."""
        return self._root.is_dir()

    # ------------------------------------------------------------------
    # Пути к файлам
    # ------------------------------------------------------------------

    def get_audio_path(self, name: str, ext: str = ".wav") -> Path:
        """Возвращает путь к аудиофайлу по имени."""
        return self.audio / f"{name}{ext}"

    def get_transcript_path(self, name: str, ext: str = ".json") -> Path:
        """Возвращает путь к файлу транскрипции по имени."""
        return self.transcripts / f"{name}{ext}"

    def get_process_path(self, name: str, ext: str = ".json") -> Path:
        """Возвращает путь к файлу процесса по имени."""
        return self.processes / f"{name}{ext}"

    def get_bpmn_path(self, name: str, ext: str = ".bpmn") -> Path:
        """Возвращает путь к BPMN-файлу по имени."""
        return self.bpmn / f"{name}{ext}"

    def get_visio_path(self, name: str, ext: str = ".vsdx") -> Path:
        """Возвращает путь к Visio-файлу по имени."""
        return self.visio / f"{name}{ext}"

    def get_output_path(self, name: str, ext: str = ".docx") -> Path:
        """Возвращает путь к выходному документу по имени."""
        return self.output / f"{name}{ext}"

    def list_audio_files(self) -> list[Path]:
        """Возвращает список аудиофайлов в проекте."""
        if not self.audio.is_dir():
            return []
        return sorted(
            p for p in self.audio.iterdir()
            if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
        )

    def list_transcripts(self) -> list[Path]:
        """Возвращает список файлов транскрипций."""
        if not self.transcripts.is_dir():
            return []
        return sorted(
            p for p in self.transcripts.iterdir()
            if p.is_file() and p.suffix.lower() in {".json", ".txt"}
        )

    def list_processes(self) -> list[Path]:
        """Возвращает список файлов процессов."""
        if not self.processes.is_dir():
            return []
        return sorted(
            p for p in self.processes.iterdir()
            if p.is_file() and p.suffix.lower() == ".json"
        )


def _load_config_from_yaml(path: Path) -> dict:
    """Читает YAML-файл конфигурации и возвращает словарь."""
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


@functools.lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Загружает и кэширует конфигурацию приложения из config.yaml и env переменных.

    Env переменные (Desktop режим):
      SURVEY_DATA_DIR  — абсолютный путь к директории данных пользователя
      BACKEND_PORT     — порт backend сервера

    Returns:
        AppConfig с загруженными настройками.
    """
    import os

    config_path = BACKEND_DIR / "config.yaml"
    raw = _load_config_from_yaml(config_path)

    # Поддержка env переменных для desktop режима
    if "SURVEY_DATA_DIR" in os.environ:
        data_dir = os.environ["SURVEY_DATA_DIR"]
        raw.setdefault("app", {})["data_dir"] = str(Path(data_dir) / "projects")

    if "BACKEND_PORT" in os.environ:
        try:
            raw.setdefault("app", {})["port"] = int(os.environ["BACKEND_PORT"])
        except ValueError:
            pass

    return AppConfig(**raw)


def get_project_dir(project_name: str, config: AppConfig | None = None) -> ProjectDir:
    """Создаёт ProjectDir для указанного проекта.

    Args:
        project_name: Имя проекта (используется как имя директории).
        config: Конфигурация приложения. Если не указана, загружается автоматически.

    Returns:
        ProjectDir для управления структурой проекта.
    """
    if config is None:
        config = get_config()
    return ProjectDir(config.data_dir / project_name)
