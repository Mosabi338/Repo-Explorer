import httpx

from app.config import GITHUB_TOKEN

headers = {}
if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

response = httpx.get("https://api.github.com/rate_limit", headers=headers)
core_limits = response.json()["resources"]["core"]

print("Limit:", core_limits["limit"])
print("Remaining:", core_limits["remaining"])