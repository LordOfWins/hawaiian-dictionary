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
    page_title="Olii — Hawaiian Dictionary",
    page_icon="🌿",
    layout="centered",
)

# ──────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Chat input styling */
    .stChatInput textarea::placeholder {
        color: #8B7D6B;
    }

    /* Sidebar refinement */
    [data-testid="stSidebar"] {
        background-color: #F0EBE3;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 0.92rem;
        line-height: 1.6;
        color: #4A4340;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #1A7A6D;
        font-weight: 600;
    }

    /* Header area */
    .main-header {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
    }
    .main-header h1 {
        color: #1A7A6D;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .main-header .subtitle {
        color: #8B7D6B;
        font-size: 0.9rem;
        margin-top: 0.25rem;
    }

    /* Disclaimer block styling */
    .stAlert {
        border-radius: 8px;
    }

    /* Chat message refinement */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

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
header_title = APP_TITLE if APP_TITLE != "Hawaiian-English Dictionary" else "Olii"
st.markdown(f"""
<div class="main-header">
    <h1>🌿 {header_title}</h1>
    <div class="subtitle">{APP_SUBTITLE or "Your cultural-linguistic guide to Hawaiian"}</div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.image("olii_logo.png", use_container_width=True)
    st.markdown("")

    st.markdown("### About Olii")
    st.markdown(
        "Language is more than just a communication tool — "
        "it carries cultural identity, knowledge, and history. "
        "**Olii** was born from the belief that technology can be "
        "a guardian of culture, not a destroyer.\n\n"
        "We are not a definitive dictionary or an ultimate authority. "
        "Olii is a **patient, respectful guide**, supporting learners "
        "in approaching ʻŌlelo Hawaiʻi with clarity, care, and "
        "cultural awareness."
    )
    st.markdown("---")

    st.markdown("### The Olii Guidelines")
    st.markdown(
        "**Context First** — Cultural and situational context "
        "before direct translation.\n\n"
        "**Supportive & Suggestive** — Corrections are offered gently, "
        "never evaluatively.\n\n"
        "**Built-in Humility** — For deeper learning and sacred chants, "
        "users are directed to consult with human Kumu.\n\n"
        "**Explicit Avoidance** — No aggressive tones, exclusionary "
        "language, or authoritative voices."
    )
    st.markdown("---")

    st.markdown("### Ethical Reference")
    st.markdown(
        "Grounded in the **UN Declaration on the Rights of Indigenous "
        "Peoples** and **UNESCO AI Ethics Recommendations**.\n\n"
        "Olii maintains strict standards of accuracy, avoids "
        "unverified information, and clearly acknowledges "
        "uncertainty when necessary."
    )
    st.markdown("---")

    st.caption(
        "Reference: Pukui & Elbert Hawaiian Dictionary tradition. "
        "This tool is part of a high school anthropology project."
    )
    st.markdown("")
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
if prompt := st.chat_input("Ask Olii about a Hawaiian or English word..."):
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
