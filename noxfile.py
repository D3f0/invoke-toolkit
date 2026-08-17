from typing import TYPE_CHECKING

import nox  # type: ignore[import-untyped]  # pylint: disable=import-error

if TYPE_CHECKING:
    from nox.sessions import Session  # type: ignore[import-untyped]

python_versions = ["3.11", "3.12", "3.13", "3.14"]


@nox.session(python=python_versions, venv_backend="uv")
def tests(session: "Session"):
    """Run the full suite in an isolated uv environment."""
    session.run_install("uv", "sync", "--active", "--group", "dev", external=True)
    session.run(
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--strict-markers",
        "-n",
        "auto",
        f"--html=.nox/python-{session.python}-report.html",
        "--self-contained-html",
        *session.posargs,
    )
