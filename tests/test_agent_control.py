from app.agent_control import is_agent_reply


def test_single_letters_are_replies():
    for letter in ("A", "B", "C", "D", "a", "b", "c", "d"):
        assert is_agent_reply(letter) is True, f"Expected {letter!r} to be a reply"


def test_done_case_insensitive():
    assert is_agent_reply("DONE") is True
    assert is_agent_reply("done") is True
    assert is_agent_reply("Done") is True


def test_yes_no_are_replies():
    assert is_agent_reply("yes") is True
    assert is_agent_reply("no") is True
    assert is_agent_reply("YES") is True


def test_approve_variants():
    assert is_agent_reply("approve") is True
    assert is_agent_reply("approved") is True
    assert is_agent_reply("reject") is True


def test_continue_stop():
    assert is_agent_reply("continue") is True
    assert is_agent_reply("stop") is True


def test_expense_message_is_not_reply():
    assert is_agent_reply("14 kebab") is False
    assert is_agent_reply("spent 8.50 coffee") is False
    assert is_agent_reply("net worth 15000") is False


def test_whitespace_is_trimmed():
    assert is_agent_reply("  A  ") is True
    assert is_agent_reply("  done  ") is True


def test_empty_string_is_not_reply():
    assert is_agent_reply("") is False


def test_partial_match_is_not_reply():
    assert is_agent_reply("ab") is False
    assert is_agent_reply("donezo") is False


def test_sentence_starting_with_reply_token_is_not_reply():
    assert is_agent_reply("A great idea") is False
    assert is_agent_reply("yes please") is False
