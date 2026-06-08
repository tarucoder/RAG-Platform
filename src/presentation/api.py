import re
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path to ensure src modules resolve correctly
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.infrastructure.logger import logger
from src.infrastructure.config import Config
from src.RAG.generator import Generator

app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="Compliant, facts-only API Gateway for Groww mutual fund schemes.",
    version="1.0.0"
)

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate the generation pipeline
try:
    generator = Generator()
except Exception as e:
    logger.error(f"Failed to initialize Generator engine: {e}")
    generator = None

class ChatRequest(BaseModel):
    question: str

def detect_pii(text: str) -> bool:
    """Scans query text to block sensitive PII (Aadhaar, PAN, Card, Phone, Email)."""
    # 12-digit Aadhaar (raw or separated by spaces/dashes)
    aadhaar_pattern = r'\b\d{4}[ -]?\d{4}[ -]?\d{4}\b'
    # 10-character alphanumeric PAN
    pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
    # 10-digit Indian Mobile Numbers (optional +91/91 prefix)
    phone_pattern = r'\b(?:\+91|91)?[6-9]\d{9}\b'
    # 16-digit credit cards
    card_pattern = r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b'
    # Standard email address pattern
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'

    # Normalize case for PAN check
    text_upper = text.upper()
    
    if (re.search(aadhaar_pattern, text) or
        re.search(pan_pattern, text_upper) or
        re.search(phone_pattern, text) or
        re.search(card_pattern, text) or
        re.search(email_pattern, text)):
        return True
    return False

@app.get("/api/health")
def health_check():
    """Simple API sanity health status check."""
    return {"status": "healthy"}

@app.post("/api/chat")
def chat(payload: ChatRequest):
    """Processes queries using retrieved context under compliance guardrails and PII scanners."""
    question = payload.question.strip()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )
        
    # Check for PII presence
    if detect_pii(question):
        logger.warning(f"PII block triggered for query: '{question[:20]}...'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For your security, please do not share account numbers, PAN cards, Aadhaar, or contact info."
        )
        
    if not generator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retrieval engine is currently offline."
        )
        
    try:
        response = generator.generate(question)
        return response
    except Exception as e:
        logger.error(f"Error handling query request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the response."
        )

# Mount Web Client static files at root
static_web_dir = Path(__file__).resolve().parent / "web"
static_web_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(static_web_dir), html=True), name="web")
