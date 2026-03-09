"""Document generation page — file list, export by choice, regenerate."""
import json
import logging
from datetime import datetime

import streamlit as st

from src.config import AppConfig, ProjectDir


def _nav(title: str):
    pages = st.session_state.get("_pages", {})
    if title in pages:
        st.switch_page(pages[title])
    else:
        st.switch_page(title)


def show_documents(project: ProjectDir, config: AppConfig):
    st.header("\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b")

    process_files = sorted(project.processes.glob("*_processes.json"))
    if not process_files:
        st.warning("Нет извлечённых процессов. Сначала извлеките процессы из расшифровок.")
        if st.button("Перейти к процессам", key="docs_go_processes"):
            _nav("Процессы")
        return

    # --- Generation controls ---
    selected = st.selectbox(
        "\u041d\u0430\u0431\u043e\u0440 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432",
        process_files,
        format_func=lambda x: x.stem,
    )

    st.markdown("**\u0422\u0438\u043f\u044b \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432:**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.checkbox("Отчёт обследования", value=True, key="chk_report")
    with c2:
        st.checkbox("Карточки процессов", value=True, key="chk_cards")
    with c3:
        gost = st.checkbox("ГОСТ 34.602-89", value=True, key="chk_gost")

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c", type="primary", key="btn_gen_docs"):
            _generate(selected, project, config, gost)
    with bc2:
        if st.button("\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c", key="btn_regen_docs"):
            _generate(selected, project, config, gost)

    st.markdown("---")

    # --- Document list ---
    st.subheader("\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b")

    doc_files = sorted(project.output.glob("*.docx"))
    if not doc_files:
        st.info("Документы ещё не сгенерированы. Выберите набор "
                "процессов выше и нажмите **Сгенерировать**.")
        return

    for doc in doc_files:
        size_kb = doc.stat().st_size / 1024
        modified = datetime.fromtimestamp(doc.stat().st_mtime).strftime("%d.%m.%Y %H:%M")

        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.markdown(f"**{doc.name}**")
        c2.markdown(f"{size_kb:.0f} \u041a\u0411")
        c3.markdown(modified)
        with open(doc, "rb") as f:
            c4.download_button(
                "\u0421\u043a\u0430\u0447\u0430\u0442\u044c",
                data=f.read(),
                file_name=doc.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"dl_{doc.name}",
            )


def _generate(process_file, project: ProjectDir, config: AppConfig, gost: bool):
    """Generate documents from processes."""
    with open(process_file, encoding="utf-8") as f:
        processes = json.load(f)

    config_dict = config.to_dict()
    config_dict["docs"]["gost_compliance"] = gost

    with st.spinner("\u0413\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432..."):
        try:
            from src.docs.doc_generator import generate_documents
            doc_files = generate_documents(processes, str(project.root), config_dict)
            st.success(f"\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u043e: {len(doc_files)} \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442(\u043e\u0432)")
        except Exception as e:
            logging.getLogger(__name__).error("Doc generation: %s", e)
            st.error("Не удалось сгенерировать документы. "
                     "Убедитесь, что процессы извлечены корректно.")
            if st.button("Повторить", key="retry_docs"):
                st.rerun()
