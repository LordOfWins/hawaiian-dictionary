"""
Simple password authentication for the dictionary app.
Uses config sheet password value for access control.
"""

import streamlit as st


def check_auth(correct_password: str) -> bool:
    """Display login form and validate password.

    Manages authentication state via st.session_state.
    Once authenticated, the login form is no longer shown.
    If no password is configured, auto-authenticates.
    """
    if st.session_state.get("authenticated"):
        return True

    # No password set — skip auth
    if not correct_password:
        st.session_state["authenticated"] = True
        return True

    st.markdown("## 🔒 Hawaiian-English Dictionary")
    st.markdown("Enter the access password to continue.")

    with st.form("login_form"):
        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
        )
        submitted = st.form_submit_button(
            "Enter",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if password_input == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

    return False
