from unittest.mock import patch


def test_answer_lifeos_question_returns_openai_response():
    with patch("app.ai_agent._call_openai", return_value="LifeOS is your personal AI OS."):
        from app.ai_agent import answer_lifeos_question
        result = answer_lifeos_question("What is LifeOS?")
    assert "LifeOS" in result


def test_answer_lifeos_question_fallback_when_no_api():
    with patch("app.ai_agent._call_openai", return_value=None):
        from app.ai_agent import answer_lifeos_question
        result = answer_lifeos_question("What is LifeOS?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_answer_with_structured_data_passes_data_to_openai():
    captured = {}

    def fake_call(system, user, max_tokens=300):
        captured["user"] = user
        return "Your net worth is €15,000."

    with patch("app.ai_agent._call_openai", side_effect=fake_call):
        from app.ai_agent import answer_lifeos_question
        answer_lifeos_question("What is my net worth?", structured_data="Live net worth: €15,000")

    assert "€15,000" in captured["user"]
    assert "What is my net worth?" in captured["user"]


def test_propose_action_includes_approve_or_cancel():
    with patch("app.ai_agent._call_openai", return_value="I'll build Module 1.2. Reply A to approve or B to cancel."):
        from app.ai_agent import propose_action
        result = propose_action("Build next module")
    assert "Reply A" in result or "A to approve" in result


def test_propose_action_fallback_includes_cancel_option():
    with patch("app.ai_agent._call_openai", return_value=None):
        from app.ai_agent import propose_action
        result = propose_action("Run tests")
    assert "B" in result  # Cancel option always present
    assert "A" in result  # Approve option always present


def test_call_openai_returns_none_when_no_key(monkeypatch):
    monkeypatch.setattr("app.config.OPENAI_API_KEY", "")
    from app.ai_agent import _call_openai
    result = _call_openai("system", "user")
    assert result is None
