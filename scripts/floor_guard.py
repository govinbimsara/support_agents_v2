#!/usr/bin/env python3
"""Floor guard: diff-scoped enforcement of the CONSTRAINTS.md floor.

Compares the working tree (staged, unstaged and untracked files included) with the merge
base of ``--base`` and HEAD, and reports every move that lowers the quality bar:

* silenced-checker: a new noqa / type-ignore comment without a trailing reason comment, or a
  coverage / scanner / secret-scan suppression of any kind.
* test-made-easier: a skip or xfail marker added to a test, a test file deleted, or more
  assertions removed from a test file than were added to it.
* unfinished-work: a stub that raises NotImplementedError, an exception handler that
  swallows the error, a bare ``...`` body in app code, or an open-item marker (the to-do
  or fix-me word) that carries no ticket ID.
* threshold-loosened / threshold-removed / threshold-changed / rule-removed: a rule in
  CONSTRAINTS.md made weaker or deleted.
* new-exception: a new row in the CONSTRAINTS.md exceptions table.

Tightening is silent; only moves that loosen the bar are reported.

Exit codes: 0 clean, 1 at least one violation, 2 the guard could not run (no git work tree,
no merge base). A 2 must never be read as a 0.

Source lines are reported by file and line number only, never by content, so a secret that
sits on a flagged line cannot leak into CI logs. Lines of CONSTRAINTS.md are quoted because
the old and new rule text is the finding.

Usage: python scripts/floor_guard.py [--base origin/main]
Requirement: NFR-QUA (CONSTRAINTS.md floor). Stdlib only, so it runs before ``uv sync``.
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

EXIT_CLEAN = 0
EXIT_VIOLATION = 1
EXIT_CANNOT_RUN = 2


class GuardError(Exception):
    """The guard could not determine the diff (reported as exit code 2)."""


@dataclass(frozen=True)
class Line:
    """One added or removed line of the diff."""

    file: str
    text: str
    number: int
    prev: str | None = None  # previous added line in the same hunk (added lines only)


@dataclass(frozen=True)
class Finding:
    rule: str
    file: str
    line: int
    detail: str = ""  # populated only for CONSTRAINTS.md findings


# --- Git plumbing -----------------------------------------------------------------------


def _git(args: list[str], cwd: Path, *, diff_exit: bool = False) -> str | None:
    """Run git; None on failure. ``diff_exit`` accepts exit 1 (a --no-index diff that differs)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode == 0 or (diff_exit and proc.returncode == 1):
        return proc.stdout
    return None


def _is_env_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith(".env") and name != ".env.example"


def collect_diff(base: str, cwd: Path) -> str:
    """Unified diff of merge-base..working tree, plus untracked files (git diff cannot see them).

    Raises GuardError rather than returning an empty diff: "could not diff" is not "clean".
    """
    top = _git(["rev-parse", "--show-toplevel"], cwd)
    if not top or not top.strip():
        raise GuardError("not inside a git work tree")
    root = Path(top.strip())

    merge_base = _git(["merge-base", base, "HEAD"], root)
    if not merge_base or not merge_base.strip():
        raise GuardError(f"no merge base against {base} (shallow clone or unknown ref?)")

    tracked = _git(["diff", "--unified=0", merge_base.strip(), "--"], root)
    if tracked is None:
        raise GuardError("could not diff against the merge base")

    listing = _git(["ls-files", "--others", "--exclude-standard"], root)
    if listing is None:
        raise GuardError("could not list untracked files")

    parts = [tracked]
    for name in filter(None, listing.splitlines()):
        if _is_env_file(name):  # defence in depth: never open a secrets file
            continue
        diff = _git(["diff", "--no-index", "--unified=0", "/dev/null", name], root, diff_exit=True)
        if diff is None:
            raise GuardError(f"could not diff untracked file {name}")
        parts.append(diff)
    return "\n".join(parts)


_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _path(raw: str) -> str:
    raw = raw.split("\t")[0]
    return raw[2:] if raw[:2] in ("a/", "b/") else raw


def parse_diff(diff: str) -> tuple[list[Line], list[Line], list[str]]:
    """Return (added, removed, deleted-files).

    ``---`` / ``+++`` are file headers only between a ``diff`` line and its first hunk; inside
    a hunk every line is content, so an added ``++i`` or a removed ``-- comment`` is a change.
    """
    added: list[Line] = []
    removed: list[Line] = []
    deleted: list[str] = []
    in_header = False
    file = old_file = ""
    old_no = new_no = 0
    prev: str | None = None

    for raw in diff.splitlines():
        if raw.startswith("diff "):
            in_header, file, old_file, prev = True, "", "", None
            continue
        hunk = _HUNK.match(raw)
        if hunk:
            in_header, prev = False, None
            old_no, new_no = int(hunk[1]), int(hunk[2])
            continue
        if in_header:
            if raw.startswith("--- "):
                old_file = _path(raw[4:])
            elif raw.startswith("+++ "):
                new = _path(raw[4:])
                file = old_file if new == "/dev/null" else new
                if new == "/dev/null":
                    deleted.append(old_file)
            continue
        if raw.startswith("+"):
            added.append(Line(file, raw[1:], new_no, prev))
            prev = raw[1:]
            new_no += 1
        elif raw.startswith("-"):
            removed.append(Line(file, raw[1:], old_no))
            old_no += 1
    return added, removed, deleted


# --- Source rules (Python patterns; the diff plumbing above is stack-agnostic) -----------
# Patterns avoid spelling out the strings they detect (a character class such as TOD[O]) so
# this file never flags itself.

# Suppressions allowed only when a second comment on the same line gives the reason.
_REASONED = re.compile(
    r"#\s*(?:noqa(?::\s*[A-Z][A-Z0-9]*(?:\s*,\s*[A-Z][A-Z0-9]*)*)?"
    r"|type:\s*ignore(?:\[[^\]]+\])?)(?P<rest>.*)$"
)
_HAS_REASON = re.compile(r"#\s*\S")
# Suppressions that are never allowed without an exception (they hide coverage or scan results).
_NEVER = re.compile(
    r"pragma:\s*no\s*cover|no[s]emgrep|gitleaks:[a]llow|#\s*ruff:\s*noqa|#\s*mypy:\s*ignore-errors"
)
_SKIP = re.compile(
    r"@pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.(?:skip|xfail)\(|@unittest\.skip"
)
_NOT_IMPLEMENTED = re.compile(r"\braise\s+NotImplemented(?:Error)?\b(?!.*#\s*\S)")
_EXCEPT_PASS_INLINE = re.compile(r"\bexcept\b[^#]*:\s*pass\b")
_EXCEPT_HEAD = re.compile(r"^\s*except\b.*:\s*$")
_BARE_PASS = re.compile(r"^\s*pass\s*$")
_UNFINISHED_MARKER = re.compile(r"\b(?:TOD[O]|FIXM[E])\b(?!\([A-Za-z][\w-]*\))")
_BARE_ELLIPSIS = re.compile(r"^\s*\.\.\.\s*$")
_ASSERT = re.compile(r"^\s*assert\b|\bpytest\.raises\(|\.assert_\w+\(")


def _is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith("tests/")
        or "/tests/" in path
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def _is_constraints(path: str) -> bool:
    return path.rsplit("/", 1)[-1] == "CONSTRAINTS.md"


def _source_rules(line: Line) -> list[str]:
    """Floor rules broken by one added line of a Python file."""
    text, rules = line.text, []
    reasoned = _REASONED.search(text)
    if _NEVER.search(text) or (reasoned and not _HAS_REASON.search(reasoned["rest"])):
        rules.append("silenced-checker")
    if _is_test(line.file) and _SKIP.search(text):
        rules.append("test-made-easier")
    unfinished = (
        _UNFINISHED_MARKER.search(text)
        or _EXCEPT_PASS_INLINE.search(text)
        or (_BARE_PASS.match(text) and line.prev is not None and _EXCEPT_HEAD.match(line.prev))
        or (not _is_test(line.file) and _NOT_IMPLEMENTED.search(text))
        or (line.file.startswith("app/") and _BARE_ELLIPSIS.match(text))
    )
    if unfinished:
        rules.append("unfinished-work")
    return rules


# --- CONSTRAINTS.md rules ----------------------------------------------------------------

_EXCEPTION_ROW = re.compile(r"^\|\s*[WE]\d+\s*\|")
_MIN_BEFORE = re.compile(r"(>=|>|≥|at least|minimum|\bmin\b|no less than|not fall|not drop)\s*$")
_MAX_BEFORE = re.compile(
    r"(<=|<|≤|at most|maximum|\bmax\b|no more than|under|below|not grow|not exceed)\s*$"
)
_MIN_AFTER = re.compile(r"^\s*\S*\s*(?:\|\s*)?(or more|or higher|must not fall|must not drop)")
_MAX_AFTER = re.compile(r"^\s*\S*\s*(?:\|\s*)?(or less|or lower|must not grow|must not exceed)")


def _rule_key(text: str) -> str | None:
    """Identify a rule: a table row by its first cell, a bullet by the text before its colon."""
    s = text.strip()
    if s.startswith("|"):
        cells = [c.strip() for c in s.split("|") if c.strip()]
        return cells[0] if cells else ""
    if re.match(r"[-*] ", s):
        return s[2:].split(":")[0].strip()
    return None  # prose, headings, dates: not a rule


def _thresholds(text: str) -> list[tuple[float, str | None]]:
    """Numbers in a rule with a direction ('min', 'max' or None) read from the words around."""
    out: list[tuple[float, str | None]] = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        before = text[max(0, m.start() - 24) : m.start()].lower()
        after = text[m.end() : m.end() + 40].lower()
        if _MIN_BEFORE.search(before) or _MIN_AFTER.search(after):
            direction: str | None = "min"
        elif _MAX_BEFORE.search(before) or _MAX_AFTER.search(after):
            direction = "max"
        else:
            direction = None
        out.append((float(m[0]), direction))
    return out


def _verdict(old: str, new: str) -> str | None:
    """Compare the thresholds of two versions of one rule; None when it did not loosen."""
    before, after = _thresholds(old), _thresholds(new)
    for direction in ("min", "max", None):
        was = [n for n, d in before if d == direction]
        now = [n for n, d in after if d == direction]
        for i, b in enumerate(was):
            if i >= len(now):
                return "threshold-removed"
            n = now[i]
            if n == b:
                continue
            if direction is None:
                return "threshold-changed"  # direction unreadable: cannot tell, so say so
            if (direction == "min" and n < b) or (direction == "max" and n > b):
                return "threshold-loosened"
    return None


def _constraints_findings(added: list[Line], removed: list[Line]) -> list[Finding]:
    findings: list[Finding] = []
    new_rules = [x for x in added if _rule_key(x.text) is not None]
    for r in (x for x in removed if _rule_key(x.text) is not None):
        match = next((a for a in new_rules if _rule_key(a.text) == _rule_key(r.text)), None)
        if match is None:
            if not _EXCEPTION_ROW.match(r.text.strip()):  # dropping an exception tightens
                findings.append(Finding("rule-removed", r.file, r.number, r.text.strip()[:160]))
            continue
        verdict = _verdict(r.text, match.text)
        if verdict:
            detail = f"{r.text.strip()}  ->  {match.text.strip()}"[:240]
            findings.append(Finding(verdict, match.file, match.number, detail))
    for a in added:
        if _EXCEPTION_ROW.match(a.text.strip()):
            findings.append(Finding("new-exception", a.file, a.number, a.text.strip()[:160]))
    return findings


# --- Orchestration -----------------------------------------------------------------------


def evaluate(added: list[Line], removed: list[Line], deleted: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for line in added:
        if line.file.endswith(".py"):
            findings.extend(Finding(rule, line.file, line.number) for rule in _source_rules(line))

    for file in deleted:
        if file.endswith(".py") and _is_test(file):
            findings.append(Finding("test-deleted", file, 0))

    # Net assertions per surviving test file: moving an assertion is fine, losing one is not.
    lost: dict[str, int] = defaultdict(int)
    first_removed: dict[str, int] = {}
    for line in removed:
        if _is_test(line.file) and line.file not in deleted and _ASSERT.search(line.text):
            lost[line.file] += 1
            first_removed.setdefault(line.file, line.number)
    for line in added:
        if _is_test(line.file) and _ASSERT.search(line.text):
            lost[line.file] -= 1
    findings.extend(
        Finding("assertion-removed", file, first_removed[file])
        for file, net in lost.items()
        if net > 0
    )

    findings.extend(
        _constraints_findings(
            [x for x in added if _is_constraints(x.file)],
            [x for x in removed if _is_constraints(x.file)],
        )
    )
    return sorted(findings, key=lambda f: (f.file, f.line, f.rule))


def run_guard(base: str, cwd: Path) -> list[Finding]:
    """Findings for the diff against ``base``; raises GuardError when the guard cannot run."""
    return evaluate(*parse_diff(collect_diff(base, cwd)))


def main(argv: list[str] | None = None, cwd: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diff-scoped CONSTRAINTS.md floor guard.")
    parser.add_argument("--base", default="origin/main", help="ref to compare against")
    args = parser.parse_args(argv)

    try:
        findings = run_guard(args.base, cwd or Path.cwd())
    except GuardError as exc:
        print(f"floor-guard: cannot run: {exc}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    if not findings:
        print("floor-guard: clean")
        return EXIT_CLEAN

    print(f"floor-guard: {len(findings)} floor violation(s):", file=sys.stderr)
    for f in findings:
        where = f"{f.file}:{f.line}" if f.line else f.file
        print(f"  [{f.rule}] {where}" + (f": {f.detail}" if f.detail else ""), file=sys.stderr)
    print(
        "\nEach is a move that lowers the bar. Fix the code, or record a tracked exception "
        "(owner + expiry) in CONSTRAINTS.md.",
        file=sys.stderr,
    )
    return EXIT_VIOLATION


if __name__ == "__main__":
    sys.exit(main())
