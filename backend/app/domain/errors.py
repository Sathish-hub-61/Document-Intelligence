"""
Domain-specific exceptions for University Document Intelligence.
These are pure domain exceptions without HTTP status codes.
"""
from typing import Optional


class DomainError(Exception):
    """Base domain exception."""
    def __init__(self, message: str, code: str = "domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class EntityNotFoundError(DomainError):
    def __init__(self, message: str = "Requested entity was not found"):
        super().__init__(message, code="not_found")


class ForbiddenError(DomainError):
    def __init__(self, message: str = "Access to this resource is forbidden"):
        super().__init__(message, code="forbidden")


class DuplicateFileError(DomainError):
    def __init__(self, message: str = "Identical file already exists for this document"):
        super().__init__(message, code="duplicate_file")


class InvalidFileError(DomainError):
    def __init__(self, message: str = "Invalid file type, corrupted signature or exceeded size limit"):
        super().__init__(message, code="invalid_file")


class AuthenticationError(DomainError):
    def __init__(self, message: str = "Authentication failed or token expired"):
        super().__init__(message, code="unauthenticated")


class ValidationError(DomainError):
    def __init__(self, message: str = "Input data validation failed"):
        super().__init__(message, code="validation_error")


class LLMUnavailableError(DomainError):
    def __init__(self, message: str = "The LLM provider failed after retries"):
        super().__init__(message, code="llm_unavailable")

