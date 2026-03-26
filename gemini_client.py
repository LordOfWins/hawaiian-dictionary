"""
Gemini API client module using the google-genai SDK.
Handles streaming content generation with dynamic system prompts.

SDK Reference: https://ai.google.dev/gemini-api/docs/text-generation?lang=python
"""

import streamlit as st
from google import genai
from google.genai import types


def get_client() -> genai.Client:
    """Create and return a Gemini API client from Streamlit secrets."""
    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(api_key=api_key)


def build_contents(chat_history: list[dict]) -> list[types.Content]:
    """Convert Streamlit chat history to Gemini Content format.

    Maps 'user' -> 'user' and 'assistant' -> 'model' roles.
    Filters out empty messages to prevent API errors.
    """
    contents = []
    for msg in chat_history:
        text = msg.get("content", "").strip()
        if not text:
            continue
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=text)],
            )
        )
    return contents


def _build_system_instruction(
    system_prompt: str,
    disclaimers: list[str] | None = None,
) -> str:
    """Build the full system instruction including disclaimer injection rules.

    If disclaimers are detected, appends an instruction to the system prompt
    telling the model to prepend them. This is a secondary safety net —
    the primary disclaimer insertion happens at the code level in app.py.
    """
    instruction = system_prompt
    if disclaimers:
        disclaimer_text = "\n".join(disclaimers)
        instruction += (
            "\n\n=== ACTIVE DISCLAIMERS ===\n"
            "The user's query involves culturally sensitive terms. "
            "The following disclaimer(s) have already been shown to the user "
            "above your response. Do NOT repeat them in your answer, but "
            "be mindful of the cultural sensitivity in your response:\n"
            f"{disclaimer_text}"
        )
    return instruction


def generate_stream(
    client: genai.Client,
    model_name: str,
    system_prompt: str,
    chat_history: list[dict],
    disclaimers: list[str] | None = None,
    max_tokens: int = 1024,
):
    """Generate streaming response from Gemini API.

    Args:
        client: Initialized Gemini client.
        model_name: Model identifier (e.g. gemini-2.0-flash).
        system_prompt: Dynamic system instruction from Google Sheet.
        chat_history: Full conversation history including current user message.
        disclaimers: List of disclaimer strings for culturally sensitive words.
        max_tokens: Maximum output tokens.

    Yields:
        str: Text chunks from the streaming response.
    """
    contents = build_contents(chat_history)
    full_instruction = _build_system_instruction(system_prompt, disclaimers)

    config = types.GenerateContentConfig(
        system_instruction=full_instruction,
        max_output_tokens=max_tokens,
        temperature=0.3,
        # Disable thinking for speed + cost efficiency on dictionary lookups
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    try:
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"\n\n⚠️ AI service error: {str(e)}"
