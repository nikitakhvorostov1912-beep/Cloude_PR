"""Project management sidebar component."""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.config import AppConfig, ProjectDir


def _get_data_dir(config: AppConfig) -> str:
    """Get resolved data_dir from session state or config."""
    return st.session_state.get("_data_dir", config.project.data_dir)


def _get_projects(config: AppConfig) -> list[str]:
    """List all existing projects."""
    base = Path(_get_data_dir(config))
    if not base.exists():
        return []
    return sorted([
        d.name for d in base.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ])


def _log_action(project: ProjectDir, action: str):
    """Append action to project history log."""
    log_path = project.root / "history.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _switch_project(name: str):
    """Switch to a project by name."""
    st.session_state.project_name = name


def show_project_manager(config: AppConfig) -> ProjectDir:
    """Render project selector in sidebar. Returns current ProjectDir."""
    data_dir = _get_data_dir(config)
    projects = _get_projects(config)

    st.sidebar.markdown("### Проект")

    if projects:
        current = st.session_state.get("project_name", projects[0])
        if current not in projects:
            current = projects[0]
            st.session_state.project_name = current

        selected = st.sidebar.selectbox(
            "Выберите проект",
            projects,
            index=projects.index(current),
            label_visibility="collapsed",
        )
        st.session_state.project_name = selected
    else:
        st.session_state.project_name = "default"
        st.session_state["_show_create_project"] = True

    # "New project" button — always visible, clear text
    if st.sidebar.button(
        "Новый проект",
        key="sidebar_add_proj",
        use_container_width=True,
        icon=":material/add:",
    ):
        st.session_state["_show_create_project"] = True
        st.rerun()

    # Inline create form (only when button is clicked)
    if st.session_state.get("_show_create_project", False):
        new_name = st.sidebar.text_input(
            "Название проекта",
            key="sidebar_new_proj",
            placeholder="Например: Компания_Альфа",
        )
        c1, c2 = st.sidebar.columns(2)
        with c1:
            if c1.button("Создать", key="sidebar_create_proj",
                         disabled=not (new_name and new_name.strip()),
                         use_container_width=True):
                new_proj = ProjectDir(new_name.strip(), data_dir)
                new_proj.ensure_dirs()
                _log_action(new_proj, "Создан проект")
                _switch_project(new_name.strip())
                st.session_state["_show_create_project"] = False
                st.rerun()
        with c2:
            if c2.button("Отмена", key="sidebar_cancel_proj",
                         use_container_width=True):
                st.session_state["_show_create_project"] = False
                st.rerun()

    project = ProjectDir(st.session_state.project_name, data_dir)
    project.ensure_dirs()

    return project
