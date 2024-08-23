from invoke_toolkit.utils.http import make_request
from invoke.context import Context
from logging import getLogger


logger = getLogger(__name__)


def get_latest_release(ctx: Context, repo: str):
    github_url = f"https://api.github.com/repos/{repo}/releases?per_page=100"
    logger.info("Requesting url %s", github_url)
    reponse = make_request(github_url, "GET", parse_json=True)
    return reponse


def get_github_release_files(): ...
