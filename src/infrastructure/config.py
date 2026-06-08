import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Get workspace root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    """Manages the configuration parameters for the RAG FAQ Assistant."""
    
    # Project Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    VECTOR_DB_DIR: Path = DATA_DIR / "vector_db"
    
    # API Configurations
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    
    # LLM Configurations
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # Load from environment variable, falling back to Streamlit secrets if available
    _groq_key = os.getenv("GROQ_API_KEY", "")
    if not _groq_key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                _groq_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    GROQ_API_KEY: str = _groq_key
    
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # RAG Configurations
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.15))
    TOP_K_CONTEXT: int = int(os.getenv("TOP_K_CONTEXT", 3))
    
    # Scheduler Configurations
    CRAWL_INTERVAL_HOURS: int = int(os.getenv("CRAWL_INTERVAL_HOURS", 24))
    
    @classmethod
    def load(cls) -> dict:
        """Loads and returns all configurations as a dictionary."""
        return {
            "api_host": cls.API_HOST,
            "api_port": cls.API_PORT,
            "debug": cls.DEBUG,
            "llm_provider": cls.LLM_PROVIDER,
            "groq_model": cls.GROQ_MODEL,
            "embedding_model": cls.EMBEDDING_MODEL,
            "similarity_threshold": cls.SIMILARITY_THRESHOLD,
            "top_k_context": cls.TOP_K_CONTEXT,
            "crawl_interval_hours": cls.CRAWL_INTERVAL_HOURS,
            "paths": {
                "base": str(cls.BASE_DIR),
                "data": str(cls.DATA_DIR),
                "raw": str(cls.RAW_DATA_DIR),
                "processed": str(cls.PROCESSED_DATA_DIR),
                "vector_db": str(cls.VECTOR_DB_DIR)
            }
        }
