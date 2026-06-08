class AppException(Exception):
    """Base exception class for all custom exceptions in the application."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class ValidationError(AppException):
    """Exception raised when user input preferences fail validation checks."""
    pass

class ScrapingException(AppException):
    """Exception raised when crawlers fail to fetch or parse webpage schemas."""
    pass

class DatabaseException(AppException):
    """Exception raised when vector database actions (save, query, load) fail."""
    pass

class LLMException(AppException):
    """Exception raised when remote LLM API engines fail, timeout, or rate-limit."""
    pass

class PIIViolationException(AppException):
    """Exception raised when queries contain PII, violating security compliance policies."""
    pass
