"""Unit tests for scripts/check_osv.py (CONSTRAINTS.md: dependency vulnerabilities).

Fixtures mirror the shape of real osv-scanner v2.7.1 JSON: severity is a CVSS score string at
results[].packages[].groups[].max_severity.
"""

import io
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import check_osv
from scripts.check_osv import ReportError, find_violations

pytestmark = pytest.mark.unit


def report(*groups: dict[str, Any], name: str = "django", version: str = "2.0.0") -> dict[str, Any]:
    return {
        "results": [
            {
                "source": {"path": "/x/uv.lock", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"name": name, "version": version, "ecosystem": "PyPI"},
                        "vulnerabilities": [],
                        "groups": list(groups),
                    }
                ],
            }
        ]
    }


def group(severity: object, vuln_id: str = "GHSA-aaaa") -> dict[str, Any]:
    g: dict[str, Any] = {"ids": [vuln_id, "PYSEC-1"], "aliases": ["CVE-1"]}
    if severity is not ...:
        g["max_severity"] = severity
    return g


@pytest.mark.parametrize("severity", ["7.0", "7.5", "9.8", "10.0"])
def test_high_and_critical_fail(severity: str) -> None:
    (v,) = find_violations(report(group(severity)), 7.0)
    assert (v.package, v.version, v.vuln_id, v.severity) == (
        "django",
        "2.0.0",
        "GHSA-aaaa",
        severity,
    )


@pytest.mark.parametrize("severity", ["0.1", "3.1", "5.5", "6.9", "6.99"])
def test_below_threshold_passes(severity: str) -> None:
    assert find_violations(report(group(severity)), 7.0) == []


@pytest.mark.parametrize("severity", [..., "", None, "0.0", 0, "n/a", "NaN", [], {}])
def test_unknown_severity_fails_closed(severity: object) -> None:
    # Unknown is not low: the group must be reported, whatever the raw value looks like.
    (v,) = find_violations(report(group(severity)), 7.0)
    assert v.vuln_id == "GHSA-aaaa"


@pytest.mark.parametrize("severity", [..., "", None])
def test_missing_or_empty_severity_is_labelled_unknown(severity: object) -> None:
    (v,) = find_violations(report(group(severity)), 7.0)
    assert v.severity == "unknown"


def test_numeric_severity_is_accepted() -> None:
    assert len(find_violations(report(group(8.1)), 7.0)) == 1
    assert find_violations(report(group(4.0)), 7.0) == []


def test_threshold_is_configurable() -> None:
    assert len(find_violations(report(group("5.5")), 5.0)) == 1
    assert find_violations(report(group("9.8")), 9.9) == []


def test_mixed_groups_report_only_the_bad_ones() -> None:
    found = find_violations(
        report(group("3.1", "LOW"), group("8.8", "HIGH"), group("6.9", "MID")), 7.0
    )
    assert [v.vuln_id for v in found] == ["HIGH"]


def test_same_group_under_two_sources_is_reported_once() -> None:
    doc = report(group("9.1"))
    doc["results"].append(
        {**doc["results"][0], "source": {"path": "/x/uv.lock", "type": "unknown"}}
    )
    assert len(find_violations(doc, 7.0)) == 1


def test_no_findings_and_empty_results_are_clean() -> None:
    assert find_violations({"results": []}, 7.0) == []
    assert find_violations(report(), 7.0) == []


@pytest.mark.parametrize(
    "doc",
    [
        [],
        "text",
        3,
        None,
        {},
        {"results": "no"},
        {"results": [1]},
        {"results": [{"packages": [1]}]},
    ],
)
def test_unexpected_structure_is_a_report_error(doc: object) -> None:
    with pytest.raises(ReportError):
        find_violations(doc, 7.0)


def write_report(tmp_path: Path, doc: object) -> str:
    path = tmp_path / "osv.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def test_main_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_osv.main([write_report(tmp_path, report(group("4.4")))]) == 0
    assert "no vulnerabilities" in capsys.readouterr().out


def test_main_violation_lists_package_and_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_osv.main([write_report(tmp_path, report(group("9.8", "GHSA-zzzz")))]) == 1
    err = capsys.readouterr().err
    assert "django 2.0.0: GHSA-zzzz (severity 9.8)" in err


def test_main_min_severity_flag(tmp_path: Path) -> None:
    path = write_report(tmp_path, report(group("5.5")))
    assert check_osv.main([path]) == 0
    assert check_osv.main([path, "--min-severity", "5"]) == 1


def test_main_unreadable_report_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_osv.main([str(tmp_path / "missing.json")]) == 2
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")  # a crashed scanner leaves an empty file
    assert check_osv.main([str(empty)]) == 2
    assert check_osv.main([write_report(tmp_path, {"unexpected": True})]) == 2
    assert "check-osv:" in capsys.readouterr().err


def test_main_reads_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(report(group("8.0")))))
    assert check_osv.main(["-"]) == 1
