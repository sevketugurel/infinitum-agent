"""
Shared components - Common utilities, interfaces, and exceptions
"""

# Import exceptions from the exceptions.py file
from .exceptions import (
    InfinitumException, ValidationError, NotFoundError, AuthenticationError,
    AuthorizationError, SearchError, ExternalServiceError, DatabaseError,
    CacheError, RateLimitError, ConfigurationError, BusinessRuleError,
    DuplicateError, ConcurrencyError, QuotaExceededError, FileProcessingError,
    NetworkError, TimeoutError, SerializationError, AIServiceError,
    VectorSearchError, get_http_status_code
)

__all__ = [
    # Exceptions
    'InfinitumException', 'ValidationError', 'NotFoundError', 'AuthenticationError',
    'AuthorizationError', 'SearchError', 'ExternalServiceError', 'DatabaseError',
    'CacheError', 'RateLimitError', 'ConfigurationError', 'BusinessRuleError',
    'DuplicateError', 'ConcurrencyError', 'QuotaExceededError', 'FileProcessingError',
    'NetworkError', 'TimeoutError', 'SerializationError', 'AIServiceError',
    'VectorSearchError', 'get_http_status_code',
]