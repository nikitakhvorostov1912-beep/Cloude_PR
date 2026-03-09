"""Reusable status card component for pipeline stages."""
import streamlit as st


def status_card(
    title: str,
    status: str = "pending",
    elapsed: str = "",
    details: str = "",
):
    """Render a status card for a pipeline stage.

    Args:
        title: Stage name.
        status: One of 'pending', 'running', 'done', 'error'.
        elapsed: Elapsed time string (e.g. '12 сек').
        details: Extra detail text.
    """
    icons = {
        "pending": "\u23f3",   # hourglass
        "running": "\u25b6\ufe0f",  # play
        "done": "\u2705",      # checkmark
        "error": "\u274c",     # cross
    }
    colors = {
        "pending": "#888888",
        "running": "#4A9EF5",
        "done": "#4CAF50",
        "error": "#F44336",
    }
    status_labels = {
        "pending": "\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435",
        "running": "\u0412 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0435...",
        "done": "\u0413\u043e\u0442\u043e\u0432\u043e",
        "error": "\u041e\u0448\u0438\u0431\u043a\u0430",
    }

    icon = icons.get(status, "\u23f3")
    color = colors.get(status, "#888888")
    label = status_labels.get(status, status)

    time_str = f" &mdash; {elapsed}" if elapsed else ""

    details_html = f"<br><small style='color: #999;'>{details}</small>" if details else ""
    html = (
        f'<div style="border:1px solid {color};border-radius:8px;'
        f'padding:12px 16px;margin-bottom:8px;background:#2D2D2D;">'
        f'<span style="font-size:1.2em;">{icon}</span> '
        f'<strong>{title}</strong>'
        f'<span style="color:{color};float:right;">{label}{time_str}</span>'
        f'{details_html}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
