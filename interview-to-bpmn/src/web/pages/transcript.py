"""Transcript viewing and editing page — by speakers, search, inline editing."""
import json
import logging
from pathlib import Path

import streamlit as st

from src.config import AppConfig, ProjectDir


def _nav(title: str):
    pages = st.session_state.get("_pages", {})
    if title in pages:
        st.switch_page(pages[title])
    else:
        st.switch_page(title)


def show_transcript(project: ProjectDir, config: AppConfig):
    st.header("\u0422\u0440\u0430\u043d\u0441\u043a\u0440\u0438\u043f\u0446\u0438\u0438")

    transcript_files = sorted(project.transcripts.glob("*.json"))

    if not transcript_files:
        if project.audio_count() == 0:
            st.warning("Нет файлов. Загрузите аудио или текст для обработки.")
        else:
            st.warning(f"Найдено {project.audio_count()} аудиофайлов, но расшифровок нет. "
                       "Запустите обработку для создания транскрипций.")
        if st.button("Перейти к загрузке файлов", key="tr_go_pipeline"):
            _nav("Пайплайн")
        return

    # File selector + regenerate button
    col_sel, col_regen = st.columns([4, 1])
    with col_sel:
        selected_file = st.selectbox(
            "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0440\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0443",
            transcript_files,
            format_func=lambda x: x.stem,
        )
    with col_regen:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c", key="btn_regen_transcript"):
            _regenerate_transcript(selected_file, project, config)

    if not selected_file:
        return

    with open(selected_file, encoding="utf-8") as f:
        transcript = json.load(f)

    # --- Detailed statistics ---
    _show_statistics(transcript)

    st.markdown("---")

    # --- Search ---
    search = st.text_input("\u041f\u043e\u0438\u0441\u043a \u043f\u043e \u0442\u0435\u043a\u0441\u0442\u0443", key="transcript_search")

    # --- View mode ---
    view_mode = st.radio(
        "\u0420\u0435\u0436\u0438\u043c \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430",
        ["\u0414\u0438\u0430\u043b\u043e\u0433 \u043f\u043e \u0441\u043f\u0438\u043a\u0435\u0440\u0430\u043c", "\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435", "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0441\u043f\u0438\u043a\u0435\u0440\u043e\u0432"],
        horizontal=True,
    )

    if view_mode == "\u0414\u0438\u0430\u043b\u043e\u0433 \u043f\u043e \u0441\u043f\u0438\u043a\u0435\u0440\u0430\u043c":
        _show_dialogue(transcript, search)
    elif view_mode == "\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435":
        _show_inline_editor(transcript, selected_file)
    elif view_mode == "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0441\u043f\u0438\u043a\u0435\u0440\u043e\u0432":
        _show_speaker_stats(transcript)

    # --- Export ---
    st.markdown("---")
    _show_export(transcript, selected_file)


def _show_statistics(transcript: dict):
    """Show detailed transcript statistics."""
    meta = transcript.get("metadata", {})
    segments = transcript.get("segments", [])
    full_text = transcript.get("full_text", transcript.get("text", ""))

    word_count = len(full_text.split()) if full_text else 0
    speaker_count = meta.get("speaker_count", len(set(s.get("speaker", "") for s in segments)))
    duration = meta.get("total_duration_formatted", meta.get("duration_seconds", "?"))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("\u0414\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c", str(duration))
    c2.metric("\u0421\u043f\u0438\u043a\u0435\u0440\u043e\u0432", speaker_count)
    c3.metric("\u0421\u043b\u043e\u0432", word_count)
    c4.metric("\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432", len(segments))
    c5.metric("\u042f\u0437\u044b\u043a", meta.get("language", "ru"))


def _show_dialogue(transcript: dict, search: str = ""):
    """Show dialogue by speakers with color coding and search highlight."""
    dialogue = transcript.get("dialogue", [])
    segments = transcript.get("segments", [])
    speakers = transcript.get("metadata", {}).get("speakers", [])

    # Use dialogue if available, otherwise segments
    items = dialogue if dialogue else segments

    palette = ["#4A9EF5", "#F44336", "#4CAF50", "#FFC107", "#9C27B0", "#795548", "#9E9E9E", "#FF9800"]
    speaker_palette = {s: palette[i % len(palette)] for i, s in enumerate(speakers)}

    for item in items:
        speaker = item.get("speaker", "")
        text = item.get("text", "")
        time_str = item.get("start_formatted", "")

        # Search filter
        if search and search.lower() not in text.lower():
            continue

        clr = speaker_palette.get(speaker, "#9E9E9E")

        # Highlight search term
        display_text = text
        if search:
            display_text = text.replace(search, f"**{search}**")

        dot = f'<span style="color:{clr};">\u25cf</span>'
        st.markdown(f"{dot} **{speaker}** `[{time_str}]`", unsafe_allow_html=True)
        st.markdown(f"> {display_text}")
        st.markdown("")


def _show_inline_editor(transcript: dict, file_path: Path):
    """Inline editing of transcript segments with autosave."""
    segments = transcript.get("segments", [])
    dialogue = transcript.get("dialogue", [])

    # Edit dialogue or segments
    items = dialogue if dialogue else segments
    item_key = "dialogue" if dialogue else "segments"

    st.markdown("**\u041a\u043b\u0438\u043a\u043d\u0438\u0442\u0435 \u043d\u0430 \u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f. \u0418\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u044e\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438.**")

    changed = False
    for i, item in enumerate(items):
        speaker = item.get("speaker", "")
        time_str = item.get("start_formatted", "")

        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown(f"**{speaker}** `{time_str}`")
        with col2:
            new_text = st.text_input(
                f"seg_{i}",
                value=item.get("text", ""),
                key=f"edit_seg_{i}",
                label_visibility="collapsed",
            )
            if new_text != item.get("text", ""):
                items[i]["text"] = new_text
                changed = True

    # Autosave
    if changed:
        transcript[item_key] = items
        # Update full_text
        transcript["full_text"] = " ".join(item.get("text", "") for item in items)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        st.success("\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438")


def _show_speaker_stats(transcript: dict):
    """Show detailed speaker statistics."""
    stats = transcript.get("metadata", {}).get("speaker_stats", {})
    segments = transcript.get("segments", [])

    if stats:
        for speaker, data in stats.items():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("\u0421\u043f\u0438\u043a\u0435\u0440", speaker)
                c2.metric("\u0412\u0440\u0435\u043c\u044f", data.get("duration_formatted", "\u041d/\u0414"))
                c3.metric("\u0421\u043b\u043e\u0432", data.get("word_count", 0))
                c4.metric("\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432", data.get("segment_count", 0))
    elif segments:
        # Calculate from segments
        from collections import Counter
        speaker_words = Counter()
        speaker_segs = Counter()
        for seg in segments:
            sp = seg.get("speaker", "unknown")
            speaker_segs[sp] += 1
            speaker_words[sp] += len(seg.get("text", "").split())

        for sp in sorted(speaker_segs):
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("\u0421\u043f\u0438\u043a\u0435\u0440", sp)
                c2.metric("\u0421\u043b\u043e\u0432", speaker_words[sp])
                c3.metric("\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432", speaker_segs[sp])
    else:
        st.info("\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 \u043e \u0441\u043f\u0438\u043a\u0435\u0440\u0430\u0445")


def _show_export(transcript: dict, file_path: Path):
    """Export options with checkboxes."""
    st.markdown("**\u042d\u043a\u0441\u043f\u043e\u0440\u0442**")
    c1, c2, c3 = st.columns(3)

    full_text = transcript.get("full_text", transcript.get("text", ""))

    with c1:
        if full_text:
            st.download_button(
                "\u0421\u043a\u0430\u0447\u0430\u0442\u044c TXT",
                data=full_text,
                file_name=f"{file_path.stem}.txt",
                mime="text/plain",
            )
    with c2:
        st.download_button(
            "\u0421\u043a\u0430\u0447\u0430\u0442\u044c JSON",
            data=json.dumps(transcript, ensure_ascii=False, indent=2),
            file_name=file_path.name,
            mime="application/json",
        )
    with c3:
        # DOCX export placeholder
        st.download_button(
            "\u0421\u043a\u0430\u0447\u0430\u0442\u044c DOCX",
            data=full_text.encode("utf-8") if full_text else b"",
            file_name=f"{file_path.stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            disabled=not full_text,
        )


def _regenerate_transcript(file_path: Path, project: ProjectDir, config: AppConfig):
    """Regenerate transcript from audio file."""
    audio_file = project.audio / f"{file_path.stem}.wav"
    if not audio_file.exists():
        st.error("Исходный аудиофайл не найден. Перегенерация "
                 "доступна только для файлов с аудиозаписью.")
        return

    with st.spinner("\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u0442\u0440\u0430\u043d\u0441\u043a\u0440\u0438\u043f\u0446\u0438\u0438..."):
        try:
            from src.transcription.formatter import format_transcript
            from src.transcription.transcriber import transcribe

            config_dict = config.to_dict()
            raw = transcribe(str(audio_file), config_dict)
            transcript = format_transcript(raw)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            st.success("\u0422\u0440\u0430\u043d\u0441\u043a\u0440\u0438\u043f\u0446\u0438\u044f \u043f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u0430!")
            st.rerun()
        except Exception as e:
            logging.getLogger(__name__).error("Regen transcript: %s", e)
            st.error("Не удалось перегенерировать расшифровку. "
                     "Проверьте наличие аудиофайла и настройки транскрипции.")
            if st.button("Повторить", key="retry_regen_transcript"):
                st.rerun()
