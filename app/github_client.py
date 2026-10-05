import logging

import httpx

from app.cache import get_cached, set_cached
from app.config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
PER_PAGE = 100   # the most GitHub allows per page
MAX_PAGES = 5    # safety limit: at most 500 repos per search


class UserNotFoundError(Exception):
    """Raised when the GitHub user does not exist."""


class ReadmeNotFoundError(Exception):
    """Raised when the repo or its README does not exist."""


class RateLimitError(Exception):
    """Raised when GitHub refuses the request because of rate limits."""


class GitHubUnavailableError(Exception):
    """Raised for network problems or unexpected GitHub errors."""


def build_headers():
    """Headers sent with every GitHub request."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-explorer-learning-project",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def clean_repo(repo):
    """Keep only the fields our app needs from GitHub's big response."""
    return {
        "name": repo["name"],
        "stars": repo["stargazers_count"],
        "language": repo["language"] or "Unknown",
        "url": repo["html_url"],
    }


def check_response(response, username):
    """Raise the right custom error if GitHub did not answer with success."""
    if response.status_code == 404:
        logger.info("User '%s' not found on GitHub", username)
        raise UserNotFoundError(f"User '{username}' was not found on GitHub.")

    if response.status_code == 401:
        logger.error("GitHub rejected the token (401)")
        raise GitHubUnavailableError("GitHub rejected the token. Check GITHUB_TOKEN.")

    if response.status_code == 403:
        logger.warning("GitHub rate limit or access denied (403)")
        raise RateLimitError("Rate limit reached. Try again later.")

    if response.status_code != 200:
        logger.error("Unexpected GitHub status: %s", response.status_code)
        raise GitHubUnavailableError(f"Unexpected GitHub error: {response.status_code}")


def fetch_page(client, username, page):
    """Fetch one page of repos. Returns GitHub's raw list for that page."""
    url = f"{GITHUB_API_URL}/users/{username}/repos"
    params = {"per_page": PER_PAGE, "page": page}

    try:
        response = client.get(url, params=params)
    except httpx.TimeoutException:
        logger.warning("Timeout fetching page %s for '%s'", page, username)
        raise GitHubUnavailableError("GitHub took too long to respond.")
    except httpx.RequestError:
        logger.warning("Connection problem fetching page %s for '%s'", page, username)
        raise GitHubUnavailableError("Could not connect to GitHub.")

    check_response(response, username)
    return response.json()


def fetch_repos_from_github(username):
    """Fetch all of a user's public repos from GitHub, page by page."""
    all_repos = []

    with httpx.Client(timeout=10.0, headers=build_headers()) as client:
        for page in range(1, MAX_PAGES + 1):
            raw_repos = fetch_page(client, username, page)

            for raw_repo in raw_repos:
                all_repos.append(clean_repo(raw_repo))

            # A page with fewer repos than PER_PAGE is the last page
            if len(raw_repos) < PER_PAGE:
                break

    logger.info("Fetched %s repos for '%s' from GitHub", len(all_repos), username)
    return all_repos


def fetch_repos(username):
    """Return repos from the cache if fresh, otherwise ask GitHub."""
    cache_key = username.lower()

    cached_repos = get_cached(cache_key)
    if cached_repos is not None:
        logger.info("Cache hit for '%s'", username)
        return cached_repos

    logger.info("Cache miss for '%s'", username)
    repos = fetch_repos_from_github(username)
    set_cached(cache_key, repos)
    return repos


def fetch_readme(owner, repo):
    """Fetch a repo's README as plain markdown text."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/readme"

    headers = build_headers()
    # Ask GitHub for the raw markdown instead of a JSON wrapper
    headers["Accept"] = "application/vnd.github.raw+json"

    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
    except httpx.TimeoutException:
        logger.warning("Timeout fetching README for '%s/%s'", owner, repo)
        raise GitHubUnavailableError("GitHub took too long to respond.")
    except httpx.RequestError:
        logger.warning("Connection problem fetching README for '%s/%s'", owner, repo)
        raise GitHubUnavailableError("Could not connect to GitHub.")

    # A 404 here means "no such repo or no README", not "no such user"
    if response.status_code == 404:
        logger.info("No README found for '%s/%s'", owner, repo)
        raise ReadmeNotFoundError(f"No README found for '{owner}/{repo}'.")

    check_response(response, owner)

    if not response.text.strip():
        raise ReadmeNotFoundError(f"The README for '{owner}/{repo}' is empty.")

    return response.text


def sort_repos(repos, sort_by):
    """Return the repos sorted by 'stars' (default) or 'name'."""
    if sort_by == "name":
        return sorted(repos, key=lambda repo: repo["name"].lower())

    return sorted(repos, key=lambda repo: repo["stars"], reverse=True)