"""Language match rate: what fraction of results are actually written in
the language the query was issued in.

This uses a deterministic Unicode-script heuristic rather than a
statistical language-ID model. It is intentionally simple and its
limitation is stated up front (see docs/methodology.md): script presence
is a proxy for language, not a guarantee (e.g. it cannot distinguish
Hindi from Marathi, both Devanagari, and will treat transliterated or
code-mixed text as a partial match based on script ratio alone).
"""

from __future__ import annotations

# (start, end) inclusive Unicode code point ranges per script.
_SCRIPT_RANGES: dict[str, tuple[int, int]] = {
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi)
    "mr": (0x0900, 0x097F),  # Devanagari (Marathi)
    "bn": (0x0980, 0x09FF),  # Bengali
    "te": (0x0C00, 0x0C7F),  # Telugu
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "pa": (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
    "or": (0x0B00, 0x0B7F),  # Odia
}

_DEFAULT_MATCH_THRESHOLD = 0.5


def script_ratio(text: str, language: str) -> float:
    """Fraction of alphabetic characters in `text` belonging to `language`'s script.

    For "en" this is the fraction of alphabetic characters that are ASCII
    Latin letters. Returns 0.0 for empty text or an unsupported language code.
    """
    if not text:
        return 0.0
    alpha_chars = [ch for ch in text if ch.isalpha()]
    if not alpha_chars:
        return 0.0

    if language == "en":
        matches = sum(1 for ch in alpha_chars if ch.isascii())
        return matches / len(alpha_chars)

    rng = _SCRIPT_RANGES.get(language)
    if rng is None:
        return 0.0
    lo, hi = rng
    matches = sum(1 for ch in alpha_chars if lo <= ord(ch) <= hi)
    return matches / len(alpha_chars)


def is_in_language(text: str, language: str, *, threshold: float = _DEFAULT_MATCH_THRESHOLD) -> bool:
    """True if `text`'s script-match ratio for `language` clears `threshold`."""
    return script_ratio(text, language) >= threshold


def language_match_rate(
    texts: list[str], expected_language: str, *, threshold: float = _DEFAULT_MATCH_THRESHOLD
) -> float:
    """Share of non-empty texts that match `expected_language`'s script.

    Returns 0.0 if there are no non-empty texts to evaluate (an explicit
    warning should be surfaced by the caller in that case -- an empty
    result set is not the same claim as "0% language match").
    """
    non_empty = [t for t in texts if t and t.strip()]
    if not non_empty:
        return 0.0
    matches = sum(1 for t in non_empty if is_in_language(t, expected_language, threshold=threshold))
    return matches / len(non_empty)
