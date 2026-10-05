import os

from dotenv import load_dotenv

# Read the .env file and load its values into the environment
load_dotenv()

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Groq (the AI service that writes summaries)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Only send the start of long READMEs to keep costs and delays down
MAX_README_CHARS = 12000

# Reply length cap. This model "thinks" before answering, and that
# thinking can count toward the cap, so leave plenty of room.
MAX_SUMMARY_TOKENS = 1000

# How long cached results stay fresh
CACHE_TTL_SECONDS = 300  # 5 minutes