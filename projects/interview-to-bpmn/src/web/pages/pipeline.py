"""Pipeline page — file upload, settings, batch processing."""
import json
import logging
import shutil
import time
from pathlib import Path

import streamlit as st

from src.config import AppConfig, ProjectDir
from src.web.components.status_card import status_card


def show_pipeline(project: ProjectDir, config: AppConfig):
    st.header("Обработка")

    # --- Section 1: File upload ---
    _section_files(project, config)

    st.markdown("---")

    # --- Section 2: Settings (collapsed) ---
    _section_settings(config)

    st.markdown("---")

    # --- Section 3: Run ---
    _section_run(project, config)


def _section_files(project: ProjectDir, config: AppConfig):
    """Single file uploader for audio and text files."""
    all_types = list(config.audio.supported_formats) + ["txt", "docx"]
    uploaded = st.file_uploader(
        "Загрузите файлы интервью",
        type=all_types,
        accept_multiple_files=True,
        key="pipeline_upload",
        help="Аудио (MP3, WAV, M4A, OGG, FLAC) или текст (TXT, DOCX)",
    )

    if uploaded:
        audio_count = 0
        text_count = 0
        for f in uploaded:
            if f.name.endswith((".txt", ".docx")):
                _save_text_as_transcript(f, project)
                text_count += 1
            else:
                path = project.audio / f.name
                with open(path, "wb") as fp:
                    fp.write(f.getbuffer())
                audio_count += 1
        parts = []
        if audio_count:
            parts.append(f"аудио: {audio_count}")
        if text_count:
            parts.append(f"текст: {text_count}")
        st.success(f"Загружено: {', '.join(parts)}")

    # Folder import (advanced)
    with st.expander("Импорт из папки"):
        folder = st.text_input(
            "Путь к папке с файлами", key="pipeline_folder",
            placeholder="C:/path/to/interviews",
        )
        if folder and st.button("Импортировать", key="btn_import_folder"):
            folder_path = Path(folder)
            if folder_path.is_dir():
                import shutil
                count = 0
                for ext in config.audio.supported_formats:
                    for f in folder_path.glob(f"*.{ext}"):
                        dest = project.audio / f.name
                        if not dest.exists():
                            shutil.copy2(f, dest)
                            count += 1
                st.success(f"Импортировано: {count} файлов")
            else:
                st.error("Папка не найдена")

    # Show existing files
    _show_file_list(project)


def _section_settings(config: AppConfig):
    """Processing settings in a collapsed expander."""
    with st.expander("Настройки обработки"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Транскрипция**")
            st.selectbox(
                "Режим",
                ["local_cpu", "local", "api"],
                format_func=lambda x: {
                    "local_cpu": "CPU (Faster-Whisper)",
                    "local": "GPU-сервер",
                    "api": "OpenAI API",
                }[x],
                index=["local_cpu", "local", "api"].index(config.transcription.mode),
                key="pipe_mode",
            )
            st.selectbox(
                "Модель Whisper",
                ["tiny", "base", "small", "medium", "large-v3"],
                index=["tiny", "base", "small", "medium", "large-v3"].index(
                    config.transcription.local_cpu.model
                ),
                key="pipe_model",
            )

        with col2:
            st.markdown("**BPMN**")
            st.selectbox(
                "Уровень детализации",
                ["high_level", "detailed", "both"],
                format_func=lambda x: {
                    "high_level": "Высокоуровневый",
                    "detailed": "Детальный",
                    "both": "Оба уровня",
                }[x],
                key="pipe_detail",
            )
            st.selectbox(
                "Формат вывода",
                ["png", "svg", "pdf"],
                key="pipe_format",
            )

    # Store pipeline config in session
    st.session_state["_pipeline_config"] = {
        "mode": st.session_state.get("pipe_mode", config.transcription.mode),
        "model": st.session_state.get("pipe_model", config.transcription.local_cpu.model),
        "detail": st.session_state.get("pipe_detail", "high_level"),
        "format": st.session_state.get("pipe_format", config.bpmn.output_format),
    }


def _render_status_cards(container, stages: dict, times: dict):
    """Render all status cards into a container."""
    _CARD_LABELS = [
        ("preprocess", "Предобработка аудио"),
        ("transcribe", "Транскрипция"),
        ("analysis", "Извлечение процессов"),
        ("bpmn", "Генерация BPMN"),
        ("docs", "Генерация документов"),
    ]
    container.empty()
    with container.container():
        for key, label in _CARD_LABELS:
            status_card(label, stages.get(key, "pending"), times.get(key, ""))


def _section_run(project: ProjectDir, config: AppConfig):
    """Run processing with status cards."""
    pipe_cfg = st.session_state.get("_pipeline_config", {})

    # Determine what needs processing
    audio_files = list(project.audio.glob("*.wav")) + list(project.audio.glob("*.mp3")) + \
                  list(project.audio.glob("*.m4a")) + list(project.audio.glob("*.ogg"))
    existing_transcripts = {f.stem for f in project.transcripts.glob("*.json")}
    unprocessed = [f for f in audio_files if f.stem not in existing_transcripts]
    total_transcripts = project.transcript_count()

    has_files = project.audio_count() > 0 or total_transcripts > 0

    if has_files:
        st.markdown(
            f"**Аудио для транскрипции:** {len(unprocessed)} новых | "
            f"**Готовых транскрипций:** {total_transcripts}"
        )

    # Reset pipeline status when project changes
    current_proj = project.root.name
    if st.session_state.get("_pipeline_project") != current_proj:
        st.session_state["_pipeline_project"] = current_proj
        st.session_state.pop("_pipeline_stages", None)
        st.session_state.pop("_pipeline_times", None)

    # Status cards in a replaceable container
    stages = st.session_state.get("_pipeline_stages", {
        "preprocess": "pending",
        "transcribe": "pending",
        "analysis": "pending",
        "bpmn": "pending",
        "docs": "pending",
    })
    times = st.session_state.get("_pipeline_times", {})

    status_placeholder = st.empty()
    _render_status_cards(status_placeholder, stages, times)

    # Show persisted error message if any
    if "_pipeline_error" in st.session_state:
        st.error(st.session_state.pop("_pipeline_error"))

    # Run button
    if not has_files:
        st.info("Загрузите файлы выше для начала обработки.")
    if st.button(
        "Обработать",
        type="primary",
        disabled=not has_files,
        key="btn_run_pipeline",
        use_container_width=True,
    ):
        _run_pipeline(project, config, pipe_cfg, unprocessed, status_placeholder)


def _run_pipeline(project: ProjectDir, config: AppConfig, pipe_cfg: dict,
                   unprocessed: list, status_placeholder):
    """Execute the full processing pipeline with live status updates."""
    config_dict = config.to_dict()
    mode = pipe_cfg.get("mode", config.transcription.mode)
    model = pipe_cfg.get("model", config.transcription.local_cpu.model)
    detail = pipe_cfg.get("detail", "high_level")
    config_dict["transcription"]["mode"] = mode
    if mode == "local_cpu":
        config_dict["transcription"]["local_cpu"]["model"] = model

    stages = {k: "pending" for k in ["preprocess", "transcribe", "analysis", "bpmn", "docs"]}
    times = {}

    def _update():
        st.session_state["_pipeline_stages"] = stages
        st.session_state["_pipeline_times"] = times
        _render_status_cards(status_placeholder, stages, times)

    _update()

    # Stage 1: Preprocess
    if unprocessed:
        # Check FFmpeg availability
        if not shutil.which("ffmpeg"):
            stages["preprocess"] = "error"
            _update()
            st.error(
                "FFmpeg не найден в системе. Установите FFmpeg для обработки аудиофайлов.\n\n"
                "Скачать: https://ffmpeg.org/download.html\n\n"
                "После установки перезапустите приложение."
            )
            return

        stages["preprocess"] = "running"
        _update()
        t0 = time.time()
        try:
            from src.transcription.preprocessor import preprocess_audio
            for f in unprocessed:
                preprocess_audio(str(f), str(project.audio), config_dict)
            stages["preprocess"] = "done"
            times["preprocess"] = f"{time.time() - t0:.0f} сек"
        except Exception as e:
            stages["preprocess"] = "error"
            _update()
            logging.getLogger(__name__).error("Preprocess: %s", e)
            st.error("Не удалось обработать аудиофайлы. "
                     "Проверьте формат файлов (MP3, WAV, M4A) и попробуйте снова.")
            return
    else:
        stages["preprocess"] = "done"
        times["preprocess"] = "пропущено"
    _update()

    # Stage 2: Transcribe
    wav_files = list(project.audio.glob("*.wav"))
    existing = {f.stem for f in project.transcripts.glob("*.json")}
    to_transcribe = [f for f in wav_files if f.stem not in existing]

    if to_transcribe:
        stages["transcribe"] = "running"
        _update()
        t0 = time.time()
        try:
            from src.transcription.formatter import format_transcript
            from src.transcription.transcriber import transcribe

            progress_bar = st.progress(0, text="Транскрипция...")
            for idx, af in enumerate(to_transcribe):
                progress_bar.progress(
                    (idx) / len(to_transcribe),
                    text=f"Транскрипция: {af.name} ({idx + 1}/{len(to_transcribe)})",
                )
                raw = transcribe(str(af), config_dict)
                transcript = format_transcript(raw)
                out = project.transcripts / f"{af.stem}.json"
                with open(out, "w", encoding="utf-8") as fp:
                    json.dump(transcript, fp, ensure_ascii=False, indent=2)
            progress_bar.progress(1.0, text="Транскрипция завершена")

            stages["transcribe"] = "done"
            times["transcribe"] = f"{time.time() - t0:.0f} сек"
        except Exception as e:
            stages["transcribe"] = "error"
            _update()
            logging.getLogger(__name__).error("Transcribe: %s", e)
            st.error("Не удалось транскрибировать аудио. "
                     "Проверьте настройки транскрипции и доступность сервиса.")
            return
    else:
        stages["transcribe"] = "done"
        times["transcribe"] = "пропущено"
    _update()

    # Stage 3: Analysis
    transcript_files = list(project.transcripts.glob("*.json"))
    existing_procs = {f.stem.replace("_processes", "") for f in project.processes.glob("*_processes.json")}
    to_analyze = [f for f in transcript_files if f.stem not in existing_procs]

    if to_analyze:
        # Pre-check LLM availability
        try:
            from src.analysis.process_extractor import check_ollama_available
            check_ollama_available(config_dict)
        except Exception as e:
            stages["analysis"] = "error"
            _update()
            st.error(str(e))
            return

        stages["analysis"] = "running"
        _update()
        t0 = time.time()
        try:
            from src.analysis.process_extractor import extract_processes

            progress_bar = st.progress(0, text="Извлечение процессов...")
            for idx, tf in enumerate(to_analyze):
                progress_bar.progress(
                    (idx) / len(to_analyze),
                    text=f"Анализ: {tf.name} ({idx + 1}/{len(to_analyze)})",
                )
                with open(tf, encoding="utf-8") as fp:
                    transcript = json.load(fp)
                processes = extract_processes(transcript, config_dict)
                out = project.processes / f"{tf.stem}_processes.json"
                with open(out, "w", encoding="utf-8") as fp:
                    json.dump(processes, fp, ensure_ascii=False, indent=2)
            progress_bar.progress(1.0, text="Анализ завершён")

            stages["analysis"] = "done"
            times["analysis"] = f"{time.time() - t0:.0f} сек"
        except Exception as e:
            stages["analysis"] = "error"
            _update()
            logging.getLogger(__name__).error("Analysis: %s", e)
            st.error("Не удалось извлечь процессы. "
                     "Проверьте, что AI-сервис запущен, и попробуйте снова.")
            return
    else:
        stages["analysis"] = "done"
        times["analysis"] = "пропущено"
    _update()

    # Stage 4: BPMN
    proc_files = list(project.processes.glob("*_processes.json"))
    if proc_files:
        stages["bpmn"] = "running"
        _update()
        t0 = time.time()
        try:
            from src.analysis.process_extractor import generate_bpmn_json
            from src.bpmn.json_to_bpmn import generate_bpmn_file
            from src.bpmn.renderer import render_bpmn

            levels = ["high_level", "detailed"] if detail == "both" else [detail]
            for pf in proc_files:
                with open(pf, encoding="utf-8") as fp:
                    data = json.load(fp)
                for proc in data.get("processes", []):
                    proc_id = proc.get("id", "process_1")
                    for lvl in levels:
                        bj = generate_bpmn_json(proc, config_dict, detail_level=lvl)
                        bf = generate_bpmn_file(bj, str(project.bpmn), proc_id, lvl)
                        render_bpmn(bf, str(project.output), config_dict)

            stages["bpmn"] = "done"
            times["bpmn"] = f"{time.time() - t0:.0f} сек"
        except Exception as e:
            stages["bpmn"] = "error"
            _update()
            logging.getLogger(__name__).error("BPMN gen: %s", e)
            err_msg = (f"Не удалось сгенерировать BPMN-схемы: {e}. "
                       "Попробуйте снова или уменьшите количество процессов.")
            st.session_state["_pipeline_error"] = err_msg
            st.error(err_msg)
            return
    else:
        stages["bpmn"] = "done"
        times["bpmn"] = "пропущено"
    _update()

    # Stage 5: Documents
    if proc_files:
        stages["docs"] = "running"
        _update()
        t0 = time.time()
        try:
            from src.docs.doc_generator import generate_documents

            for pf in proc_files:
                with open(pf, encoding="utf-8") as fp:
                    data = json.load(fp)
                generate_documents(data, str(project.root), config_dict)

            stages["docs"] = "done"
            times["docs"] = f"{time.time() - t0:.0f} сек"
        except Exception as e:
            stages["docs"] = "error"
            _update()
            logging.getLogger(__name__).error("Doc gen: %s", e)
            st.error("Не удалось сгенерировать документы. "
                     "Убедитесь, что процессы извлечены корректно.")
            return
    else:
        stages["docs"] = "done"
        times["docs"] = "пропущено"
    _update()

    # Log action
    from src.web.components.project_manager import _log_action
    _log_action(project, "Полная обработка завершена")

    st.success("Обработка завершена!")


def _show_file_list(project: ProjectDir):
    """Show existing files with processing status."""
    audio_files = sorted(project.audio.glob("*"))
    transcripts = {f.stem for f in project.transcripts.glob("*.json")}

    if not audio_files and not transcripts:
        return

    st.markdown("#### Файлы в проекте")
    for af in audio_files:
        done = af.stem in transcripts
        mark = "\u2705" if done else "\u23f3"
        st.markdown(f"{mark} {af.name}")

    # Show transcript-only files (from text upload)
    audio_stems = {f.stem for f in audio_files}
    for t_name in sorted(transcripts - audio_stems):
        st.markdown(f"\u2705 {t_name}.json (текст)")


def _save_text_as_transcript(uploaded_file, project: ProjectDir):
    """Convert uploaded text file to transcript JSON format."""
    name = uploaded_file.name
    stem = Path(name).stem

    if name.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8", errors="replace")
    elif name.endswith(".docx"):
        try:
            import io

            import docx
            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            content = "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            content = uploaded_file.read().decode("utf-8", errors="replace")
    else:
        content = uploaded_file.read().decode("utf-8", errors="replace")

    transcript = {
        "text": content,
        "full_text": content,
        "segments": [{"text": content, "start": 0, "end": 0, "speaker": "Спикер_1"}],
        "dialogue": [{"speaker": "Спикер_1", "text": content, "start": "00:00:00", "end": "00:00:00"}],
        "metadata": {
            "source": name,
            "type": "text_import",
            "duration_seconds": 0,
            "language": "ru",
        },
    }

    out = project.transcripts / f"{stem}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
