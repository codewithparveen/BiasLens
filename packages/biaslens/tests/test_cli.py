import json

import pytest

from biaslens.cli import main
from biaslens.report import AuditReport


def test_estimate_command_prints_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["estimate", "--queries", "q1,q2", "--cities", "Chennai,Delhi", "--languages", "ta,hi", "--runs", "2"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["budget"]["search_calls"] == 2 * 2 * 2 * 2  # 2q x 2c x 2l x 2 runs


def test_estimate_command_needs_no_api_key(capsys: pytest.CaptureFixture[str]) -> None:
    # No --api-key flag exists for estimate at all -- this just re-confirms it exits cleanly.
    exit_code = main(["estimate", "--queries", "q1", "--cities", "Chennai", "--languages", "en"])
    assert exit_code == 0


def test_cache_stats_command_on_fresh_cache(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    cache_path = tmp_path / "c.sqlite3"
    exit_code = main(["cache-stats", "--cache-path", str(cache_path)])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"total_entries": 0, "expired_entries": 0, "live_entries": 0}


def _sample_report_json(tmp_path) -> str:
    report = AuditReport(
        plan={"queries": ["q1"], "cities": ["Chennai"], "languages": ["ta"]},  # type: ignore[arg-type]
        queries=[],
        is_demo_data=True,
    )
    path = tmp_path / "report.json"
    path.write_text(report.to_json())
    return str(path)


def test_report_command_summary_format(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _sample_report_json(tmp_path)
    exit_code = main(["report", path, "--format", "summary"])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["query_count"] == 0


def test_report_command_html_format(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _sample_report_json(tmp_path)
    exit_code = main(["report", path, "--format", "html"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "<html>" in out


def test_report_command_missing_file_returns_error(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["report", str(tmp_path / "does-not-exist.json"), "--format", "summary"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "no such file" in err


def test_audit_command_missing_key_reports_clean_error(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    # No SERPAPI_KEY in this test's env and no --api-key passed -> AuthError,
    # caught and reported as a clean exit code, not a traceback.
    import os

    env_backup = os.environ.pop("SERPAPI_KEY", None)
    try:
        exit_code = main(
            [
                "audit",
                "--queries",
                "q1",
                "--cities",
                "Chennai",
                "--languages",
                "en",
                "--cache-path",
                str(tmp_path / "c.sqlite3"),
            ]
        )
    finally:
        if env_backup is not None:
            os.environ["SERPAPI_KEY"] = env_backup
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "error:" in err
