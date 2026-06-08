import sys
import logging
from pathlib import Path

# Get project logs path
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

def setup_logger(name: str = "app") -> logging.Logger:
    """Configures and returns a structured logger printing to console and a file."""
    # Ensure logs directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup multiple times
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File Handler
    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    return logger

# Global default logger instance
logger = setup_logger("app")
