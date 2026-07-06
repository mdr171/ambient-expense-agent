import os
from dotenv import load_dotenv

load_dotenv()

# Pastikan API key dari .env tersedia untuk google-genai Client()
# .env menggunakan GEMINI_API_KEY, tapi Client() membaca GOOGLE_API_KEY
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Konfigurasi Model LLM
MODEL_NAME = "gemini-3.1-flash-lite"

# Threshold pengeluaran (Batas auto-approve)
AUTO_APPROVE_THRESHOLD = 100.0

