from typing import TYPE_CHECKING

import nox  # pylint: disable=import-error

if TYPE_CHECKING:
    from nox.sessions import Session
# uv will handle any missing python versions
python_versions = ["3.10", "3.11", "3.12", "3.13"]


@nox.session(python=python_versions, venv_backend="uv")
def tests(session: "Session"):
    """Run tests on specified Python versions."""
    # Install the package and test dependencies with uv
    session.run_install("uv", "pip", "install", ".", external=True)
    session.run_install(
        "sh", "-c", "uv export --only-dev | uv pip install -r /dev/stdin"
    )

    # session.run("uv", "run", "python", "-c", "import invoke_toolkit")

    # Generate version-specific HTML report filename
    python_version = session.python
    html_report = f".nox/python-{python_version}-report.html"

    # Run pytest with common options
    session.run(
        "pytest",
        "tests/",
        "-v",  # verbose output
        "-s",  # don't capture output
        "--tb=short",  # shorter traceback format
        "--strict-markers",  # treat unregistered markers as errors
        "-n",
        "auto",  # parallel testing
        f"--html={html_report}",  # generate HTML report with version in name
        "--self-contained-html",  # make HTML report self-contained
        *session.posargs,  # allows passing additional pytest args from command line
    )
