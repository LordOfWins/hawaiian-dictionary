"""
Hawaiian word matching engine.
Handles blocked pattern detection and word category disclaimer matching.
"""

from sheets_loader import _normalize_hawaiian


def check_blocked(user_input: str, blocked_patterns: list[dict]) -> str | None:
    """Check if user input matches any blocked pattern.

    Blocked patterns are checked BEFORE any AI call (cost = $0).
    Returns the rejection message if matched, None otherwise.
    """
    normalized_input = _normalize_hawaiian(user_input)
    for entry in blocked_patterns:
        if entry["pattern"].search(normalized_input):
            return entry["response"]
    return None


def find_disclaimers(
    user_input: str,
    word_categories: list[dict],
) -> list[str]:
    """Find all matching disclaimers for words in user input.

    Uses pre-normalized word patterns with word boundary matching.
    Deduplicates disclaimers by content.
    """
    normalized_input = _normalize_hawaiian(user_input)
    seen = set()
    disclaimers = []
    for entry in word_categories:
        if entry["pattern"].search(normalized_input):
            disclaimer = entry["disclaimer"]
            if disclaimer and disclaimer not in seen:
                seen.add(disclaimer)
                disclaimers.append(disclaimer)
    return disclaimers
