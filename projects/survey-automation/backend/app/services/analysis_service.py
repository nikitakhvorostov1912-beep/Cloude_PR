"""Сервис анализа: извлечение процессов, GAP, TO-BE, требования."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import aiofiles

from app.analysis.llm_client import LLMClient
from app.analysis.prompts import (
    EXTRACT_PROCESSES_PROMPT,
    GAP_ANALYSIS_PROMPT,
    GENERATE_REQUIREMENTS_PROMPT,
    GENERATE_TO_BE_PROMPT,
    SYSTEM_PROMPT,
)
from app.config import ProjectDir, get_config, get_project_dir
from app.exceptions import NotFoundError, ProcessingError

logger = logging.getLogger(__name__)


class AnalysisService:
    """Анализ транскрипций: извлечение процессов, GAP-анализ, TO-BE, требования.

    Координирует вызовы LLM для каждого этапа аналитического конвейера
    и сохраняет результаты в директорию проекта.

    Args:
        llm_client: Экземпляр LLM-клиента. Если не задан, создаётся автоматически.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client

    @property
    def llm(self) -> LLMClient:
        """Ленивая инициализация LLM-клиента."""
        if self._llm is None:
            config = get_config()
            self._llm = LLMClient(config.analysis)
        return self._llm

    # ------------------------------------------------------------------
    # Извлечение процессов
    # ------------------------------------------------------------------

    async def extract_processes(
        self,
        project_id: str,
        transcript_ids: list[str] | None = None,
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Извлекает бизнес-процессы из транскрипций проекта.

        Args:
            project_id: Идентификатор проекта.
            transcript_ids: Список ID транскрипций для анализа.
                Если None, обрабатываются все транскрипции.
            on_progress: Колбэк прогресса (current, total, message).

        Returns:
            Список извлечённых бизнес-процессов.

        Raises:
            NotFoundError: Если проект или транскрипции не найдены.
            ProcessingError: При ошибке анализа.
        """
        project_dir = self._ensure_project_exists(project_id)

        if on_progress:
            on_progress(0, 100, "Загрузка транскрипций...")

        transcripts = await self._load_transcripts(project_dir, transcript_ids)
        if not transcripts:
            raise NotFoundError(
                "Транскрипции не найдены в проекте",
                detail={"project_id": project_id},
            )

        all_processes: list[dict[str, Any]] = []
        total = len(transcripts)

        for idx, (tid, transcript_data) in enumerate(transcripts.items()):
            if on_progress:
                pct = 10 + (idx / total) * 80
                on_progress(pct, 100, f"Анализ транскрипции: {tid}...")

            transcript_text = self._extract_full_text(transcript_data)
            prompt = EXTRACT_PROCESSES_PROMPT.format(transcript_text=transcript_text)

            try:
                response = await self.llm.send_json(SYSTEM_PROMPT, prompt)
            except ProcessingError:
                raise
            except Exception as exc:
                raise ProcessingError(
                    f"Ошибка при анализе транскрипции: {tid}",
                    detail=str(exc),
                ) from exc

            processes = response.get("data", response) if not isinstance(response, list) else response
            if isinstance(processes, dict) and not isinstance(processes.get("data"), dict):
                # Ответ может быть обёрнут в {"data": [...]}
                processes = processes.get("data", [processes])
            if isinstance(processes, dict):
                processes = [processes]

            # Назначаем уникальные ID процессам
            for proc in processes:
                if not proc.get("id"):
                    proc["id"] = f"proc_{uuid4().hex[:8]}"
                proc["source_transcript"] = tid

            all_processes.extend(processes)

        if on_progress:
            on_progress(90, 100, "Сохранение процессов...")

        # Сохраняем каждый процесс как отдельный файл
        for proc in all_processes:
            await self._save_process(project_dir, proc)

        # Сохраняем общий файл со всеми процессами
        await self._save_json(
            project_dir.processes / "_all_processes.json",
            all_processes,
        )

        if on_progress:
            on_progress(100, 100, "Извлечение процессов завершено")

        logger.info(
            "Извлечено %d процессов из %d транскрипций (проект: %s)",
            len(all_processes),
            total,
            project_id,
        )
        return all_processes

    # ------------------------------------------------------------------
    # GAP-анализ
    # ------------------------------------------------------------------

    async def run_gap_analysis(
        self,
        project_id: str,
        erp_config: str = "1С:ERP",
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Проводит GAP-анализ процессов относительно конфигурации 1С.

        Args:
            project_id: Идентификатор проекта.
            erp_config: Название конфигурации 1С для сравнения.
            on_progress: Колбэк прогресса (current, total, message).

        Returns:
            Список результатов GAP-анализа по каждому процессу.

        Raises:
            NotFoundError: Если процессы не найдены.
            ProcessingError: При ошибке анализа.
        """
        project_dir = self._ensure_project_exists(project_id)
        processes = await self._load_all_processes(project_dir)

        if not processes:
            raise NotFoundError(
                "Бизнес-процессы не найдены. Сначала выполните извлечение процессов.",
                detail={"project_id": project_id},
            )

        if on_progress:
            on_progress(0, 100, "Запуск GAP-анализа...")

        all_gaps: list[dict[str, Any]] = []
        total = len(processes)

        for idx, proc in enumerate(processes):
            if on_progress:
                pct = 10 + (idx / total) * 80
                on_progress(pct, 100, f"GAP-анализ: {proc.get('name', proc.get('id'))}...")

            process_json = json.dumps(proc, ensure_ascii=False, indent=2)
            prompt = GAP_ANALYSIS_PROMPT.format(
                process_json=process_json,
                config_name=erp_config,
            )

            try:
                response = await self.llm.send_json(SYSTEM_PROMPT, prompt)
            except ProcessingError:
                raise
            except Exception as exc:
                raise ProcessingError(
                    f"Ошибка GAP-анализа процесса: {proc.get('id')}",
                    detail=str(exc),
                ) from exc

            response["process_id"] = proc.get("id", "")
            all_gaps.append(response)

        if on_progress:
            on_progress(90, 100, "Сохранение результатов GAP-анализа...")

        # Сохраняем результаты
        gaps_dir = project_dir.processes
        await self._save_json(gaps_dir / "_gap_analysis.json", all_gaps)

        for gap in all_gaps:
            pid = gap.get("process_id", "")
            if pid:
                await self._save_json(gaps_dir / f"{pid}_gap.json", gap)

        if on_progress:
            on_progress(100, 100, "GAP-анализ завершён")

        logger.info(
            "GAP-анализ завершён для %d процессов (проект: %s)",
            len(all_gaps),
            project_id,
        )
        return all_gaps

    # ------------------------------------------------------------------
    # TO-BE генерация
    # ------------------------------------------------------------------

    async def generate_tobe(
        self,
        project_id: str,
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Генерирует TO-BE процессы на основе AS-IS и GAP-анализа.

        Args:
            project_id: Идентификатор проекта.
            on_progress: Колбэк прогресса.

        Returns:
            Список TO-BE процессов.

        Raises:
            NotFoundError: Если процессы или GAP-анализ не найдены.
            ProcessingError: При ошибке генерации.
        """
        project_dir = self._ensure_project_exists(project_id)
        processes = await self._load_all_processes(project_dir)
        gaps = await self._load_gaps(project_dir)

        if not processes:
            raise NotFoundError(
                "Бизнес-процессы не найдены. Сначала выполните извлечение процессов.",
                detail={"project_id": project_id},
            )
        if not gaps:
            raise NotFoundError(
                "Результаты GAP-анализа не найдены. Сначала выполните GAP-анализ.",
                detail={"project_id": project_id},
            )

        if on_progress:
            on_progress(0, 100, "Генерация TO-BE процессов...")

        # Индексируем GAP по process_id
        gap_by_process: dict[str, dict[str, Any]] = {}
        for gap in gaps:
            pid = gap.get("process_id", "")
            if pid:
                gap_by_process[pid] = gap

        all_tobe: list[dict[str, Any]] = []
        total = len(processes)

        for idx, proc in enumerate(processes):
            pid = proc.get("id", "")
            if on_progress:
                pct = 10 + (idx / total) * 80
                on_progress(pct, 100, f"Генерация TO-BE: {proc.get('name', pid)}...")

            gap_data = gap_by_process.get(pid, {})
            process_json = json.dumps(proc, ensure_ascii=False, indent=2)
            gap_json = json.dumps(gap_data, ensure_ascii=False, indent=2)

            prompt = GENERATE_TO_BE_PROMPT.format(
                process_json=process_json,
                gap_analysis_json=gap_json,
                config_name=gap_data.get("config_name", "1С:ERP"),
            )

            try:
                response = await self.llm.send_json(SYSTEM_PROMPT, prompt)
            except ProcessingError:
                raise
            except Exception as exc:
                raise ProcessingError(
                    f"Ошибка генерации TO-BE для процесса: {pid}",
                    detail=str(exc),
                ) from exc

            response["original_process_id"] = pid
            all_tobe.append(response)

        if on_progress:
            on_progress(90, 100, "Сохранение TO-BE процессов...")

        # Сохраняем результаты
        await self._save_json(project_dir.processes / "_tobe_processes.json", all_tobe)
        for tobe in all_tobe:
            tobe_id = tobe.get("process_id", tobe.get("original_process_id", ""))
            if tobe_id:
                await self._save_json(
                    project_dir.processes / f"{tobe_id}_tobe.json",
                    tobe,
                )

        if on_progress:
            on_progress(100, 100, "Генерация TO-BE завершена")

        logger.info(
            "Сгенерировано %d TO-BE процессов (проект: %s)",
            len(all_tobe),
            project_id,
        )
        return all_tobe

    # ------------------------------------------------------------------
    # Генерация требований
    # ------------------------------------------------------------------

    async def generate_requirements(
        self,
        project_id: str,
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Генерирует лист требований на основе процессов и GAP-анализа.

        Args:
            project_id: Идентификатор проекта.
            on_progress: Колбэк прогресса.

        Returns:
            Список требований.

        Raises:
            NotFoundError: Если процессы не найдены.
            ProcessingError: При ошибке генерации.
        """
        project_dir = self._ensure_project_exists(project_id)
        processes = await self._load_all_processes(project_dir)

        if not processes:
            raise NotFoundError(
                "Бизнес-процессы не найдены. Сначала выполните извлечение процессов.",
                detail={"project_id": project_id},
            )

        if on_progress:
            on_progress(0, 100, "Генерация листа требований...")

        gaps = await self._load_gaps(project_dir)

        # Формируем данные для промпта (процессы + GAP)
        enriched_processes = []
        gap_by_process: dict[str, dict[str, Any]] = {}
        for gap in gaps:
            pid = gap.get("process_id", "")
            if pid:
                gap_by_process[pid] = gap

        for proc in processes:
            pid = proc.get("id", "")
            enriched = dict(proc)
            if pid in gap_by_process:
                enriched["gap_analysis"] = gap_by_process[pid]
            enriched_processes.append(enriched)

        processes_json = json.dumps(enriched_processes, ensure_ascii=False, indent=2)

        if on_progress:
            on_progress(20, 100, "Отправка запроса к LLM...")

        config_name = "1С:ERP"
        if gaps:
            config_name = gaps[0].get("config_name", config_name)

        prompt = GENERATE_REQUIREMENTS_PROMPT.format(
            processes_json=processes_json,
            config_name=config_name,
        )

        try:
            response = await self.llm.send_json(SYSTEM_PROMPT, prompt)
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(
                "Ошибка генерации требований",
                detail=str(exc),
            ) from exc

        requirements = response.get("requirements", [])
        if not requirements and isinstance(response, dict):
            requirements = [response]

        if on_progress:
            on_progress(80, 100, "Сохранение требований...")

        await self._save_json(project_dir.processes / "_requirements.json", response)

        if on_progress:
            on_progress(100, 100, "Генерация требований завершена")

        logger.info(
            "Сгенерировано %d требований (проект: %s)",
            len(requirements),
            project_id,
        )
        return requirements

    # ------------------------------------------------------------------
    # Чтение данных
    # ------------------------------------------------------------------

    async def get_processes(self, project_id: str) -> list[dict[str, Any]]:
        """Возвращает список сохранённых процессов проекта.

        Args:
            project_id: Идентификатор проекта.

        Returns:
            Список процессов.
        """
        project_dir = self._ensure_project_exists(project_id)
        return await self._load_all_processes(project_dir)

    async def get_process(
        self,
        project_id: str,
        process_id: str,
    ) -> dict[str, Any]:
        """Возвращает данные конкретного процесса.

        Args:
            project_id: Идентификатор проекта.
            process_id: Идентификатор процесса.

        Returns:
            Данные процесса.

        Raises:
            NotFoundError: Если процесс не найден.
        """
        project_dir = self._ensure_project_exists(project_id)
        process_path = project_dir.get_process_path(process_id)

        if not process_path.is_file():
            raise NotFoundError(
                f"Процесс не найден: {process_id}",
                detail={"project_id": project_id, "process_id": process_id},
            )
        return await self._load_json(process_path)

    async def update_process(
        self,
        project_id: str,
        process_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Обновляет данные процесса (ручное редактирование пользователем).

        Args:
            project_id: Идентификатор проекта.
            process_id: Идентификатор процесса.
            data: Словарь с обновлёнными полями.

        Returns:
            Обновлённые данные процесса.

        Raises:
            NotFoundError: Если процесс не найден.
            ProcessingError: При ошибке сохранения.
        """
        project_dir = self._ensure_project_exists(project_id)
        process_path = project_dir.get_process_path(process_id)

        if not process_path.is_file():
            raise NotFoundError(
                f"Процесс не найден: {process_id}",
                detail={"project_id": project_id, "process_id": process_id},
            )

        process_data = await self._load_json(process_path)

        # Обновляем поля (кроме id)
        for key, value in data.items():
            if key != "id":
                process_data[key] = value

        await self._save_json(process_path, process_data)
        logger.info("Процесс обновлён: %s (проект: %s)", process_id, project_id)
        return process_data

    async def get_gaps(self, project_id: str) -> list[dict[str, Any]]:
        """Возвращает результаты GAP-анализа.

        Args:
            project_id: Идентификатор проекта.

        Returns:
            Список результатов GAP-анализа.
        """
        project_dir = self._ensure_project_exists(project_id)
        return await self._load_gaps(project_dir)

    async def get_requirements(self, project_id: str) -> list[dict[str, Any]]:
        """Возвращает лист требований.

        Args:
            project_id: Идентификатор проекта.

        Returns:
            Список требований.
        """
        project_dir = self._ensure_project_exists(project_id)
        requirements_path = project_dir.processes / "_requirements.json"

        if not requirements_path.is_file():
            return []

        data = await self._load_json(requirements_path)
        if isinstance(data, dict):
            return data.get("requirements", [data])
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_project_exists(project_id: str) -> ProjectDir:
        """Проверяет существование проекта."""
        project_dir = get_project_dir(project_id)
        if not project_dir.exists():
            raise NotFoundError(
                f"Проект не найден: {project_id}",
                detail={"project_id": project_id},
            )
        return project_dir

    @staticmethod
    async def _load_transcripts(
        project_dir: ProjectDir,
        transcript_ids: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Загружает транскрипции проекта."""
        result: dict[str, dict[str, Any]] = {}

        if not project_dir.transcripts.is_dir():
            return result

        json_files = sorted(
            p for p in project_dir.transcripts.iterdir()
            if p.is_file() and p.suffix.lower() == ".json"
        )

        for jf in json_files:
            tid = jf.stem
            if transcript_ids and tid not in transcript_ids:
                continue
            try:
                async with aiofiles.open(jf, "r", encoding="utf-8") as f:
                    content = await f.read()
                data = json.loads(content)
                if isinstance(data, dict):
                    result[tid] = data
            except Exception as exc:
                logger.warning("Не удалось прочитать транскрипцию %s: %s", jf.name, exc)
                continue

        return result

    @staticmethod
    def _extract_full_text(transcript_data: dict[str, Any]) -> str:
        """Извлекает полный текст из данных транскрипции."""
        # Пробуем получить готовый полный текст
        full_text = transcript_data.get("full_text", "")
        if full_text:
            return full_text

        # Собираем из сегментов
        segments = transcript_data.get("segments", [])
        if segments:
            parts: list[str] = []
            for seg in segments:
                speaker = seg.get("speaker", "")
                text = seg.get("text", "")
                if speaker:
                    parts.append(f"{speaker}: {text}")
                else:
                    parts.append(text)
            return "\n".join(parts)

        return str(transcript_data)

    async def _load_all_processes(self, project_dir: ProjectDir) -> list[dict[str, Any]]:
        """Загружает все процессы проекта."""
        # Сначала пробуем общий файл
        all_path = project_dir.processes / "_all_processes.json"
        if all_path.is_file():
            try:
                data = await self._load_json_raw(all_path)
                if isinstance(data, list):
                    return data
            except Exception as exc:
                logger.warning("Не удалось загрузить %s: %s", all_path.name, exc)

        # Загружаем отдельные файлы процессов
        if not project_dir.processes.is_dir():
            return []

        processes: list[dict[str, Any]] = []
        for jf in sorted(project_dir.processes.iterdir()):
            if (
                jf.is_file()
                and jf.suffix.lower() == ".json"
                and not jf.name.startswith("_")
                and not jf.name.endswith("_gap.json")
                and not jf.name.endswith("_tobe.json")
            ):
                try:
                    data = await self._load_json(jf)
                    processes.append(data)
                except Exception as exc:
                    logger.warning("Не удалось прочитать процесс %s: %s", jf.name, exc)
                    continue

        return processes

    async def _load_gaps(self, project_dir: ProjectDir) -> list[dict[str, Any]]:
        """Загружает результаты GAP-анализа."""
        gaps_path = project_dir.processes / "_gap_analysis.json"
        if gaps_path.is_file():
            try:
                data = await self._load_json_raw(gaps_path)
                if isinstance(data, list):
                    return data
            except Exception as exc:
                logger.warning("Не удалось загрузить GAP-анализ %s: %s", gaps_path.name, exc)
        return []

    async def _save_process(
        self,
        project_dir: ProjectDir,
        process: dict[str, Any],
    ) -> Path:
        """Сохраняет процесс в отдельный JSON-файл."""
        pid = process.get("id", f"proc_{uuid4().hex[:8]}")
        path = project_dir.get_process_path(pid)
        await self._save_json(path, process)
        return path

    async def _save_json(self, path: Path, data: Any) -> None:
        """Сохраняет данные в JSON-файл."""
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка сохранения файла: {path.name}",
                detail=str(exc),
            ) from exc

    async def _load_json(self, path: Path) -> dict[str, Any]:
        """Загружает JSON-файл как словарь."""
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

    async def _load_json_raw(self, path: Path) -> Any:
        """Загружает JSON-файл без проверки типа (может быть list или dict)."""
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        except (json.JSONDecodeError, OSError) as exc:
            raise ProcessingError(
                f"Ошибка чтения файла: {path.name}",
                detail=str(exc),
            ) from exc
