from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "entrada"
INDEX_DIR = DATA_DIR / "indice"
INDEX_FILE = INDEX_DIR / "indice.json"
PROCESSED_DIR = DATA_DIR / "processados"

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
}

MAX_PREVIEW_CHARS = 180
MAX_INDEXED_CHARS = 4000

SEARCH_TOP_K = int(os.getenv("SEARCH_TOP_K", "5"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

SYSTEM_PROMPT = """\
Você é um assistente técnico de inteligência documental local.

Regras:
1. Responda usando prioritariamente o contexto recuperado.
2. Se o contexto for insuficiente, diga isso explicitamente.
3. Não invente fatos ausentes.
4. Seja objetivo, técnico e estruturado.
5. Quando útil, cite os nomes dos arquivos usados na resposta.
"""