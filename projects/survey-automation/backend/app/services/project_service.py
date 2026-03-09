"""Сервис управления проектами."""

from __future__ import annotations

import json
import logging
import shutil

import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import ProjectDir, get_config, get_project_dir
from app.exceptions import NotFoundError, ProcessingError, ValidationError

logger = logging.getLogger(__name__)


class ProjectService:
    """Управление жизненным циклом проектов.

    Каждый проект хранится в директории ``data/projects/{id}/``
    и описывается файлом ``project.json``.
    """

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    async def create_project(
        self,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Создаёт новый проект с директориями и метаданными.

        Args:
            name: Название проекта.
            description: Описание проекта (опционально).

        Returns:
            Словарь с метаданными созданного проекта.

        Raises:
            ValidationError: Если название пустое.
            ProcessingError: При ошибке создания директорий или файла.
        """
        if not name or not name.strip():
            raise ValidationError(
                "Название проекта не может быть пустым",
            )

        project_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()

        project_data: dict[str, Any] = {
            "id": project_id,
            "name": name.strip(),
            "description": description.strip(),
            "created_at": now,
            "updated_at": now,
            "status": "new",
            "pipeline_state": {
                "stage": None,
                "progress": 0,
                "completed_stages": [],
            },
        }

        project_dir = get_project_dir(project_id)

        try:
            project_dir.ensure_dirs()
        except OSError as exc:
            raise ProcessingError(
                "Ошибка при создании директорий проекта",
                detail=str(exc),
            ) from exc

        await self._save_project_json(project_dir, project_data)

        logger.info("Проект создан: id=%s, name=%s", project_id, name)
        return project_data

    async def list_projects(self) -> list[dict[str, Any]]:
        """Возвращает список всех проектов с краткой информацией.

        Returns:
            Список словарей с метаданными каждого проекта.
        """
        config = get_config()
        data_dir = config.data_dir

        if not data_dir.is_dir():
            return []

        projects: list[dict[str, Any]] = []

        for child in sorted(data_dir.iterdir()):
            if not child.is_dir():
                continue
            project_json_path = child / "project.json"
            if not project_json_path.is_file():
                continue
            try:
                data = await self._load_json(project_json_path)
                projects.append({
                    "id": data.get("id", child.name),
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "status": data.get("status", "new"),
                    "pipeline_state": data.get("pipeline_state", {}),
                })
            except Exception as exc:
                logger.warning(
                    "Не удалось прочитать проект %s: %s",
                    child.name,
                    exc,
                )
                continue

        return projects

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Возвращает полные данные проекта.

        Args:
            project_id: Идентификатор проекта.

        Returns:
            Словарь с метаданными и статусом конвейера.

        Raises:
            NotFoundError: Если проект не найден.
        """
        project_dir = self._ensure_project_exists(project_id)
        project_json_path = project_dir.root / "project.json"
        return await self._load_json(project_json_path)

    async def delete_project(self, project_id: str) -> None:
        """Удаляет проект и все его файлы.

        Args:
            project_id: Идентификатор проекта.

        Raises:
            NotFoundError: Если проект не найден.
            ProcessingError: При ошибке удаления.
        """
        project_dir = self._ensure_project_exists(project_id)

        try:
            shutil.rmtree(project_dir.root)
        except OSError as exc:
            raise ProcessingError(
                "Ошибка при удалении проекта",
                detail=str(exc),
            ) from exc

        logger.info("Проект удалён: id=%s", project_id)

    async def update_project(
        self,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Обновляет метаданные проекта.

        Args:
            project_id: Идентификатор проекта.
            data: Словарь с полями для обновления (name, description, status).

        Returns:
            Обновлённые данные проекта.

        Raises:
            NotFoundError: Если проект не найден.
            ProcessingError: При ошибке сохранения.
        """
        project_dir = self._ensure_project_exists(project_id)
        project_json_path = project_dir.root / "project.json"
        project_data = await self._load_json(project_json_path)

        # Обновляем только разрешённые поля
        allowed_fields = {"name", "description", "status", "pipeline_state"}
        for key, value in data.items():
            if key in allowed_fields:
                project_data[key] = value

        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        await self._save_project_json(project_dir, project_data)
        logger.info("Проект обновлён: id=%s", project_id)
        return project_data

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_project_exists(project_id: str) -> ProjectDir:
        """Проверяет, что проект существует, и возвращает его директорию.

        Raises:
            NotFoundError: Если проект не найден.
        """
        project_dir = get_project_dir(project_id)
        if not project_dir.exists():
            raise NotFoundError(
                f"Проект не найден: {project_id}",
                detail={"project_id": project_id},
            )
        return project_dir

    async def _save_project_json(
        self,
        project_dir: ProjectDir,
        data: dict[str, Any],
    ) -> Path:
        """Сохраняет project.json в корне директории проекта."""
        json_path = project_dir.root / "project.json"
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
                await f.write(content)
        except OSError as exc:
            raise ProcessingError(
                "Ошибка сохранения метаданных проекта",
                detail=str(exc),
            ) from exc
        return json_path

    async def _load_json(self, path: Path) -> dict[str, Any]:
        """Загружает и парсит JSON-файл."""
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProcessingError(
                f"Некорректный JSON в файле: {path.name}",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка чтения файла: {path.name}",
                detail=str(exc),
            ) from exc

        if not isinstance(data, dict):
            raise ProcessingError(
                f"Ожидается JSON-объект в файле: {path.name}",
                detail=f"Получен тип: {type(data).__name__}",
            )
        return data
