"""CLI tests: the JSON form is the contract that pyngo-run depends on."""

import json
from pathlib import Path

import pytest

from pyngo.cli import main


def test_build_json_is_one_object(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    program = tmp_path / "ok.pyn"
    _ = program.write_text("{ int a = 1; print ( a ); }", encoding="utf-8")

    assert main(["build", str(program), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["errors"] == []
    assert payload["data"][0]["text"] == "a : int"
    assert any(row["text"] == "HLT" for row in payload["code"])


def test_build_json_reports_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    program = tmp_path / "bad.pyn"
    _ = program.write_text("{ int a = true; }", encoding="utf-8")

    assert main(["build", str(program), "--json"]) == 1

    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert payload["data"] == []
    assert payload["errors"] == ["Line 1: TYPE ERROR: Variable 'a' is int, but got bool."]
