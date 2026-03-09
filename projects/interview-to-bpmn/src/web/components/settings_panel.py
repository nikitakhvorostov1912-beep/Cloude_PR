"""Compact settings panel for sidebar."""
import streamlit as st

from src.config import AppConfig


def show_settings(config: AppConfig):
    """Render compact settings toggles in sidebar."""
    with st.sidebar.expander("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"):
        # Transcription
        mode = st.selectbox(
            "\u0420\u0435\u0436\u0438\u043c \u0442\u0440\u0430\u043d\u0441\u043a\u0440\u0438\u043f\u0446\u0438\u0438",
            ["local_cpu", "local", "api"],
            format_func=lambda x: {
                "local_cpu": "CPU (Faster-Whisper)",
                "local": "GPU-\u0441\u0435\u0440\u0432\u0435\u0440",
                "api": "OpenAI API",
            }[x],
            index=["local_cpu", "local", "api"].index(config.transcription.mode),
            key="settings_mode",
        )

        model = st.selectbox(
            "\u041c\u043e\u0434\u0435\u043b\u044c Whisper",
            ["tiny", "base", "small", "medium", "large-v3"],
            index=["tiny", "base", "small", "medium", "large-v3"].index(
                config.transcription.local_cpu.model
            ),
            key="settings_model",
        )

        # Analysis
        provider = st.selectbox(
            "AI-\u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440",
            ["ollama", "anthropic"],
            format_func=lambda x: {
                "ollama": "Ollama (\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e)",
                "anthropic": "Anthropic Claude",
            }[x],
            index=["ollama", "anthropic"].index(config.analysis.provider),
            key="settings_provider",
        )

        # BPMN
        both_levels = st.toggle(
            "BPMN: \u043e\u0431\u0430 \u0443\u0440\u043e\u0432\u043d\u044f",
            value=config.bpmn.generate_both_levels,
            key="settings_both_levels",
        )

        fmt = st.selectbox(
            "\u0424\u043e\u0440\u043c\u0430\u0442 \u0432\u044b\u0432\u043e\u0434\u0430",
            ["png", "svg", "pdf"],
            index=["png", "svg", "pdf"].index(config.bpmn.output_format),
            key="settings_format",
        )

    # Store overrides in session state for pages to use
    st.session_state["_settings"] = {
        "transcription_mode": mode,
        "whisper_model": model,
        "analysis_provider": provider,
        "bpmn_both_levels": both_levels,
        "output_format": fmt,
    }
