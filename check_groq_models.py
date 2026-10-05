import httpx

from app.config import GROQ_API_KEY, GROQ_BASE_URL

url = f"{GROQ_BASE_URL.rstrip('/')}/models"
headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

response = httpx.get(url, headers=headers, timeout=10.0)
print("Status code:", response.status_code)

if response.status_code == 200:
    for model in response.json()["data"]:
        print(model["id"])