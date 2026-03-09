"""Streamlit main application — Interview-to-BPMN.

Multi-page navigation architecture with grouped sidebar menu.
"""
import json
from pathlib import Path

import streamlit as st

from src.config import AppConfig, ProjectDir
from src.web.components.error_handler import safe_page

st.set_page_config(
    page_title="Интервью в BPMN",
    page_icon="I2B",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit default elements and raw exception tracebacks
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header [data-testid="stDeployButton"] {display: none;}
    [data-testid="manage-app-button"] {display: none;}
    .stException {display: none !important;}
</style>
""", unsafe_allow_html=True)

# Project root — resolve all relative paths from here
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SESSION_FILE = _PROJECT_ROOT / "data" / ".session.json"


@st.cache_resource
def _load_config() -> AppConfig:
    config_path = _PROJECT_ROOT / "config.yaml"
    return AppConfig.from_yaml(str(config_path))


def _load_session():
    """Restore last project name from disk."""
    if SESSION_FILE.exists():
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            return data.get("project_name", "default")
        except (json.JSONDecodeError, OSError):
            pass
    return "default"


def _save_session():
    """Persist current project name to disk."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"project_name": st.session_state.get("project_name", "default")}
    SESSION_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _resolve_data_dir(config: AppConfig) -> Path:
    """Resolve data_dir to absolute path based on project root."""
    data_dir = Path(config.project.data_dir)
    if not data_dir.is_absolute():
        data_dir = (_PROJECT_ROOT / data_dir).resolve()
    return data_dir


def _get_context() -> tuple[ProjectDir, AppConfig]:
    """Get current project and config from session state."""
    config: AppConfig = st.session_state.config
    project_name = st.session_state.get("project_name", "default")
    data_dir = st.session_state.get("_data_dir", config.project.data_dir)
    project = ProjectDir(project_name, data_dir)
    project.ensure_dirs()
    return project, config


# --- Page wrappers (no-arg functions for st.Page) ---

def _page_dashboard():
    with safe_page("Главная"):
        from src.web.pages.dashboard import show_dashboard
        project, config = _get_context()
        show_dashboard(project, config)


def _page_pipeline():
    with safe_page("Обработка"):
        from src.web.pages.pipeline import show_pipeline
        project, config = _get_context()
        show_pipeline(project, config)


def _page_transcripts():
    with safe_page("Транскрипции"):
        from src.web.pages.transcript import show_transcript
        project, config = _get_context()
        show_transcript(project, config)


def _page_processes():
    with safe_page("Процессы"):
        from src.web.pages.processes import show_processes
        project, config = _get_context()
        show_processes(project, config)


def _page_bpmn():
    with safe_page("BPMN"):
        from src.web.pages.bpmn_view import show_bpmn
        project, config = _get_context()
        show_bpmn(project, config)


def _page_documents():
    with safe_page("Документы"):
        from src.web.pages.documents import show_documents
        project, config = _get_context()
        show_documents(project, config)


def _page_help():
    with safe_page("Справка"):
        from src.web.pages.help_page import show_help
        show_help()


# --- Init session state ---
if "config" not in st.session_state:
    st.session_state.config = _load_config()
if "_data_dir" not in st.session_state:
    st.session_state._data_dir = str(_resolve_data_dir(st.session_state.config))
if "project_name" not in st.session_state:
    st.session_state.project_name = _load_session()


def main():
    config: AppConfig = st.session_state.config

    # --- Sidebar: project selector ---
    from src.web.components.project_manager import show_project_manager
    show_project_manager(config)

    _save_session()

    # --- Multi-page navigation ---
    pages = {
        "": [
            st.Page(_page_dashboard, title="Главная", icon=":material/home:", default=True),
        ],
        "Обработка данных": [
            st.Page(_page_pipeline, title="Пайплайн", icon=":material/play_circle:"),
            st.Page(_page_transcripts, title="Транскрипции", icon=":material/text_snippet:"),
        ],
        "Анализ": [
            st.Page(_page_processes, title="Процессы", icon=":material/account_tree:"),
            st.Page(_page_bpmn, title="BPMN", icon=":material/schema:"),
            st.Page(_page_documents, title="Документы", icon=":material/description:"),
        ],
        "Инструменты": [
            st.Page(_page_help, title="Справка", icon=":material/help:"),
        ],
    }

    # Store page objects for cross-page navigation (st.switch_page needs objects)
    _page_map = {}
    for group_pages in pages.values():
        for p in group_pages:
            _page_map[p.title] = p
    st.session_state["_pages"] = _page_map

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
