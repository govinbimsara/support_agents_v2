#!/usr/bin/env python3
"""Gate for osv-scanner JSON: fail when a dependency vulnerability is high severity or worse.

osv-scanner reports findings but has no severity threshold of its own (it exits 1 on ANY
finding, including low ones), so CONSTRAINTS.md's "nothing at high or above" is enforced here.

Input: the JSON written by ``osv-scanner scan source -L uv.lock --format json``. The severity
used is ``results[].packages[].groups[].max_severity``, a CVSS base score as a string
(verified against osv-scanner v2.7.1 output). A group is one vulnerability, de-duplicated across
its aliases (GHSA / CVE / PYSEC ids).

Fails closed: a group whose severity is missing, empty, zero or not a number counts as a
violation, because "unknown" is not "low". Route a reviewed false positive through
``osv-scanner.toml`` (an ignore entry with a reason and expiry) and an exceptions row in
CONSTRAINTS.md, never by loosening this script.

Exit codes: 0 clean, 1 at least one violation, 2 the report could not be read (a scanner that
crashed and wrote nothing must never read as a clean scan).

Usage: python scripts/check_osv.py osv.json [--min-severity 7.0]
Requirement: CONSTRAINTS.md "Security: dependencies". Stdlib only.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_CLEAN = 0
EXIT_VIOLATION = 1
EXIT_UNREADABLE = 2

# CVSS "High" starts at 7.0 (v3/v4 qualitative scale). Below that is mostly noise for a POC.
DEFAULT_MIN_SEVERITY = 7.0


class ReportError(Exception):
    """The report is not a usable osv-scanner JSON document (exit code 2)."""


@dataclass(frozen=True)
class Violation:
    package: str
    version: str
    vuln_id: str
    severity: str  # the raw value, so "unknown" is visible in the output


def _severity(raw: object) -> float | None:
    """CVSS score as a float, or None when unknown (missing, empty, zero, not a number)."""
    if not isinstance(raw, str | int | float):
        return None
    try:
        score = float(raw)
    except ValueError:
        return None
    return score if score > 0 else None  # also False for NaN


def find_violations(report: Any, min_severity: float) -> list[Violation]:
    """Groups at or above ``min_severity`` and groups with unknown severity."""
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ReportError("not an osv-scanner JSON report (no 'results' list)")

    try:
        return _scan(report["results"], min_severity)
    except (AttributeError, TypeError, IndexError) as exc:
        # A crash here would exit 1 and read as "vulnerabilities found"; say "unreadable" (2).
        raise ReportError(f"unexpected report structure ({exc.__class__.__name__})") from exc


def _scan(results: list[Any], min_severity: float) -> list[Violation]:
    seen: set[tuple[str, str, str]] = set()
    violations: list[Violation] = []
    for result in results:
        for pkg in result.get("packages", []):
            info = pkg.get("package", {})
            name, version = str(info.get("name", "?")), str(info.get("version", "?"))
            for group in pkg.get("groups", []):
                raw = group.get("max_severity")
                score = _severity(raw)
                if score is not None and score < min_severity:
                    continue
                ids = group.get("ids") or ["?"]
                key = (name, version, str(ids[0]))
                if key in seen:  # the same lockfile can be reported under two sources
                    continue
                seen.add(key)
                violations.append(Violation(name, version, str(ids[0]), str(raw or "unknown")))
    return violations


def load_report(path: str) -> Any:
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read {path}: {exc.__class__.__name__}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail on high-severity osv-scanner findings.")
    parser.add_argument("report", help="osv-scanner JSON file, or - for stdin")
    parser.add_argument("--min-severity", type=float, default=DEFAULT_MIN_SEVERITY)
    args = parser.parse_args(argv)

    try:
        violations = find_violations(load_report(args.report), args.min_severity)
    except ReportError as exc:
        print(f"check-osv: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    if not violations:
        print(f"check-osv: no vulnerabilities at severity >= {args.min_severity} (or unknown)")
        return EXIT_CLEAN

    print(
        f"check-osv: {len(violations)} vulnerability group(s) at severity >= "
        f"{args.min_severity} or unknown:",
        file=sys.stderr,
    )
    for v in sorted(violations, key=lambda x: (x.package, x.vuln_id)):
        print(f"  {v.package} {v.version}: {v.vuln_id} (severity {v.severity})", file=sys.stderr)
    return EXIT_VIOLATION


if __name__ == "__main__":
    sys.exit(main())
