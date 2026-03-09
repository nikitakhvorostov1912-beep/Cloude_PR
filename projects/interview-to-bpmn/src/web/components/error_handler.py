"""Global error handler — user-friendly error display, no technical details."""
import logging
import traceback
from contextlib import contextmanager

import streamlit as st

logger = logging.getLogger(__name__)

# Human-readable error messages for known exception types (NN/g guidelines)
_ERROR_MESSAGES = {
    "StreamlitDuplicateElementId": (
        "Ошибка отображения. Обновите страницу (F5)."
    ),
    "FileNotFoundError": (
        "Файл не найден. Проверьте, что все необходимые "
        "файлы загружены в проект."
    ),
    "JSONDecodeError": (
        "Не удалось прочитать данные. Файл повреждён "
        "или имеет неверный формат. Загрузите файл заново."
    ),
    "PermissionError": (
        "Нет доступа к файлу. Закройте файл в других "
        "программах и попробуйте снова."
    ),
    "ConnectionError": (
        "Нет соединения с сервером. Проверьте, что "
        "необходимые сервисы (Ollama, Whisper) запущены."
    ),
    "TimeoutError": (
        "Превышено время ожидания. Попробуйте снова "
        "или уменьшите объём данных."
    ),
    "UnicodeDecodeError": (
        "Не удалось прочитать файл. Убедитесь, что файл "
        "сохранён в формате UTF-8."
    ),
    "KeyError": (
        "Отсутствуют необходимые данные. Повторите "
        "предыдущий шаг обработки."
    ),
    "ModuleNotFoundError": (
        "Не установлен необходимый компонент. "
        "Подробности в разделе Справка."
    ),
    "ValueError": (
        "Некорректные данные. Проверьте входные файлы "
        "и настройки, затем попробуйте снова."
    ),
    "RuntimeError": (
        "Ошибка выполнения. Проверьте настройки "
        "и попробуйте снова."
    ),
    "OSError": (
        "Ошибка доступа к файловой системе. "
        "Проверьте права доступа и свободное место на диске."
    ),
}


def _get_friendly_message(exc: Exception) -> str:
    """Get a user-friendly message for an exception."""
    exc_type = type(exc).__name__
    if exc_type in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[exc_type]
    for cls in type(exc).__mro__:
        if cls.__name__ in _ERROR_MESSAGES:
            return _ERROR_MESSAGES[cls.__name__]
    return "Произошла непредвиденная ошибка. Попробуйте обновить страницу."


@contextmanager
def safe_page(page_name: str):
    """Context manager — catches exceptions, shows user-friendly message only."""
    try:
        yield
    except Exception as exc:
        logger.error(
            "Error on page '%s': %s\n%s",
            page_name,
            exc,
            traceback.format_exc(),
        )
        friendly = _get_friendly_message(exc)
        st.error(friendly)
        if st.button("Обновить страницу", key=f"retry_{page_name}"):
            st.rerun()
