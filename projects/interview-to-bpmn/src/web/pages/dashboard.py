"""Dashboard — project hub with progress, next step, project list."""
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.config import AppConfig, ProjectDir
from src.web.components.project_manager import _switch_project


def _nav(title: str):
    """Switch page using stored StreamlitPage objects."""
    pages = st.session_state.get("_pages", {})
    if title in pages:
        st.switch_page(pages[title])
    else:
        st.switch_page(title)

# Pipeline stages definition
_STAGES = [
    ("Аудио / Текст", lambda p: p.audio_count() > 0 or p.transcript_count() > 0),
    ("Транскрипции", lambda p: p.transcript_count() > 0),
    ("Процессы", lambda p: p.process_count() > 0),
    ("BPMN-схемы", lambda p: p.bpmn_count() > 0),
    ("Документы", lambda p: p.doc_count() > 0),
]

# Next step: (hint text, target page title)
_NEXT_STEPS = [
    ("Загрузите файлы интервью", "Пайплайн"),
    ("Запустите обработку загруженных файлов", "Пайплайн"),
    ("Извлеките процессы из расшифровок", "Процессы"),
    ("Сгенерируйте BPMN-схемы", "BPMN"),
    ("Сгенерируйте документы", "Документы"),
]


def show_dashboard(project: ProjectDir, config: AppConfig):
    done, total, next_idx = _get_progress(project)

    if done == 0:
        # Empty project — show onboarding
        _show_onboarding(project)
    else:
        # Project with data — show pipeline progress
        _show_pipeline_overview(project, done, total, next_idx)

    st.markdown("---")

    # --- Project management ---
    _show_project_management(project, config)

    st.markdown("---")

    # --- All projects ---
    _show_all_projects(project, config)


def _get_progress(project: ProjectDir) -> tuple[int, int, int]:
    """Return (done, total, first_incomplete_index)."""
    results = [check(project) for _, check in _STAGES]
    done = sum(results)
    first_incomplete = next((i for i, r in enumerate(results) if not r), len(results))
    return done, len(results), first_incomplete


def _show_onboarding(project: ProjectDir):
    """Welcome screen for empty project."""
    st.header(project.name)

    st.markdown(
        "Загрузите аудиозаписи интервью или текстовые расшифровки, "
        "и система автоматически:\n"
        "1. Транскрибирует аудио в текст\n"
        "2. Извлечёт бизнес-процессы\n"
        "3. Построит BPMN-схемы\n"
        "4. Сгенерирует проектную документацию"
    )

    st.markdown("")

    if st.button(
        "Загрузить файлы",
        type="primary",
        key="btn_onboarding_upload",
        use_container_width=True,
        icon=":material/upload_file:",
    ):
        _nav("Пайплайн")


def _show_pipeline_overview(project: ProjectDir, done: int, total: int, next_idx: int):
    """Show current project progress and next action."""
    st.header(project.name)

    # Visual pipeline steps as columns
    cols = st.columns(total)
    for i, (name, check) in enumerate(_STAGES):
        is_done = check(project)
        with cols[i]:
            if is_done:
                st.markdown(f"**:green[{name}]**")
            elif i == next_idx:
                st.markdown(f"**:blue[{name}]**")
            else:
                st.markdown(f":gray[{name}]")

    # Progress bar
    st.progress(done / total if total else 0,
                text=f"{done} из {total} этапов завершено")

    # Next step with clickable navigation button
    if done < total:
        hint, target_page = _NEXT_STEPS[next_idx]
        st.info(f"Следующий шаг: {hint}")
        if st.button(
            f"Перейти к: {target_page}",
            key="btn_next_step",
            type="primary",
        ):
            _nav(target_page)
    else:
        st.success("Все этапы завершены!")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Открыть BPMN-схемы", key="btn_go_bpmn"):
                _nav("BPMN")
        with c2:
            if st.button("Открыть документы", key="btn_go_docs"):
                _nav("Документы")

    # Compact metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Аудио", project.audio_count())
    c2.metric("Расшифровок", project.transcript_count())
    c3.metric("Процессов", project.process_count())
    c4.metric("BPMN", project.bpmn_count())
    c5.metric("Документов", project.doc_count())


def _show_project_management(project: ProjectDir, config: AppConfig):
    """Project management actions in a collapsed expander."""
    with st.expander("Управление проектом"):
        if st.button("Архивировать", key=f"arc_{project.name}",
                     use_container_width=True):
            archive_dir = Path(st.session_state.get("_data_dir", config.project.data_dir)) / "_архив"
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / project.name
            if project.root.exists() and not dest.exists():
                shutil.move(str(project.root), str(dest))
                _switch_project("default")
                st.rerun()

        # Delete with confirmation
        del_key = f"dash_del_{project.name}"
        if st.session_state.get(del_key, False):
            st.warning("Вы уверены? Это действие нельзя отменить.")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("Да, удалить", key=f"dely_{project.name}",
                             use_container_width=True):
                    shutil.rmtree(project.root, ignore_errors=True)
                    st.session_state[del_key] = False
                    st.session_state.project_name = "default"
                    st.session_state.sidebar_project_select = "default"
                    st.rerun()
            with dc2:
                if st.button("Отмена", key=f"delc_{project.name}",
                             use_container_width=True):
                    st.session_state[del_key] = False
                    st.rerun()
        else:
            if st.button("Удалить проект", key=f"deln_{project.name}",
                         use_container_width=True):
                st.session_state[del_key] = True
                st.rerun()


def _show_all_projects(project: ProjectDir, config: AppConfig):
    """Show project list."""
    st.subheader("Проекты")

    base = Path(st.session_state.get("_data_dir", config.project.data_dir))
    base.mkdir(parents=True, exist_ok=True)

    project_dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not project_dirs:
        st.info("Проектов пока нет. Нажмите **Новый проект** в боковой панели.")
        return

    # Grid of project cards
    cols = st.columns(3)
    for i, pdir in enumerate(project_dirs):
        p = ProjectDir(pdir.name, st.session_state.get("_data_dir", config.project.data_dir))
        is_current = pdir.name == project.name
        with cols[i % 3]:
            _render_project_card(p, is_current)


def _render_project_card(p: ProjectDir, is_current: bool):
    """Render a compact project card."""
    results = [check(p) for _, check in _STAGES]
    done = sum(results)

    try:
        created = datetime.fromtimestamp(p.root.stat().st_ctime).strftime("%d.%m.%Y")
    except OSError:
        created = "?"

    with st.container(border=True):
        if is_current:
            st.markdown(f"**{p.name}** (текущий)")
        else:
            st.markdown(f"**{p.name}**")

        st.caption(f"{created} | {done}/5 этапов")

        if not is_current:
            if st.button("Открыть", key=f"open_{p.name}",
                         type="primary", use_container_width=True):
                _switch_project(p.name)
                st.rerun()
