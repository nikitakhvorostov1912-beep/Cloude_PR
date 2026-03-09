"""Генерация ZIP-архива со всеми документами проекта."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Any

from ..exceptions import ExportError

logger = logging.getLogger(__name__)

# Маппинг расширений файлов к папкам в архиве
_EXTENSION_TO_FOLDER: dict[str, str] = {
    ".txt": "Транскрипции",
    ".json": "Процессы",
    ".bpmn": "BPMN",
    ".vsdx": "Visio",
    ".docx": "Документы",
    ".xlsx": "Документы",
    ".pdf": "Документы",
}

# Маппинг поддиректорий проекта к папкам в архиве
_SUBDIR_TO_FOLDER: dict[str, str] = {
    "transcripts": "Транскрипции",
    "processes": "Процессы",
    "bpmn": "BPMN",
    "visio": "Visio",
    "output": "Документы",
}

# Расширения файлов, которые включаются в архив
_ALLOWED_EXTENSIONS: set[str] = {
    ".txt", ".json", ".bpmn", ".vsdx", ".docx", ".xlsx", ".pdf",
    ".xml", ".csv", ".html", ".png", ".svg",
}


class ArchiveGenerator:
    """Генератор ZIP-архива со всеми документами проекта.

    Собирает все сгенерированные файлы из директории проекта
    и упаковывает их в ZIP-архив с логичной структурой папок
    и корректными русскими именами файлов.

    Example::

        gen = ArchiveGenerator()
        path = gen.generate_zip(
            project_dir=Path("data/projects/ERP-внедрение"),
            project_name="ERP-внедрение",
            output_path=Path("output/ERP-внедрение.zip"),
        )
    """

    def generate_zip(
        self,
        project_dir: Path,
        project_name: str,
        output_path: Path,
    ) -> Path:
        """Генерирует ZIP-архив со всеми документами проекта.

        Args:
            project_dir: Корневая директория проекта с поддиректориями
                (transcripts/, processes/, bpmn/, visio/, output/).
            project_name: Название проекта (используется как корневая
                папка внутри архива).
            output_path: Путь для сохранения .zip файла.

        Returns:
            Путь к созданному ZIP-архиву.

        Raises:
            ExportError: При ошибке создания архива.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            files_added = 0
            files_skipped = 0

            with zipfile.ZipFile(
                str(output_path),
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as zf:
                for subdir_name, archive_folder in _SUBDIR_TO_FOLDER.items():
                    subdir_path = project_dir / subdir_name
                    if not subdir_path.is_dir():
                        logger.debug(
                            "Поддиректория не найдена, пропуск: %s", subdir_path
                        )
                        continue

                    added, skipped = self._add_directory_to_zip(
                        zf=zf,
                        source_dir=subdir_path,
                        archive_root=project_name,
                        archive_folder=archive_folder,
                    )
                    files_added += added
                    files_skipped += skipped

                # Добавляем файлы из корня проекта (если есть)
                added_root, skipped_root = self._add_root_files(
                    zf=zf,
                    project_dir=project_dir,
                    archive_root=project_name,
                )
                files_added += added_root
                files_skipped += skipped_root

            logger.info(
                "ZIP-архив создан: %s (файлов: %d, пропущено: %d)",
                output_path,
                files_added,
                files_skipped,
            )
            return output_path

        except Exception as exc:
            logger.exception("Ошибка создания ZIP-архива: %s", exc)
            raise ExportError(
                "Ошибка при создании ZIP-архива проекта",
                detail=str(exc),
            ) from exc

    def _add_directory_to_zip(
        self,
        zf: zipfile.ZipFile,
        source_dir: Path,
        archive_root: str,
        archive_folder: str,
    ) -> tuple[int, int]:
        """Добавляет содержимое директории в ZIP-архив.

        Args:
            zf: Открытый ZipFile для записи.
            source_dir: Исходная директория с файлами.
            archive_root: Корневая папка в архиве (название проекта).
            archive_folder: Папка назначения в архиве.

        Returns:
            Кортеж (добавлено, пропущено).
        """
        added = 0
        skipped = 0

        for file_path in sorted(source_dir.rglob("*")):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in _ALLOWED_EXTENSIONS:
                logger.debug("Файл пропущен (неподдерживаемое расширение): %s", file_path)
                skipped += 1
                continue

            try:
                # Относительный путь внутри поддиректории
                relative = file_path.relative_to(source_dir)
                # Путь в архиве: ПроектName/Папка/файл
                archive_name = f"{archive_root}/{archive_folder}/{relative}"
                # Нормализуем разделители
                archive_name = archive_name.replace("\\", "/")

                zf.write(str(file_path), archive_name)
                added += 1
                logger.debug("Добавлен в архив: %s -> %s", file_path, archive_name)

            except Exception as exc:
                logger.warning(
                    "Не удалось добавить файл в архив: %s (%s)",
                    file_path,
                    exc,
                )
                skipped += 1

        return added, skipped

    def _add_root_files(
        self,
        zf: zipfile.ZipFile,
        project_dir: Path,
        archive_root: str,
    ) -> tuple[int, int]:
        """Добавляет файлы из корня проекта в архив.

        Файлы из корня проекта (не в поддиректориях) добавляются
        в соответствующую папку архива по расширению.

        Args:
            zf: Открытый ZipFile для записи.
            project_dir: Корневая директория проекта.
            archive_root: Корневая папка в архиве.

        Returns:
            Кортеж (добавлено, пропущено).
        """
        added = 0
        skipped = 0

        for file_path in sorted(project_dir.iterdir()):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            if ext not in _ALLOWED_EXTENSIONS:
                continue

            try:
                # Определяем папку по расширению
                folder = _EXTENSION_TO_FOLDER.get(ext, "Документы")
                archive_name = f"{archive_root}/{folder}/{file_path.name}"
                archive_name = archive_name.replace("\\", "/")

                zf.write(str(file_path), archive_name)
                added += 1

            except Exception as exc:
                logger.warning(
                    "Не удалось добавить корневой файл в архив: %s (%s)",
                    file_path,
                    exc,
                )
                skipped += 1

        return added, skipped
