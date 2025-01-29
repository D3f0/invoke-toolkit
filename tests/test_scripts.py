import json
import os
from pathlib import Path
import subprocess


def is_executable(file_path):
    return os.access(file_path, os.X_OK)


def test_script_in_venv(toplevel: Path) -> None:
    # This will ignore the shebanc
    runme = toplevel / "tests/scripts/runme.py"
    assert runme.exists()
    assert is_executable(runme)
    output = (
        subprocess.run(
            f"uv run python {runme} -Fjson -l",
            shell=True,
            cwd=toplevel,
            stdout=subprocess.PIPE,
        )
        .stdout.decode()
        .strip()
    )

    program_list_output = json.loads(output)
    assert "tasks" in program_list_output
    assert "hello" in program_list_output["tasks"]
    # assert is_executable(runme)
