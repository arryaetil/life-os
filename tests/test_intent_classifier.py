from app.intent_classifier import classify_intent


def test_expense_messages_are_finance_transaction():
    assert classify_intent("14 kebab") == "finance_transaction"
    assert classify_intent("8.50 coffee") == "finance_transaction"
    assert classify_intent("+314 DUO") == "finance_transaction"
    assert classify_intent("spent 25 food") == "finance_transaction"
    assert classify_intent("250 groceries") == "finance_transaction"


def test_question_messages_are_lifeos_question():
    assert classify_intent("What is my net worth?") == "lifeos_question"
    assert classify_intent("What was done last session?") == "lifeos_question"
    assert classify_intent("How does the net worth tracker work?") == "lifeos_question"
    assert classify_intent("What should we build next?") == "lifeos_question"
    assert classify_intent("Tell me about LifeOS") == "lifeos_question"
    assert classify_intent("Show me my progress") == "lifeos_question"


def test_action_messages_are_action_request():
    assert classify_intent("Build the next module") == "action_request"
    assert classify_intent("Run tests") == "action_request"
    assert classify_intent("Prepare handoff") == "action_request"
    assert classify_intent("Start working on portfolio tracker") == "action_request"
    assert classify_intent("Deploy to Railway") == "action_request"
    assert classify_intent("Create the portfolio table") == "action_request"


def test_ambiguous_short_messages_are_unknown():
    assert classify_intent("hello") == "unknown"
    assert classify_intent("great") == "unknown"
    assert classify_intent("ok") == "unknown"


def test_amount_with_many_words_not_classified_as_finance():
    # More than 6 words — even with an amount, shouldn't be auto-classed as finance
    result = classify_intent("I spent about 14 euros on kebab yesterday evening")
    assert result != "finance_transaction"
