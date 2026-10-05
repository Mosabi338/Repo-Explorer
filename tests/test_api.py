import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai_client import AIServiceError
from app.github_client import (
    GitHubUnavailableError,
    RateLimitError,
    ReadmeNotFoundError,
    UserNotFoundError,
)
from app.main import app, check_repo_name

client = TestClient(app)

FAKE_REPOS = [
    {"name": "repo-one", "stars": 5, "language": "Python", "url": "https://example.com/1"},
    {"name": "repo-two", "stars": 9, "language": "Unknown", "url": "https://example.com/2"},
]


# ---------- repo list API ----------

def test_api_returns_repos(monkeypatch):
    monkeypatch.setattr("app.main.fetch_repos", lambda username: FAKE_REPOS)

    response = client.get("/api/repos/octocat")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "octocat"
    assert data["count"] == 2


@pytest.mark.parametrize(
    "error_class, expected_status",
    [
        (UserNotFoundError, 404),
        (RateLimitError, 429),
        (GitHubUnavailableError, 503),
    ],
)
def test_api_turns_errors_into_http_statuses(monkeypatch, error_class, expected_status):
    def failing_fetch(username):
        raise error_class("something went wrong")

    monkeypatch.setattr("app.main.fetch_repos", failing_fetch)

    response = client.get("/api/repos/octocat")

    assert response.status_code == expected_status
    assert response.json()["detail"] == "something went wrong"


# ---------- web page ----------

def test_home_page_shows_search_form():
    response = client.get("/")

    assert response.status_code == 200
    assert "Repo Explorer" in response.text


def test_home_page_lists_repos(monkeypatch):
    monkeypatch.setattr("app.main.fetch_repos", lambda username: list(FAKE_REPOS))

    response = client.get("/?username=octocat")

    assert "repo-one" in response.text
    assert "repo-two" in response.text


def test_home_page_shows_error_message(monkeypatch):
    def failing_fetch(username):
        raise UserNotFoundError("User 'ghost' was not found on GitHub.")

    monkeypatch.setattr("app.main.fetch_repos", failing_fetch)

    response = client.get("/?username=ghost")

    assert "was not found on GitHub" in response.text


def test_home_page_ignores_invalid_sort_value(monkeypatch):
    monkeypatch.setattr("app.main.fetch_repos", lambda username: list(FAKE_REPOS))

    response = client.get("/?username=octocat&sort=banana")

    assert response.status_code == 200


# ---------- summary API ----------

def test_summary_endpoint_returns_summary(monkeypatch):
    monkeypatch.setattr("app.main.summarize_repo", lambda owner, repo: "- A summary")

    response = client.post("/api/summary/octocat/Hello-World")

    assert response.status_code == 200
    assert response.json()["summary"] == "- A summary"


@pytest.mark.parametrize(
    "error_class, expected_status",
    [
        (ReadmeNotFoundError, 404),
        (RateLimitError, 429),
        (GitHubUnavailableError, 503),
        (AIServiceError, 503),
    ],
)
def test_summary_endpoint_turns_errors_into_http_statuses(
    monkeypatch, error_class, expected_status
):
    def failing_summary(owner, repo):
        raise error_class("something went wrong")

    monkeypatch.setattr("app.main.summarize_repo", failing_summary)

    response = client.post("/api/summary/octocat/Hello-World")

    assert response.status_code == expected_status


def test_summary_endpoint_rejects_names_with_odd_characters():
    response = client.post("/api/summary/octocat/bad!name")

    assert response.status_code == 422


@pytest.mark.parametrize("bad_name", [".", ".."])
def test_check_repo_name_rejects_dot_names(bad_name):
    with pytest.raises(HTTPException) as caught:
        check_repo_name(bad_name)

    assert caught.value.status_code == 422


def test_summary_endpoint_accepts_dotted_repo_names(monkeypatch):
    monkeypatch.setattr("app.main.summarize_repo", lambda owner, repo: "- ok")

    response = client.post("/api/summary/octocat/octocat.github.io")

    assert response.status_code == 200