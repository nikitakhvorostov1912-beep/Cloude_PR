"""Process extraction and editing page — accordions, inline editing, AS IS/TO BE."""
import json
import logging

import streamlit as st

from src.config import AppConfig, ProjectDir


def _nav(title: str):
    pages = st.session_state.get("_pages", {})
    if title in pages:
        st.switch_page(pages[title])
    else:
        st.switch_page(title)


def show_processes(project: ProjectDir, config: AppConfig):
    st.header("\u041f\u0440\u043e\u0446\u0435\u0441\u0441\u044b")

    transcript_files = sorted(project.transcripts.glob("*.json"))
    if not transcript_files:
        st.warning("Нет расшифровок. Сначала загрузите и обработайте файлы.")
        if st.button("Перейти к загрузке файлов", key="proc_go_pipeline"):
            _nav("Пайплайн")
        return

    config_dict = config.to_dict()

    # --- Actions row ---
    selected_transcript = st.selectbox(
        "\u0420\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0430 \u0434\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430",
        transcript_files,
        format_func=lambda x: x.stem,
    )

    process_files = sorted(project.processes.glob("*_processes.json"))

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("\u0418\u0437\u0432\u043b\u0435\u0447\u044c AS IS", type="primary", key="btn_extract_as_is"):
            _extract_as_is(selected_transcript, project, config_dict)
    with c2:
        if process_files:
            if st.button("\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c TO BE", key="btn_gen_to_be"):
                _generate_to_be(process_files[-1], project, config_dict)
    with c3:
        if process_files:
            if st.button("\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c", key="btn_regen_proc"):
                _extract_as_is(selected_transcript, project, config_dict)

    st.markdown("---")

    # --- AS IS / TO BE side by side ---
    as_is_files = sorted(project.processes.glob("*_processes.json"))
    to_be_files = sorted(project.processes.glob("*_to_be.json"))

    if not as_is_files and not to_be_files:
        st.info("Процессы ещё не извлечены. Выберите расшифровку выше "
               "и нажмите **Извлечь AS IS** для автоматического анализа.")
        return

    if as_is_files and to_be_files:
        # Side by side comparison
        col_as, col_to = st.columns(2)
        with col_as:
            st.subheader("AS IS")
            _show_process_list(as_is_files[-1], project, key_prefix="as_is")
        with col_to:
            st.subheader("TO BE")
            _show_process_list(to_be_files[-1], project, key_prefix="to_be", editable=False)
    elif as_is_files:
        _show_process_list(as_is_files[-1], project, key_prefix="as_is")
    elif to_be_files:
        _show_process_list(to_be_files[-1], project, key_prefix="to_be", editable=False)


def _extract_as_is(transcript_path, project: ProjectDir, config_dict: dict):
    """Extract AS IS processes from transcript."""
    with st.spinner("AI \u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u0440\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0443..."):
        try:
            with open(transcript_path, encoding="utf-8") as f:
                transcript = json.load(f)

            from src.analysis.process_extractor import extract_processes
            from src.analysis.validator import validate_processes
            processes = extract_processes(transcript, config_dict)
            validation = validate_processes(processes)

            output = project.processes / f"{transcript_path.stem}_processes.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(processes, f, ensure_ascii=False, indent=2)

            st.success(f"\u0418\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u043e \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432: {validation['process_count']}")
            _show_validation(validation)

        except Exception as e:
            logging.getLogger(__name__).error("Extract AS IS: %s", e)
            st.error("Не удалось извлечь процессы. Проверьте, что AI-сервис "
                     "запущен, и попробуйте снова.")
            if st.button("Повторить", key="retry_extract"):
                st.rerun()


def _generate_to_be(process_file, project: ProjectDir, config_dict: dict):
    """Generate TO BE processes from AS IS."""
    with st.spinner("AI \u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u0435\u0442 TO BE..."):
        try:
            with open(process_file, encoding="utf-8") as f:
                as_is = json.load(f)

            from src.analysis.process_extractor import generate_to_be
            to_be = generate_to_be(as_is, config_dict)

            output = project.processes / f"{process_file.stem}_to_be.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(to_be, f, ensure_ascii=False, indent=2)

            st.success("TO BE \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u044b \u0441\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b!")
        except Exception as e:
            logging.getLogger(__name__).error("Generate TO BE: %s", e)
            st.error("Не удалось сгенерировать TO BE процессы. "
                     "Попробуйте снова.")
            if st.button("Повторить", key="retry_to_be"):
                st.rerun()


def _show_validation(validation: dict):
    """Show validation results inline."""
    if validation.get("warnings"):
        with st.expander(f"\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f ({len(validation['warnings'])})"):
            for w in validation["warnings"]:
                st.warning(w)
    if validation.get("errors"):
        for e in validation["errors"]:
            st.error(e)


def _show_process_list(file_path, project: ProjectDir, key_prefix: str = "", editable: bool = True):
    """Display processes as editable accordions."""
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    processes = data.get("processes", data.get("to_be_processes", []))
    changed = False

    for i, proc in enumerate(processes):
        proc_name = proc.get("name", f"\u041f\u0440\u043e\u0446\u0435\u0441\u0441 {i+1}")
        with st.expander(f"{proc_name} ({proc.get('type', 'as_is').upper()})"):
            if editable:
                # Editable fields
                new_name = st.text_input(
                    "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", value=proc_name,
                    key=f"{key_prefix}_name_{i}",
                )
                if new_name != proc_name:
                    proc["name"] = new_name
                    changed = True

                c1, c2 = st.columns(2)
                with c1:
                    trigger = st.text_input(
                        "\u0422\u0440\u0438\u0433\u0433\u0435\u0440", value=proc.get("trigger", ""),
                        key=f"{key_prefix}_trigger_{i}",
                    )
                    if trigger != proc.get("trigger", ""):
                        proc["trigger"] = trigger
                        changed = True
                with c2:
                    result = st.text_input(
                        "\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442", value=proc.get("result", ""),
                        key=f"{key_prefix}_result_{i}",
                    )
                    if result != proc.get("result", ""):
                        proc["result"] = result
                        changed = True
            else:
                trigger_val = proc.get("trigger", "\u041d/\u0414")
                result_val = proc.get("result", "\u041d/\u0414")
                st.markdown(f"**\u0422\u0440\u0438\u0433\u0433\u0435\u0440:** {trigger_val}")
                st.markdown(f"**\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442:** {result_val}")

            # Participants
            participants = proc.get("participants", [])
            if participants:
                st.markdown("**\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0438:**")
                for p in participants:
                    st.markdown(f"- {p.get('role', '')} ({p.get('department', '')})")

            # Steps
            steps = proc.get("steps", [])
            if steps:
                st.markdown("**\u0428\u0430\u0433\u0438 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0430:**")
                for j, step in enumerate(steps):
                    if editable:
                        new_step = st.text_input(
                            f"\u0428\u0430\u0433 {j+1}",
                            value=step.get("name", ""),
                            key=f"{key_prefix}_step_{i}_{j}",
                        )
                        if new_step != step.get("name", ""):
                            steps[j]["name"] = new_step
                            changed = True
                    else:
                        performer = f" [{step.get('performer', '')}]" if step.get("performer") else ""
                        st.markdown(f"{j+1}. {step.get('name', '')}{performer}")

            # Pain points
            pain_points = proc.get("pain_points", [])
            if pain_points:
                st.markdown("**\u041f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0435 \u0437\u043e\u043d\u044b:**")
                for pp in pain_points:
                    severity = {"high": "\u2b24", "medium": "\u25c9", "low": "\u25cb"}.get(
                        pp.get("severity", ""), "\u26aa"
                    )
                    st.markdown(f"  {severity} {pp.get('description', '')}")

    # Automation requests
    auto_requests = data.get("automation_requests", [])
    if auto_requests:
        st.markdown("#### \u0422\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f \u043a \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u0438")
        for req in auto_requests:
            priority = {"high": "\u2b24", "medium": "\u25c9", "low": "\u25cb"}.get(
                req.get("priority", ""), "\u26aa"
            )
            st.markdown(f"  {priority} {req.get('description', '')}")

    # Autosave
    if changed and editable:
        if "processes" in data:
            data["processes"] = processes
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success("\u0418\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u044b")
