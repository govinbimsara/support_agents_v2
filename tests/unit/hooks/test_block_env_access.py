"""Unit tests for the PreToolUse secrets guard (project secrets policy).

The hook is run as a subprocess exactly as Claude Code runs it: JSON on stdin, exit code 2
means the call is blocked. Payloads are built in memory; no env file is ever opened.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "block_env_access.py"
BLOCKED_EXIT = 2
ALLOWED_EXIT = 0

# Every .env* file is off limits, .env.example included: tell the user the variable names.
ENV_FILES = [".env", ".env.example"]
ORDINARY_FILES = ["README.md", "app/config/loader.py"]


def _payload(tool: str, target: str) -> dict[str, Any]:
    if tool == "Read":
        tool_input: dict[str, Any] = {"file_path": target}
    elif tool == "Edit":
        tool_input = {"file_path": target, "old_string": "a", "new_string": "b"}
    elif tool == "Write":
        tool_input = {"file_path": target, "content": "x"}
    else:
        tool_input = {"command": f"cat {target}"}
    return {"tool_name": tool, "tool_input": tool_input}


def _run_hook(payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write", "Bash"])
@pytest.mark.parametrize("target", ENV_FILES)
def test_secrets_policy_blocks_every_env_file_for_every_tool(tool: str, target: str) -> None:
    result = _run_hook(_payload(tool, target))

    assert result.returncode == BLOCKED_EXIT
    assert "BLOCKED" in result.stderr


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write", "Bash"])
@pytest.mark.parametrize("target", ORDINARY_FILES)
def test_secrets_policy_allows_ordinary_files(tool: str, target: str) -> None:
    result = _run_hook(_payload(tool, target))

    assert result.returncode == ALLOWED_EXIT
    assert result.stderr == ""


def test_secrets_policy_block_message_tells_the_agent_to_name_variables_not_read_files() -> None:
    result = _run_hook(_payload("Read", ".env.example"))

    assert "variable" in result.stderr
    assert "Only .env.example is allowed" not in result.stderr


def test_secrets_policy_allows_writing_text_that_merely_mentions_an_env_file() -> None:
    """Only the target path of an edit matters, so docs and .gitignore text stay writable."""
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "docs/notes.md", "content": "set the variable in .env"},
    }

    assert _run_hook(payload).returncode == ALLOWED_EXIT
