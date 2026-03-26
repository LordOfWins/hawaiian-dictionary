"""
Hawaiian-English AI Dictionary Web App
Streamlit application entry point.

Architecture:
    Google Sheets (4 sheets) → sheets_loader.py (cached)
    User Input → matcher.py (block check + disclaimer detection)
    Gemini API → gemini_client.py (streaming response)
    Auth → auth.py (password gate)
"""

import streamlit as st
from sheets_loader import load_all_sheets
from auth import check_auth
from matcher import check_blocked, find_disclaimers
from gemini_client import get_client, generate_stream

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
MAX_HISTORY_TURNS = 20


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────
def trim_history():
    """Keep only the last MAX_HISTORY_TURNS pairs of messages."""
    messages = st.session_state.get("messages", [])
    if len(messages) > MAX_HISTORY_TURNS * 2:
        st.session_state.messages = messages[-(MAX_HISTORY_TURNS * 2):]


# ──────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Hawaiian Dictionary",
    page_icon="🌺",
    layout="centered",
)

# ──────────────────────────────────────────────
# Load Google Sheets Data (cached by TTL)
# ──────────────────────────────────────────────
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", "")

if not SPREADSHEET_URL:
    st.error("SPREADSHEET_URL is not configured in secrets.")
    st.stop()

data = load_all_sheets(SPREADSHEET_URL)

if not data["system_prompt"]:
    st.warning("System prompt is empty. The AI may not behave as expected.")

config = data["config"]
PASSWORD = config.get("password", "")
MODEL_NAME = config.get("model", "gemini-2.5-flash")
try:
    MAX_TOKENS = int(config.get("max_tokens", "1024"))
except (ValueError, TypeError):
    MAX_TOKENS = 1024
APP_TITLE = config.get("app_title", "Hawaiian-English Dictionary")
APP_SUBTITLE = config.get("app_subtitle", "")

# ──────────────────────────────────────────────
# Authentication Gate
# ──────────────────────────────────────────────
if not check_auth(PASSWORD):
    st.stop()

# ──────────────────────────────────────────────
# Chat UI Header
# ──────────────────────────────────────────────
st.markdown(f"# 🌺 {APP_TITLE}")
if APP_SUBTITLE:
    st.caption(APP_SUBTITLE)
else:
    st.caption(f"Powered by {MODEL_NAME}")

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "This AI-powered dictionary helps you explore "
        "Hawaiian words and their English meanings.\n\n"
        "Type a **Hawaiian** or **English** word to get started."
    )
    st.markdown("---")
    st.markdown(
        "**Reference**: Based on the Pukui & Elbert "
        "Hawaiian Dictionary tradition."
    )
    st.markdown("---")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ──────────────────────────────────────────────
# Chat History Init & Display
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ──────────────────────────────────────────────
# Chat Input Processing
# ──────────────────────────────────────────────
if prompt := st.chat_input("Type a Hawaiian or English word..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Step 1: Blocked Pattern Check (no AI call)
    blocked_response = check_blocked(prompt, data["blocked_patterns"])
    if blocked_response:
        st.session_state.messages.append({
            "role": "assistant",
            "content": blocked_response,
        })
        with st.chat_message("assistant"):
            st.markdown(blocked_response)
        st.rerun()

    # Step 2: Disclaimer Detection
    disclaimers = find_disclaimers(prompt, data["word_categories"])

    # Step 3: Gemini Streaming Response
    with st.chat_message("assistant"):
        disclaimer_block = ""
        if disclaimers:
            disclaimer_block = "\n\n".join(disclaimers) + "\n\n---\n\n"
            st.markdown(disclaimer_block)

        try:
            client = get_client()
            stream = generate_stream(
                client=client,
                model_name=MODEL_NAME,
                system_prompt=data["system_prompt"],
                chat_history=st.session_state.messages,
                disclaimers=disclaimers,
                max_tokens=MAX_TOKENS,
            )
            ai_response = st.write_stream(stream)
        except Exception as e:
            ai_response = f"⚠️ Service temporarily unavailable: {str(e)}"
            st.error(ai_response)

        full_response = disclaimer_block + (ai_response or "")
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
        })

    # Step 4: Trim history
    trim_history()
