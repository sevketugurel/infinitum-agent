"""
Shared exceptions - Common exception classes used across the application
"""
from typing import Optional, Dict, Any


class InfinitumException(Exception):
    """Base exception for all Infinitum application exceptions"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ValidationError(InfinitumException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value


class NotFoundError(InfinitumException):
    """Raised when a requested resource is not found"""
    
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' not found"
        super().__init__(message, error_code="NOT_FOUND")
        self.details['resource_type'] = resource_type
        self.details['identifier'] = identifier


class AuthenticationError(InfinitumException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(InfinitumException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", required_permission: Optional[str] = None):
        super().__init__(message, error_code="AUTHORIZATION_ERROR")
        if required_permission:
            self.details['required_permission'] = required_permission


class SearchError(InfinitumException):
    """Raised when search operations fail"""
    
    def __init__(self, message: str, query: Optional[str] = None):
        super().__init__(message, error_code="SEARCH_ERROR")
        if query:
            self.details['query'] = query


class ExternalServiceError(InfinitumException):
    """Raised when external service calls fail"""
    
    def __init__(self, service_name: str, message: str, status_code: Optional[int] = None):
        super().__init__(f"{service_name}: {message}", error_code="EXTERNAL_SERVICE_ERROR")
        self.details['service_name'] = service_name
        if status_code:
            self.details['status_code'] = status_code


class DatabaseError(InfinitumException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message, error_code="DATABASE_ERROR")
        if operation:
            self.details['operation'] = operation


class CacheError(InfinitumException):
    """Raised when cache operations fail"""
    
    def __init__(self, message: str, key: Optional[str] = None):
        super().__init__(message, error_code="CACHE_ERROR")
        if key:
            self.details['key'] = key


class RateLimitError(InfinitumException):
    """Raised when rate limits are exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 limit: Optional[int] = None, reset_time: Optional[int] = None):
        super().__init__(message, error_code="RATE_LIMIT_ERROR")
        if limit:
            self.details['limit'] = limit
        if reset_time:
            self.details['reset_time'] = reset_time


class ConfigurationError(InfinitumException):
    """Raised when configuration is invalid or missing"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR")
        if config_key:
            self.details['config_key'] = config_key


class BusinessRuleError(InfinitumException):
    """Raised when business rules are violated"""
    
    def __init__(self, message: str, rule: Optional[str] = None):
        super().__init__(message, error_code="BUSINESS_RULE_ERROR")
        if rule:
            self.details['rule'] = rule


class DuplicateError(InfinitumException):
    """Raised when attempting to create duplicate resources"""
    
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message, error_code="DUPLICATE_ERROR")
        self.details['resource_type'] = resource_type
        self.details['identifier'] = identifier


class ConcurrencyError(InfinitumException):
    """Raised when concurrent modification conflicts occur"""
    
    def __init__(self, message: str = "Concurrent modification detected"):
        super().__init__(message, error_code="CONCURRENCY_ERROR")


class QuotaExceededError(InfinitumException):
    """Raised when user quotas are exceeded"""
    
    def __init__(self, quota_type: str, limit: int, current: int):
        message = f"{quota_type} quota exceeded: {current}/{limit}"
        super().__init__(message, error_code="QUOTA_EXCEEDED")
        self.details['quota_type'] = quota_type
        self.details['limit'] = limit
        self.details['current'] = current


class FileProcessingError(InfinitumException):
    """Raised when file processing fails"""
    
    def __init__(self, message: str, filename: Optional[str] = None, 
                 file_type: Optional[str] = None):
        super().__init__(message, error_code="FILE_PROCESSING_ERROR")
        if filename:
            self.details['filename'] = filename
        if file_type:
            self.details['file_type'] = file_type


class NetworkError(InfinitumException):
    """Raised when network operations fail"""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 status_code: Optional[int] = None):
        super().__init__(message, error_code="NETWORK_ERROR")
        if url:
            self.details['url'] = url
        if status_code:
            self.details['status_code'] = status_code


class TimeoutError(InfinitumException):
    """Raised when operations timeout"""
    
    def __init__(self, message: str = "Operation timed out", 
                 timeout_seconds: Optional[float] = None):
        super().__init__(message, error_code="TIMEOUT_ERROR")
        if timeout_seconds:
            self.details['timeout_seconds'] = timeout_seconds


class SerializationError(InfinitumException):
    """Raised when serialization/deserialization fails"""
    
    def __init__(self, message: str, data_type: Optional[str] = None):
        super().__init__(message, error_code="SERIALIZATION_ERROR")
        if data_type:
            self.details['data_type'] = data_type


class AIServiceError(InfinitumException):
    """Raised when AI service operations fail"""
    
    def __init__(self, message: str, model: Optional[str] = None, 
                 operation: Optional[str] = None):
        super().__init__(message, error_code="AI_SERVICE_ERROR")
        if model:
            self.details['model'] = model
        if operation:
            self.details['operation'] = operation


class VectorSearchError(InfinitumException):
    """Raised when vector search operations fail"""
    
    def __init__(self, message: str, index_name: Optional[str] = None):
        super().__init__(message, error_code="VECTOR_SEARCH_ERROR")
        if index_name:
            self.details['index_name'] = index_name


# Exception mapping for HTTP status codes
HTTP_STATUS_MAP = {
    ValidationError: 400,
    NotFoundError: 404,
    AuthenticationError: 401,
    AuthorizationError: 403,
    DuplicateError: 409,
    RateLimitError: 429,
    QuotaExceededError: 429,
    ConcurrencyError: 409,
    BusinessRuleError: 422,
    ConfigurationError: 500,
    DatabaseError: 500,
    ExternalServiceError: 502,
    NetworkError: 502,
    TimeoutError: 504,
    InfinitumException: 500,  # Default for base exception
}


def get_http_status_code(exception: Exception) -> int:
    """Get HTTP status code for an exception"""
    for exc_type, status_code in HTTP_STATUS_MAP.items():
        if isinstance(exception, exc_type):
            return status_code
    return 500  # Default to internal server error