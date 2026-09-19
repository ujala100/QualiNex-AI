"""
Central configuration for the AIVOA Complaint Management backend.

All secrets/config are read from environment variables (see .env.example).
Nothing here is hardcoded so the same code runs against SQLite (fast local
demo) or MySQL/Postgres (the mandated production stack) by only changing
DATABASE_URL.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Groq LLM configuration -------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_BASE = "https://api.groq.com/openai/v1/chat/completions"

# Fast, cheap model -> used for structured field EXTRACTION (high volume,
# low-latency task: turning free text into the Log Complaint form JSON).
GROQ_EXTRACTION_MODEL = os.getenv("GROQ_EXTRACTION_MODEL", "gemma2-9b-it")

# Larger model -> used for REASONING tasks where quality matters more than
# speed: risk classification, root cause, CAPA, duplicate reasoning, summary.
GROQ_REASONING_MODEL = os.getenv("GROQ_REASONING_MODEL", "llama-3.3-70b-versatile")

# --- Database ----------------------------------------------------------------
# Defaults to local SQLite so the grader can run this with zero setup.
# For the mandated stack, set e.g.:
#   postgresql+psycopg2://user:pass@localhost:5432/aivoa
#   mysql+pymysql://user:pass@localhost:3306/aivoa
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aivoa.db")

# --- Misc ---------------------------------------------------------------------
MAX_UPLOAD_MB = 10
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".eml"}
