"""Confirmation dialog component."""
import streamlit as st


def confirm_action(key: str, message: str, button_label: str = "\u0423\u0434\u0430\u043b\u0438\u0442\u044c") -> bool:
    """Two-step confirmation: first click shows warning, second confirms.

    Args:
        key: Unique key for session state.
        message: Warning message to display.
        button_label: Label for the confirm button.

    Returns:
        True if user confirmed the action.
    """
    state_key = f"_confirm_{key}"

    if st.session_state.get(state_key, False):
        st.warning(message)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"\u0414\u0430, {button_label.lower()}", key=f"{key}_yes"):
                st.session_state[state_key] = False
                return True
        with col2:
            if st.button("\u041e\u0442\u043c\u0435\u043d\u0430", key=f"{key}_no"):
                st.session_state[state_key] = False
        return False
    else:
        if st.button(button_label, key=f"{key}_ask"):
            st.session_state[state_key] = True
        return False
