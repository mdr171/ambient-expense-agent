import os
from dotenv import load_dotenv

load_dotenv()

# Ensure API key from .env is available for google-genai Client()
# .env uses GEMINI_API_KEY, but Client() expects GOOGLE_API_KEY
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# LLM Model Configuration
MODEL_NAME = "gemini-3.1-flash-lite"

# Expense Threshold (Auto-approval limit)
AUTO_APPROVE_THRESHOLD = 100.0

