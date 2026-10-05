import httpx

GITHUB_API_URL = "https://api.github.com"


# Custom errors: each one describes a specific thing that can go wrong
class UserNotFoundError(Exception):
    """Raised when the GitHub user does not exist."""


class RateLimitError(Exception):
    """Raised when GitHub refuses the request because of rate limits."""


class GitHubUnavailableError(Exception):
    """Raised for network problems or unexpected GitHub errors."""


def fetch_repos(username):
    """Fetch a user's public repos. Returns a list, or raises an error."""
    url = f"{GITHUB_API_URL}/users/{username}/repos"

    # Step 1: try to reach GitHub at all
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.TimeoutException:
        raise GitHubUnavailableError("GitHub took too long to respond.")
    except httpx.RequestError:
        raise GitHubUnavailableError("Could not connect to GitHub. Check your internet.")

    # Step 2: check what GitHub answered
    if response.status_code == 404:
        raise UserNotFoundError(f"User '{username}' was not found on GitHub.")

    if response.status_code == 403:
        raise RateLimitError("Rate limit reached. Try again later.")

    if response.status_code != 200:
        raise GitHubUnavailableError(f"Unexpected GitHub error: {response.status_code}")

    # Step 3: success, so return the data
    return response.json()


def print_repos(repos):
    """Print a readable summary of each repo."""
    print("Number of repos:", len(repos))

    for repo in repos:
        name = repo["name"]
        stars = repo["stargazers_count"]
        language = repo["language"] or "Unknown"
        print(f"{name} | stars: {stars} | language: {language}")


def main():
    username = "octocat"

    try:
        repos = fetch_repos(username)
    except UserNotFoundError as error:
        print("Not found:", error)
    except RateLimitError as error:
        print("Rate limit:", error)
    except GitHubUnavailableError as error:
        print("GitHub problem:", error)
    else:
        print_repos(repos)


if __name__ == "__main__":
    main()