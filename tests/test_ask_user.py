import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ask_user import format_decision_message


def test_format_basic_decision():
    result = format_decision_message(
        question="Which database?",
        options=["A) PostgreSQL", "B) SQLite"],
        recommendation="",
    )
    assert "🤔 Decision needed:" in result
    assert "Which database?" in result
    assert "Options:" in result
    assert "A) PostgreSQL" in result
    assert "B) SQLite" in result
    assert "Reply with A/B/C." in result
    assert "Recommendation:" not in result


def test_format_decision_with_recommendation():
    result = format_decision_message(
        question="Which approach?",
        options=["A) Fast", "B) Safe"],
        recommendation="A — faster and simpler for this scope",
    )
    assert "Recommendation:" in result
    assert "A — faster and simpler for this scope" in result


def test_format_decision_three_options():
    result = format_decision_message(
        question="Pick storage",
        options=["A) S3", "B) Local disk", "C) PostgreSQL BLOB"],
        recommendation="C — already have the connection",
    )
    assert "C) PostgreSQL BLOB" in result
    assert "C — already have the connection" in result


def test_format_options_before_recommendation():
    """Options section must appear before Recommendation in the output."""
    result = format_decision_message(
        question="Q?",
        options=["A) X", "B) Y"],
        recommendation="A — better",
    )
    options_pos = result.index("Options:")
    rec_pos = result.index("Recommendation:")
    assert options_pos < rec_pos


def test_format_no_recommendation_omits_section():
    """Empty recommendation must not add a blank Recommendation: header."""
    result = format_decision_message("Q?", ["A) X"], "")
    assert "Recommendation:" not in result


def test_format_reply_prompt_present():
    result = format_decision_message("Q?", ["A) X"], "")
    assert result.strip().endswith("Reply with A/B/C.")
