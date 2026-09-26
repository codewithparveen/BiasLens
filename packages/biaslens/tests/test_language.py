from biaslens.metrics.language import (
    is_in_language,
    language_match_rate,
    script_ratio,
)

TAMIL_TEXT = "இது ஒரு சோதனை வாக்கியம்"  # "This is a test sentence"
HINDI_TEXT = "यह एक परीक्षण वाक्य है"  # Devanagari
ENGLISH_TEXT = "This is a test sentence about diabetes remedies"


def test_script_ratio_tamil_text_scores_high_for_ta() -> None:
    assert script_ratio(TAMIL_TEXT, "ta") > 0.9


def test_script_ratio_tamil_text_scores_low_for_en() -> None:
    assert script_ratio(TAMIL_TEXT, "en") < 0.1


def test_script_ratio_hindi_text_scores_high_for_hi() -> None:
    assert script_ratio(HINDI_TEXT, "hi") > 0.9


def test_script_ratio_english_text_scores_high_for_en() -> None:
    assert script_ratio(ENGLISH_TEXT, "en") > 0.9


def test_script_ratio_empty_text_is_zero() -> None:
    assert script_ratio("", "en") == 0.0


def test_script_ratio_unsupported_language_is_zero() -> None:
    assert script_ratio(ENGLISH_TEXT, "xx") == 0.0


def test_is_in_language_threshold() -> None:
    assert is_in_language(TAMIL_TEXT, "ta") is True
    assert is_in_language(TAMIL_TEXT, "en") is False


def test_language_match_rate_all_matching() -> None:
    texts = [TAMIL_TEXT, TAMIL_TEXT, TAMIL_TEXT]
    assert language_match_rate(texts, "ta") == 1.0


def test_language_match_rate_none_matching() -> None:
    texts = [ENGLISH_TEXT, ENGLISH_TEXT]
    assert language_match_rate(texts, "ta") == 0.0


def test_language_match_rate_mixed() -> None:
    texts = [TAMIL_TEXT, ENGLISH_TEXT]
    assert language_match_rate(texts, "ta") == 0.5


def test_language_match_rate_ignores_blank_entries() -> None:
    texts = [TAMIL_TEXT, "", "   "]
    assert language_match_rate(texts, "ta") == 1.0


def test_language_match_rate_no_valid_texts_is_zero() -> None:
    assert language_match_rate(["", "  "], "ta") == 0.0
    assert language_match_rate([], "ta") == 0.0
