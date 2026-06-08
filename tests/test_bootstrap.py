import sys
from pathlib import Path

# Add src to the path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.infrastructure.config import Config
from src.infrastructure.logger import logger
from src.infrastructure.exceptions import AppException

def test_config_load():
    """Verify that configuration loads as a dict and contains basic paths."""
    config_dict = Config.load()
    assert isinstance(config_dict, dict)
    assert "paths" in config_dict
    assert "llm_provider" in config_dict
    assert config_dict["llm_provider"] == "groq"
    logger.info("Configuration loading validation passed.")

def test_logger():
    """Verify that logging works without errors."""
    try:
        logger.info("Sanity check message inside unit tests.")
        assert True
    except Exception as e:
        assert False, f"Logger threw an exception: {e}"

def test_custom_exception():
    """Verify that custom exception structure functions correctly."""
    try:
        raise AppException("Domain test failure.")
    except AppException as e:
        assert e.message == "Domain test failure."
        logger.info("Custom exceptions validation passed.")
