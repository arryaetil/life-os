import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import once before any test runs so patches work correctly
import create_handoff


def _run_handoff(monkeypatch, tmp_path, extra_args=None):
    """Run create_handoff.main() with all dependencies mocked. Returns mock_tg with call history preserved."""
    argv = ["create_handoff.py"] + (extra_args or [])
    monkeypatch.setattr(sys, "argv", argv)

    # Create the mock before the context manager so we can return it and preserve history
    mock_tg = MagicMock(return_value=True)

    with patch("create_handoff.send_telegram_message", mock_tg), \
         patch("create_handoff.write_agent_state"), \
         patch("create_handoff.read_latest_agent_state", return_value=None), \
         patch("create_handoff._git", return_value="abc123 commit"), \
         patch.object(create_handoff, "HANDOFF_PATH", tmp_path / "latest.md"), \
         patch.object(create_handoff, "STARTUP_PROMPT_PATH", tmp_path / "prompt.md"):
        create_handoff.main()

    return mock_tg


def test_silent_mode_skips_telegram(monkeypatch, tmp_path):
    mock_tg = _run_handoff(monkeypatch, tmp_path, extra_args=["--silent"])
    mock_tg.assert_not_called()


def test_normal_mode_sends_telegram(monkeypatch, tmp_path):
    mock_tg = _run_handoff(monkeypatch, tmp_path, extra_args=[])
    mock_tg.assert_called_once()


def test_silent_mode_still_writes_handoff_file(monkeypatch, tmp_path):
    _run_handoff(monkeypatch, tmp_path, extra_args=["--silent"])
    assert (tmp_path / "latest.md").exists()
