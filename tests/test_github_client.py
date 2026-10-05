import httpx
import pytest

from app import github_client
from app.github_client import (
    PER_PAGE,
    GitHubUnavailableError,
    RateLimitError,
    ReadmeNotFoundError,
    UserNotFoundError,
    check_response,
    clean_repo,
    fetch_page,
    fetch_repos,
    fetch_repos_from_github,
    sort_repos,
    fetch_readme,
)


def make_raw_repo(name, stars=0, language=None):
    """Build a fake repo shaped like GitHub's response."""
    return {
        "name": name,
        "stargazers_count": stars,
        "language": language,
        "html_url": f"https://github.com/octocat/{name}",
    }


# ---------- clean_repo ----------

def test_clean_repo_keeps_only_needed_fields():
    raw = make_raw_repo("hello", stars=5, language="Python")
    cleaned = clean_repo(raw)

    assert cleaned == {
        "name": "hello",
        "stars": 5,
        "language": "Python",
        "url": "https://github.com/octocat/hello",
    }


def test_clean_repo_replaces_missing_language_with_unknown():
    raw = make_raw_repo("hello", language=None)

    assert clean_repo(raw)["language"] == "Unknown"


# ---------- sort_repos ----------

def test_sort_repos_by_stars_puts_highest_first():
    repos = [
        {"name": "a", "stars": 1},
        {"name": "b", "stars": 50},
        {"name": "c", "stars": 10},
    ]

    sorted_repos = sort_repos(repos, "stars")

    assert [repo["name"] for repo in sorted_repos] == ["b", "c", "a"]


def test_sort_repos_by_name_ignores_capitals():
    repos = [
        {"name": "banana", "stars": 0},
        {"name": "Apple", "stars": 0},
        {"name": "cherry", "stars": 0},
    ]

    sorted_repos = sort_repos(repos, "name")

    assert [repo["name"] for repo in sorted_repos] == ["Apple", "banana", "cherry"]


# ---------- check_response ----------

def test_check_response_raises_user_not_found_on_404():
    with pytest.raises(UserNotFoundError):
        check_response(httpx.Response(404), "ghost")


def test_check_response_raises_rate_limit_on_403():
    with pytest.raises(RateLimitError):
        check_response(httpx.Response(403), "octocat")


def test_check_response_raises_unavailable_on_401():
    with pytest.raises(GitHubUnavailableError):
        check_response(httpx.Response(401), "octocat")


def test_check_response_raises_unavailable_on_500():
    with pytest.raises(GitHubUnavailableError):
        check_response(httpx.Response(500), "octocat")


def test_check_response_accepts_200():
    # No error raised means the test passes
    check_response(httpx.Response(200), "octocat")


# ---------- fetch_page (network failures) ----------

class BrokenClient:
    """A fake client that always fails the way a real network can."""

    def __init__(self, error):
        self.error = error

    def get(self, url, params=None):
        raise self.error


def test_fetch_page_turns_timeout_into_unavailable_error():
    client = BrokenClient(httpx.ReadTimeout("too slow"))

    with pytest.raises(GitHubUnavailableError):
        fetch_page(client, "octocat", 1)


def test_fetch_page_turns_connection_failure_into_unavailable_error():
    client = BrokenClient(httpx.ConnectError("no network"))

    with pytest.raises(GitHubUnavailableError):
        fetch_page(client, "octocat", 1)


# ---------- pagination ----------

def test_fetch_repos_from_github_collects_every_page(monkeypatch):
    pages_requested = []

    def fake_fetch_page(client, username, page):
        pages_requested.append(page)
        if page == 1:
            return [make_raw_repo(f"repo-{number}") for number in range(PER_PAGE)]
        return [make_raw_repo("last-repo")]

    monkeypatch.setattr(github_client, "fetch_page", fake_fetch_page)

    repos = fetch_repos_from_github("octocat")

    assert len(repos) == PER_PAGE + 1
    assert pages_requested == [1, 2]


def test_exactly_one_full_page_still_requests_a_second_page(monkeypatch):
    pages_requested = []

    def fake_fetch_page(client, username, page):
        pages_requested.append(page)
        if page == 1:
            return [make_raw_repo(f"repo-{number}") for number in range(PER_PAGE)]
        return []

    monkeypatch.setattr(github_client, "fetch_page", fake_fetch_page)

    repos = fetch_repos_from_github("octocat")

    assert len(repos) == PER_PAGE
    assert pages_requested == [1, 2]


# ---------- caching ----------

def test_fetch_repos_uses_cache_on_second_call(monkeypatch):
    calls = []

    def fake_fetch_from_github(username):
        calls.append(username)
        return [{"name": "repo-one"}]

    monkeypatch.setattr(github_client, "fetch_repos_from_github", fake_fetch_from_github)

    fetch_repos("octocat")
    fetch_repos("OCTOCAT")  # different capitals, same cache entry

    assert len(calls) == 1


def test_fetch_repos_does_not_cache_errors(monkeypatch):
    calls = []

    def failing_fetch(username):
        calls.append(username)
        raise UserNotFoundError("nope")

    monkeypatch.setattr(github_client, "fetch_repos_from_github", failing_fetch)

    for _ in range(2):
        with pytest.raises(UserNotFoundError):
            fetch_repos("ghost")

    assert len(calls) == 2

# ---------- fetch_readme ----------

def test_fetch_readme_returns_the_text(monkeypatch):
    monkeypatch.setattr(
        github_client.httpx, "get", lambda *args, **kwargs: httpx.Response(200, text="# Hi")
    )

    assert fetch_readme("octocat", "Hello-World") == "# Hi"


def test_fetch_readme_raises_when_missing(monkeypatch):
    monkeypatch.setattr(
        github_client.httpx, "get", lambda *args, **kwargs: httpx.Response(404)
    )

    with pytest.raises(ReadmeNotFoundError):
        fetch_readme("octocat", "no-such-repo")


def test_fetch_readme_raises_when_empty(monkeypatch):
    monkeypatch.setattr(
        github_client.httpx, "get", lambda *args, **kwargs: httpx.Response(200, text="   ")
    )

    with pytest.raises(ReadmeNotFoundError):
        fetch_readme("octocat", "empty-repo")


def test_fetch_readme_turns_timeout_into_unavailable_error(monkeypatch):
    def timing_out(*args, **kwargs):
        raise httpx.ReadTimeout("too slow")

    monkeypatch.setattr(github_client.httpx, "get", timing_out)

    with pytest.raises(GitHubUnavailableError):
        fetch_readme("octocat", "Hello-World")