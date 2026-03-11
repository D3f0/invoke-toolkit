"""Fixtures for extension tests.

These fixtures ensure tests that need directories outside of git repos
work correctly in CI environments.
"""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def system_tmp_path() -> Iterator[Path]:
    """
    Creates a temporary directory in the system temp location.

    Unlike pytest's tmp_path, this is guaranteed to be outside any git repo,
    which is required for tests that use `create.package` (which refuses to
    create packages inside git repositories).

    The directory is cleaned up after the test completes.
    """
    tmp_dir = tempfile.mkdtemp(prefix="intk_test_")
    tmp_path = Path(tmp_dir)
    yield tmp_path
    # Cleanup after test
    shutil.rmtree(tmp_path, ignore_errors=True)
