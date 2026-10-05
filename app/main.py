from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.templating import Jinja2Templates

from app.ai_client import AIServiceError, summarize_repo
from app.github_client import (
    GitHubUnavailableError,
    RateLimitError,
    ReadmeNotFoundError,
    UserNotFoundError,
    fetch_repos,
    sort_repos,
)
from app.logging_config import setup_logging

# Build a path to app/templates that works from any folder
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

VALID_SORTS = ("stars", "name")

# GitHub owner names: letters, digits, hyphens.
OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]*$"

# Repo names may also contain dots and underscores.
REPO_PATTERN = r"^[A-Za-z0-9._-]+$"

setup_logging()

app = FastAPI(title="Repo Explorer")


def check_repo_name(repo):
    """Reject '.' and '..', which could change the GitHub URL we call."""
    if repo in (".", ".."):
        raise HTTPException(status_code=422, detail="Invalid repository name.")


@app.get("/")
def home(request: Request, username: str = "", sort: str = "stars"):
    """The web page: shows a search form, and results if a username is given."""
    username = username.strip()
    repos = []
    error = None

    # Ignore unexpected sort values instead of trusting the URL
    if sort not in VALID_SORTS:
        sort = "stars"

    if username:
        try:
            repos = fetch_repos(username)
        except (UserNotFoundError, RateLimitError, GitHubUnavailableError) as problem:
            error = str(problem)
        else:
            repos = sort_repos(repos, sort)

    context = {"username": username, "repos": repos, "error": error, "sort": sort}
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/api/repos/{username}")
def get_repos(username: str):
    """The JSON API: lists a user's repos."""
    try:
        repos = fetch_repos(username)
    except UserNotFoundError as problem:
        raise HTTPException(status_code=404, detail=str(problem))
    except RateLimitError as problem:
        raise HTTPException(status_code=429, detail=str(problem))
    except GitHubUnavailableError as problem:
        raise HTTPException(status_code=503, detail=str(problem))

    return {"username": username, "count": len(repos), "repos": repos}


@app.post("/api/summary/{owner}/{repo}")
def summarize(
    owner: str = PathParam(..., pattern=OWNER_PATTERN, max_length=39),
    repo: str = PathParam(..., pattern=REPO_PATTERN, max_length=100),
):
    """Summarize a repo's README with AI."""
    check_repo_name(repo)

    try:
        summary = summarize_repo(owner, repo)
    except ReadmeNotFoundError as problem:
        raise HTTPException(status_code=404, detail=str(problem))
    except RateLimitError as problem:
        raise HTTPException(status_code=429, detail=str(problem))
    except (GitHubUnavailableError, AIServiceError) as problem:
        raise HTTPException(status_code=503, detail=str(problem))

    return {"owner": owner, "repo": repo, "summary": summary}