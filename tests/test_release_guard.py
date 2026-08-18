import os
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).parents[1]
GUARD = REPOSITORY_ROOT / "scripts" / "validate-release-tag.sh"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def release_repository(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    repository = tmp_path / "repository"

    run(["git", "init", "--bare", str(remote)], tmp_path)
    run(["git", "clone", str(remote), str(repository)], tmp_path)
    run(["git", "config", "user.email", "test@example.com"], repository)
    run(["git", "config", "user.name", "Test User"], repository)
    (repository / "README").write_text("initial\n")
    run(["git", "add", "README"], repository)
    run(["git", "commit", "-m", "initial"], repository)
    run(["git", "branch", "-M", "main"], repository)
    run(["git", "push", "-u", "origin", "main"], repository)
    return repository


def guard(tag_name: str, repository: Path) -> subprocess.CompletedProcess[str]:
    output = repository / "github-output"
    return subprocess.run(
        [str(GUARD)],
        cwd=repository,
        env={**os.environ, "TAG_NAME": tag_name, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_canonical_tag_at_origin_main(release_repository: Path) -> None:
    run(["git", "tag", "v0.0.67"], release_repository)
    run(["git", "push", "origin", "v0.0.67"], release_repository)

    result = guard("v0.0.67", release_repository)

    assert result.returncode == 0


def test_rejects_noncanonical_uppercase_tag(release_repository: Path) -> None:
    run(["git", "tag", "V0.0.67"], release_repository)
    run(["git", "push", "origin", "V0.0.67"], release_repository)

    result = guard("V0.0.67", release_repository)

    assert result.returncode != 0
    assert "canonical lowercase tag" in result.stderr


def test_rejects_tag_behind_updated_origin_main(
    release_repository: Path, tmp_path: Path
) -> None:
    run(["git", "tag", "v0.0.67"], release_repository)
    run(["git", "push", "origin", "v0.0.67"], release_repository)

    updater = tmp_path / "updater"
    run(
        ["git", "clone", str(release_repository.parent / "remote.git"), str(updater)],
        tmp_path,
    )
    run(["git", "config", "user.email", "test@example.com"], updater)
    run(["git", "config", "user.name", "Test User"], updater)
    run(["git", "checkout", "main"], updater)
    (updater / "README").write_text("updated\n")
    run(["git", "commit", "-am", "advance main"], updater)
    run(["git", "push"], updater)

    result = guard("v0.0.67", release_repository)

    assert result.returncode != 0
    assert "does not point to origin/main" in result.stderr
