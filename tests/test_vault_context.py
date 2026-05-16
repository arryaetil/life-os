from unittest.mock import patch
from app.vault_context import load_vault_context, MAX_TOTAL_CHARS


def test_returns_nonempty_string():
    ctx = load_vault_context()
    assert isinstance(ctx, str)
    assert len(ctx) > 0


def test_total_length_under_max():
    ctx = load_vault_context()
    # Allow small tolerance for section headers
    assert len(ctx) <= MAX_TOTAL_CHARS + 200


def test_missing_file_skipped():
    with patch("app.vault_context._VAULT_FILES", [("does_not_exist_xyz.md", 1000)]):
        ctx = load_vault_context()
    assert ctx == ""


def test_long_file_truncated():
    with patch("app.vault_context._VAULT_FILES", [("CLAUDE.md", 50)]):
        ctx = load_vault_context()
    assert "[...truncated]" in ctx


def test_max_total_chars_enforced():
    with patch("app.vault_context.MAX_TOTAL_CHARS", 100):
        ctx = load_vault_context()
    # Context should not balloon past the limit (with header overhead)
    assert len(ctx) < 400


def test_empty_file_list_returns_empty():
    with patch("app.vault_context._VAULT_FILES", []):
        ctx = load_vault_context()
    assert ctx == ""
