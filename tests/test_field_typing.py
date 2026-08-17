"""Static typing contract tests for Field defaults."""

import subprocess
from pathlib import Path


def test_positive_field_typing_fixture_passes():
    result = subprocess.run(
        ["uv", "run", "ty", "check", "tests/typecheck/fields.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_incompatible_factory_fixture_is_rejected(tmp_path: Path):
    source = Path("tests/typecheck/fields_negative.py.fixture")
    target = tmp_path / "fields_negative.py"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        ["uv", "run", "pyright", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "reportArgumentType" in result.stdout + result.stderr
