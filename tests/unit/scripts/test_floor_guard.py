"""Unit tests for scripts/floor_guard.py (CONSTRAINTS.md floor).

Every test builds a throwaway git repo, so the guard's diff plumbing is exercised for real.
Strings the guard detects are assembled from pieces so this file never trips the guard itself.
"""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import floor_guard
from scripts.floor_guard import GuardError, run_guard

pytestmark = pytest.mark.unit

NOQA = "# no" + "qa"
TYPE_IGNORE = "# type" + ": ignore"
SKIP_MARK = "@pytest.mark." + "skip"
XFAIL_MARK = "@pytest.mark." + "xfail"
NO_COVER = "# pragma" + ": no cover"
OPEN_ITEM = "TO" + "DO"

SCRIPT = Path(floor_guard.__file__).resolve()

BASE_CONSTRAINTS = """\
# Constraints

| Dimension | Check | Threshold |
|---|---|---|
| Coverage (changed lines) | pytest-cov | >= 80% |
| Lint | ruff | zero errors |

- Floor rule: nothing is skipped

## Exceptions
| ID | Rule | Reason |
|---|---|---|
| W1 | some-rule | legacy |
"""

BASE_TEST = "def test_a():\n    assert 1 == 1\n    assert 2 == 2\n"


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "CONSTRAINTS.md", BASE_CONSTRAINTS)
    write(tmp_path, "tests/test_a.py", BASE_TEST)
    write(tmp_path, "app/mod.py", "def f() -> int:\n    return 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def rules(repo: Path) -> set[str]:
    return {f.rule for f in run_guard("main", repo)}


def test_clean_tree_is_clean(repo: Path) -> None:
    assert run_guard("main", repo) == []


def test_ordinary_change_is_clean(repo: Path) -> None:
    write(repo, "app/mod.py", "def f() -> int:\n    return 2\n")
    write(repo, "tests/test_b.py", "def test_b():\n    assert f() == 2\n")
    assert run_guard("main", repo) == []


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (f"x = 1  {NOQA}\n", "silenced-checker"),
        (f"x = 1  {NOQA}: E501\n", "silenced-checker"),
        (f"x = 1  {TYPE_IGNORE}\n", "silenced-checker"),
        (f"x = 1  {TYPE_IGNORE}[misc]\n", "silenced-checker"),
        (f"x = 1  {NO_COVER}\n", "silenced-checker"),
        (f"x = 1  {NO_COVER}  # but with a reason\n", "silenced-checker"),
        (f"# {OPEN_ITEM} later\n", "unfinished-work"),
        ("raise NotImplemented" + "Error\n", "unfinished-work"),
        ("raise NotImplemented" + "Error  # x\n", "unfinished-work"),
        ("raise NotImplemented" + "Error  # abstract hook\n", "unfinished-work"),
        ("raise NotImplemented" + "Error  # see the spec\n", "unfinished-work"),
        ("try:\n    f()\nexcept ValueError:\n    pass\n", "unfinished-work"),
        ("try:\n    f()\nexcept ValueError: pass\n", "unfinished-work"),
    ],
)
def test_added_line_is_flagged(repo: Path, content: str, expected: str) -> None:
    write(repo, "app/new.py", content)
    assert rules(repo) == {expected}


@pytest.mark.parametrize(
    "content",
    [
        f"x = 1  {NOQA}: E501  # long URL, cannot wrap\n",
        f"x = 1  {TYPE_IGNORE}[misc]  # frozen model asserted at runtime\n",
        f"# {OPEN_ITEM}(FR-TS-07) make this idempotent\n",
        "raise NotImplemented" + "Error  # abstract hook, see ADR-0003\n",
        "raise NotImplemented" + "Error  # FR-TS-07 lands with the flows slice\n",
        "raise NotImplemented" + "Error  # NFR-SEC-08\n",
        "try:\n    f()\nexcept ValueError:\n    log()\n    pass\n",
    ],
)
def test_reasoned_or_benign_line_passes(repo: Path, content: str) -> None:
    write(repo, "app/new.py", content)
    assert run_guard("main", repo) == []


def test_bare_ellipsis_flagged_in_app_only(repo: Path) -> None:
    write(repo, "app/stub.py", "def f() -> None:\n    ...\n")
    write(repo, "scripts/helper.py", "def f() -> None:\n    ...\n")
    findings = run_guard("main", repo)
    assert [(f.rule, f.file) for f in findings] == [("unfinished-work", "app/stub.py")]
    write(repo, "app/stub.py", "def f() -> None:\n    ...  # protocol method\n")
    assert [f.file for f in run_guard("main", repo)] == []


def test_markers_in_non_python_files_are_ignored(repo: Path) -> None:
    write(repo, "docs/notes.md", f"Do not use {NOQA} or {SKIP_MARK}; {OPEN_ITEM} list\n")
    assert run_guard("main", repo) == []


@pytest.mark.parametrize("marker", [SKIP_MARK, XFAIL_MARK, "@pytest.mark." + "skipif(True)"])
def test_skip_marker_in_test_is_flagged(repo: Path, marker: str) -> None:
    write(repo, "tests/test_b.py", f"import pytest\n\n{marker}\ndef test_b():\n    assert True\n")
    assert rules(repo) == {"test-made-easier"}


def test_deleted_test_file_is_flagged(repo: Path) -> None:
    (repo / "tests/test_a.py").unlink()
    assert rules(repo) == {"test-deleted"}


def test_removed_assertion_is_flagged(repo: Path) -> None:
    write(repo, "tests/test_a.py", "def test_a():\n    assert 1 == 1\n")
    findings = run_guard("main", repo)
    assert [(f.rule, f.file, f.line) for f in findings] == [
        ("assertion-removed", "tests/test_a.py", 3)
    ]


def test_moved_assertion_is_not_flagged(repo: Path) -> None:
    write(repo, "tests/test_a.py", "def test_a():\n    assert 2 == 2\n    assert 1 == 1\n")
    assert run_guard("main", repo) == []


def test_renamed_test_file_with_edits_is_not_flagged(repo: Path) -> None:
    # A move is not a loss: the assertions follow the file to its new path.
    git(repo, "mv", "tests/test_a.py", "tests/test_renamed.py")
    write(
        repo,
        "tests/test_renamed.py",
        "def test_a():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n",
    )
    assert run_guard("main", repo) == []


def test_renamed_test_file_that_loses_an_assertion_is_flagged(repo: Path) -> None:
    git(repo, "mv", "tests/test_a.py", "tests/test_renamed.py")
    write(repo, "tests/test_renamed.py", "def test_a():\n    assert 1 == 1\n")
    assert rules(repo) == {"assertion-removed"}


def test_staged_changes_are_seen(repo: Path) -> None:
    write(repo, "app/new.py", f"x = 1  {NOQA}\n")
    git(repo, "add", "app/new.py")
    assert rules(repo) == {"silenced-checker"}


def test_committed_changes_on_a_branch_are_seen(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feature")
    write(repo, "app/new.py", f"x = 1  {NOQA}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feature")
    assert rules(repo) == {"silenced-checker"}


def test_loosened_threshold_is_flagged_with_both_versions(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace(">= 80%", ">= 70%"))
    (finding,) = run_guard("main", repo)
    assert finding.rule == "threshold-loosened"
    assert ">= 80%" in finding.detail
    assert ">= 70%" in finding.detail


def test_tightened_threshold_is_silent(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace(">= 80%", ">= 90%"))
    assert run_guard("main", repo) == []


def test_threshold_with_unreadable_direction_is_reported(repo: Path) -> None:
    # "limit 3" has no direction words, so the guard cannot tell tightening from loosening.
    base = BASE_CONSTRAINTS.replace("zero errors", "limit 3")
    write(repo, "CONSTRAINTS.md", base)
    git(repo, "commit", "-q", "-am", "numbered rule")
    write(repo, "CONSTRAINTS.md", base.replace("limit 3", "limit 9"))
    assert rules(repo) == {"threshold-changed"}


def test_threshold_that_lost_its_number_is_flagged(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace(">= 80%", "high"))
    assert rules(repo) == {"threshold-removed"}


def test_maximum_threshold_raised_is_loosened(repo: Path) -> None:
    base = BASE_CONSTRAINTS.replace("zero errors", "<= 10 ms")
    write(repo, "CONSTRAINTS.md", base)
    git(repo, "commit", "-q", "-am", "latency rule")
    write(repo, "CONSTRAINTS.md", base.replace("<= 10 ms", "<= 20 ms"))
    assert rules(repo) == {"threshold-loosened"}
    write(repo, "CONSTRAINTS.md", base.replace("<= 10 ms", "<= 5 ms"))
    assert run_guard("main", repo) == []


MEASURED = """
## Measured, not yet enforced

| Metric | Today |
|---|---|
| Project coverage | 98% |
| Unit test count | 151 |

## Next section

- Floor note: kept
"""


def test_refreshing_a_measured_number_is_silent(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS + MEASURED)
    git(repo, "commit", "-q", "-am", "measured table")
    write(
        repo,
        "CONSTRAINTS.md",
        (BASE_CONSTRAINTS + MEASURED).replace("98%", "97%").replace("151", "160"),
    )
    assert run_guard("main", repo) == []


def test_dropping_a_measured_row_is_silent(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS + MEASURED)
    git(repo, "commit", "-q", "-am", "measured table")
    write(
        repo,
        "CONSTRAINTS.md",
        (BASE_CONSTRAINTS + MEASURED).replace("| Unit test count | 151 |\n", ""),
    )
    assert run_guard("main", repo) == []


def test_numbers_after_the_measured_section_are_still_checked(repo: Path) -> None:
    base = (BASE_CONSTRAINTS + MEASURED).replace("- Floor note: kept", "- Floor note: limit 3")
    write(repo, "CONSTRAINTS.md", base)
    git(repo, "commit", "-q", "-am", "numbered rule")
    write(repo, "CONSTRAINTS.md", base.replace("limit 3", "limit 9"))
    assert rules(repo) == {"threshold-changed"}


def test_moving_an_enforced_rule_into_measured_is_flagged(repo: Path) -> None:
    moved = BASE_CONSTRAINTS.replace("| Coverage (changed lines) | pytest-cov | >= 80% |\n", "")
    write(
        repo,
        "CONSTRAINTS.md",
        moved + MEASURED.replace("| Unit test count | 151 |", "| Coverage (changed lines) | 10% |"),
    )
    assert rules(repo) == {"rule-removed"}


def test_removed_rule_is_flagged(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace("| Lint | ruff | zero errors |\n", ""))
    assert rules(repo) == {"rule-removed"}


def test_removed_bullet_rule_is_flagged(repo: Path) -> None:
    write(
        repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace("- Floor rule: nothing is skipped\n", "")
    )
    assert rules(repo) == {"rule-removed"}


def test_new_exception_row_is_flagged(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS + "| W2 | other-rule | later |\n")
    assert rules(repo) == {"new-exception"}


def test_dropping_an_exception_is_silent(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace("| W1 | some-rule | legacy |\n", ""))
    assert run_guard("main", repo) == []


@pytest.mark.parametrize(
    ("fails", "message"),
    [
        (lambda a: a[0] == "diff" and "--no-index" not in a, "could not diff against"),
        (lambda a: a[0] == "ls-files", "could not list untracked"),
        (lambda a: a[0] == "diff" and "--no-index" in a, "could not diff untracked"),
    ],
    ids=["tracked-diff", "untracked-listing", "untracked-diff"],
)
def test_a_failing_git_call_cannot_run_rather_than_read_as_clean(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fails: Callable[[list[str]], bool],
    message: str,
) -> None:
    write(repo, "app/new.py", "x = 1\n")  # untracked, so the per-file diff runs too
    real_git = floor_guard._git

    def flaky(args: list[str], cwd: Path, *, diff_exit: bool = False) -> str | None:
        return None if fails(args) else real_git(args, cwd, diff_exit=diff_exit)

    monkeypatch.setattr(floor_guard, "_git", flaky)
    with pytest.raises(GuardError, match=message):
        run_guard("main", repo)
    assert floor_guard.main(["--base", "main"], cwd=repo) == 2
    assert "cannot run" in capsys.readouterr().err


def test_editing_a_rule_without_changing_its_number_is_silent(repo: Path) -> None:
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace("pytest-cov", "coverage.py"))
    assert run_guard("main", repo) == []


def test_deleting_a_non_test_file_is_silent(repo: Path) -> None:
    (repo / "app/mod.py").unlink()
    assert run_guard("main", repo) == []


def test_unreadable_constraints_file_is_still_checked(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # If the sections cannot be read, nothing is exempt: a loosened bar must still be found.
    write(repo, "CONSTRAINTS.md", BASE_CONSTRAINTS.replace(">= 80%", ">= 70%"))

    def unreadable(self: Path, *args: object, **kwargs: object) -> str:
        raise OSError("unreadable")

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert rules(repo) == {"threshold-loosened"}


def test_unknown_base_cannot_run(repo: Path) -> None:
    with pytest.raises(GuardError, match="merge base"):
        run_guard("no-such-ref", repo)


def test_outside_a_repo_cannot_run(tmp_path: Path) -> None:
    with pytest.raises(GuardError, match="git work tree"):
        run_guard("main", tmp_path)


def test_env_files_are_never_diffed(repo: Path) -> None:
    # Normally git-ignored; if one is ever untracked and visible the guard must skip it.
    write(repo, ".env.local", f"x = 1  {NOQA}\n")
    assert run_guard("main", repo) == []


def test_main_exit_codes_and_redaction(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert floor_guard.main(["--base", "main"], cwd=repo) == 0
    assert "clean" in capsys.readouterr().out

    secret = "AKIA" + "ABCDEFGHIJKLMNOP"
    write(repo, "app/new.py", f'KEY = "{secret}"  {NOQA}\n')
    assert floor_guard.main(["--base", "main"], cwd=repo) == 1
    err = capsys.readouterr().err
    assert "[silenced-checker] app/new.py:1" in err
    assert secret not in err  # source lines are reported by location, never by content

    assert floor_guard.main(["--base", "no-such-ref"], cwd=repo) == 2
    assert "cannot run" in capsys.readouterr().err


def test_cli_entry_point_exit_codes(repo: Path) -> None:
    def run(*args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, check=False
        ).returncode

    assert run("--base", "main") == 0
    write(repo, "app/new.py", f"x = 1  {NOQA}\n")
    assert run("--base", "main") == 1
    assert run("--base", "no-such-ref") == 2
