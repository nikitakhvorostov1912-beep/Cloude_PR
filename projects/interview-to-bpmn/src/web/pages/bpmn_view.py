"""BPMN page — interactive viewer, validation, AS IS/TO BE side by side."""
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


def show_bpmn(project: ProjectDir, config: AppConfig):
    st.header("BPMN-\u0441\u0445\u0435\u043c\u044b")

    process_files = sorted(project.processes.glob("*_processes.json"))
    if not process_files:
        st.warning("Нет извлечённых процессов. Сначала извлеките процессы из расшифровок.")
        if st.button("Перейти к процессам", key="bpmn_go_processes"):
            _nav("Процессы")
        return

    # --- Controls ---
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        selected = st.selectbox(
            "\u041d\u0430\u0431\u043e\u0440 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432", process_files,
            format_func=lambda x: x.stem,
        )
    with col2:
        detail = st.selectbox(
            "\u0423\u0440\u043e\u0432\u0435\u043d\u044c",
            ["high_level", "detailed", "both"],
            format_func=lambda x: {
                "high_level": "\u0412\u0435\u0440\u0445\u043d\u0438\u0439",
                "detailed": "\u0414\u0435\u0442\u0430\u043b\u044c\u043d\u044b\u0439",
                "both": "\u041e\u0431\u0430",
            }[x],
        )
    with col3:
        fmt = st.selectbox("\u0424\u043e\u0440\u043c\u0430\u0442", ["png", "svg", "pdf"])

    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c BPMN", type="primary", key="btn_gen_bpmn"):
            _generate_bpmn(selected, project, config, detail, fmt)
    with c2:
        if st.button("\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c", key="btn_regen_bpmn"):
            _generate_bpmn(selected, project, config, detail, fmt)

    st.markdown("---")

    # --- Display diagrams ---
    # Try AS IS / TO BE side by side
    as_is_images = sorted(project.output.glob("*_overview.*")) + sorted(project.output.glob("*_high_level.*"))
    to_be_images = sorted(project.output.glob("*_to_be*.*"))

    # Filter to image files only
    img_exts = {".png", ".svg"}
    as_is_images = [f for f in as_is_images if f.suffix in img_exts]
    to_be_images = [f for f in to_be_images if f.suffix in img_exts]

    if as_is_images and to_be_images:
        col_as, col_to = st.columns(2)
        with col_as:
            st.subheader("AS IS")
            for img in as_is_images:
                _render_image(img)
        with col_to:
            st.subheader("TO BE")
            for img in to_be_images:
                _render_image(img)
    else:
        # Show all images
        all_images = sorted(f for f in project.output.iterdir() if f.suffix in img_exts)
        if all_images:
            for img in all_images:
                with st.expander(img.stem, expanded=True):
                    _render_image(img)
                    _show_downloads(img, project)
        else:
            _show_bpmn_xml_fallback(project)

    # --- Validation panel ---
    bpmn_files = sorted(project.bpmn.glob("*.bpmn"))
    if bpmn_files:
        _show_validation_panel(bpmn_files)

    # --- Export ---
    st.markdown("---")
    _show_export_section(project)


def _generate_bpmn(process_file, project: ProjectDir, config: AppConfig, detail: str, fmt: str):
    """Generate BPMN diagrams."""
    with open(process_file, encoding="utf-8") as f:
        data = json.load(f)

    config_dict = config.to_dict()
    config_dict["bpmn"]["output_format"] = fmt
    processes = data.get("processes", [])
    levels = ["high_level", "detailed"] if detail == "both" else [detail]

    progress = st.progress(0)
    total = len(processes) * len(levels)
    current = 0

    for proc in processes:
        proc_name = proc.get("name", "Процесс")
        for level in levels:
            level_name = {"high_level": "верхний", "detailed": "детальный"}.get(level, level)
            with st.spinner(f"Генерация: {proc_name} ({level_name})..."):
                try:
                    from src.analysis.process_extractor import generate_bpmn_json
                    from src.analysis.validator import validate_bpmn_json
                    from src.bpmn.json_to_bpmn import bpmn_json_to_xml
                    from src.bpmn.renderer import render_bpmn

                    bpmn_json = generate_bpmn_json(proc, config_dict, detail_level=level)
                    validation = validate_bpmn_json(bpmn_json)

                    if not validation["valid"]:
                        for err in validation["errors"]:
                            st.warning(f"Проверка схемы: {err}")

                    xml_string = bpmn_json_to_xml(bpmn_json)

                    suffix = "_detailed" if level == "detailed" else "_overview"
                    proc_id = proc.get("id", "process_1")
                    bpmn_path = project.bpmn / f"{proc_id}{suffix}.bpmn"

                    with open(bpmn_path, "w", encoding="utf-8") as f:
                        f.write(xml_string)

                    render_bpmn(str(bpmn_path), str(project.output), config_dict)
                    st.success(f"{proc_name} ({level_name})")
                except Exception as e:
                    logging.getLogger(__name__).error("BPMN gen %s: %s", proc_name, e)
                    st.error(f"Не удалось сгенерировать схему для "
                             f"'{proc_name}'. Попробуйте снова.")
                    if st.button("Повторить", key=f"retry_bpmn_{proc_name}_{level}"):
                        st.rerun()

            current += 1
            if total > 0:
                progress.progress(current / total)


def _render_image(img_file):
    """Render an image file (PNG or SVG)."""
    if img_file.suffix == ".png":
        st.image(str(img_file), use_container_width=True)
    elif img_file.suffix == ".svg":
        with open(img_file, encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)


def _show_downloads(img_file, project: ProjectDir):
    """Show download buttons for an image."""
    c1, c2 = st.columns(2)
    with c1:
        with open(img_file, "rb") as f:
            st.download_button(
                f"\u0421\u043a\u0430\u0447\u0430\u0442\u044c {img_file.suffix.upper()}",
                data=f.read(),
                file_name=img_file.name,
                key=f"dl_img_{img_file.name}",
            )
    with c2:
        bpmn_file = project.bpmn / f"{img_file.stem}.bpmn"
        if bpmn_file.exists():
            with open(bpmn_file, "rb") as f:
                st.download_button(
                    "\u0421\u043a\u0430\u0447\u0430\u0442\u044c BPMN XML",
                    data=f.read(),
                    file_name=bpmn_file.name,
                    key=f"dl_bpmn_{bpmn_file.name}",
                )


def _show_bpmn_xml_fallback(project: ProjectDir):
    """Show BPMN XML when no images available."""
    bpmn_files = sorted(project.bpmn.glob("*.bpmn"))
    if bpmn_files:
        st.info("BPMN-файлы созданы, но визуализация недоступна. "
                "Для отображения схем необходим дополнительный "
                "компонент. Подробности в разделе **Справка**.")
        for bf in bpmn_files:
            with st.expander(bf.name):
                with open(bf, encoding="utf-8") as f:
                    st.code(f.read(), language="xml")
    else:
        st.info("BPMN-схемы ещё не созданы. Извлеките процессы, "
                "затем нажмите **Сгенерировать BPMN** выше.")
        if st.button("Перейти к процессам", key="bpmn_go_processes_2"):
            _nav("Процессы")


def _show_validation_panel(bpmn_files):
    """Show validation results for BPMN files."""
    with st.expander("\u0412\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044f BPMN"):
        for bf in bpmn_files:
            try:
                # Read and try to parse XML
                with open(bf, encoding="utf-8") as f:
                    content = f.read()

                if "<definitions" in content:
                    st.markdown(f"\u2705 **{bf.name}** \u2014 \u0432\u0430\u043b\u0438\u0434\u043d\u044b\u0439 BPMN 2.0 XML")
                else:
                    st.markdown(f"\u26a0\ufe0f **{bf.name}** \u2014 \u043d\u0435 BPMN XML")
            except Exception as e:
                st.markdown(f"\u274c **{bf.name}** \u2014 {e}")


def _show_export_section(project: ProjectDir):
    """Export section with checkboxes for format selection."""
    st.markdown("**\u042d\u043a\u0441\u043f\u043e\u0440\u0442**")

    all_files = []
    for ext in ["*.png", "*.svg", "*.bpmn"]:
        if ext == "*.bpmn":
            all_files.extend(sorted(project.bpmn.glob(ext)))
        else:
            all_files.extend(sorted(project.output.glob(ext)))

    if not all_files:
        return

    for f in all_files:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"`{f.name}`")
        with open(f, "rb") as fp:
            c2.download_button(
                "\u0421\u043a\u0430\u0447\u0430\u0442\u044c",
                data=fp.read(),
                file_name=f.name,
                key=f"export_{f.name}",
            )
