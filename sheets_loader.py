"""
Google Sheets data loader with Streamlit caching.
Loads all 4 sheets (system_prompt, word_categories, blocked_patterns, config)
in a single cached call to minimize API usage.
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import unicodedata
import re


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def _get_gspread_client() -> gspread.Client:
    """Create an authorized gspread client from Streamlit secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _normalize_hawaiian(text: str) -> str:
    """Normalize Hawaiian text for matching purposes.

    Converts to lowercase, replaces okina variants with standard
    apostrophe, and strips macrons (kahako) from vowels.
    """
    text = text.lower()
    # Normalize various okina representations
    text = text.replace("\u02BB", "'")   # ʻ modifier letter turned comma
    text = text.replace("\u2018", "'")   # left single quotation mark
    text = text.replace("\u2019", "'")   # right single quotation mark
    text = text.replace("\u0027", "'")   # basic apostrophe
    # Strip macrons (combining macron U+0304)
    text = unicodedata.normalize("NFD", text)
    text = text.replace("\u0304", "")
    text = unicodedata.normalize("NFC", text)
    return text


def _build_word_lookup(records: list[dict]) -> list[dict]:
    """Build word category lookup with pre-normalized keys and compiled regex."""
    result = []
    for row in records:
        word = str(row.get("word", "")).strip()
        if not word:
            continue
        normalized = _normalize_hawaiian(word)
        pattern = re.compile(
            r"\b" + re.escape(normalized) + r"\b",
            re.IGNORECASE,
        )
        result.append({
            "word": word,
            "normalized_word": normalized,
            "pattern": pattern,
            "category": str(row.get("category", "")),
            "disclaimer": str(row.get("disclaimer_en", "")),
        })
    return result


def _build_blocked_lookup(records: list[dict]) -> list[dict]:
    """Build blocked patterns lookup with pre-compiled regex."""
    result = []
    for row in records:
        pattern_text = str(row.get("pattern", "")).strip()
        if not pattern_text:
            continue
        pattern = re.compile(
            re.escape(pattern_text),
            re.IGNORECASE,
        )
        result.append({
            "pattern_text": pattern_text,
            "pattern": pattern,
            "response": str(row.get("response_en", "")),
        })
    return result


@st.cache_data(ttl=300, show_spinner="Loading dictionary data...")
def load_all_sheets(spreadsheet_url: str) -> dict:
    """Load all 4 sheets from Google Sheets and return structured data.

    Uses Streamlit cache with 5-minute TTL.
    """
    try:
        gc = _get_gspread_client()
        spreadsheet = gc.open_by_url(spreadsheet_url)

        # 1. system_prompt: A1=header, A2=prompt text
        ws_prompt = spreadsheet.worksheet("system_prompt")
        system_prompt = ws_prompt.acell("A2").value or ""

        # 2. word_categories: word | category | disclaimer_en
        ws_words = spreadsheet.worksheet("word_categories")
        word_records = ws_words.get_all_records()
        word_categories = _build_word_lookup(word_records)

        # 3. blocked_patterns: pattern | response_en
        ws_blocked = spreadsheet.worksheet("blocked_patterns")
        blocked_records = ws_blocked.get_all_records()
        blocked_patterns = _build_blocked_lookup(blocked_records)

        # 4. config: key | value (row-per-setting)
        ws_config = spreadsheet.worksheet("config")
        config_records = ws_config.get_all_records()
        config = {}
        for row in config_records:
            key = str(row.get("key", "")).strip()
            value = str(row.get("value", "")).strip()
            if key:
                config[key] = value

        return {
            "system_prompt": system_prompt.strip(),
            "word_categories": word_categories,
            "blocked_patterns": blocked_patterns,
            "config": config,
        }

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            "Spreadsheet not found. "
            "Check the URL and sharing permissions."
        )
        return _empty_data()
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"Worksheet not found: {e}")
        return _empty_data()
    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error: {e}")
        return _empty_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return _empty_data()


def _empty_data() -> dict:
    """Return empty fallback data structure."""
    return {
        "system_prompt": "",
        "word_categories": [],
        "blocked_patterns": [],
        "config": {},
    }
