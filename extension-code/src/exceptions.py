"""
Exceptions module template for UAC Universal Extensions.

This module provides:
- Base ExecutionError class
- Standard exception types (DataValidationError, ConnectionError, etc.)
- ErrorManager singleton for error collection
- Exit code conventions

CUSTOMIZE:
- Add custom exception types for your extension
- Modify ErrorManager methods if needed
"""
from typing import Optional

class ExecutionError(Exception):
    """
    The default error raised by an extension.

    All extension errors must inherit from it.

    Attrs:
        exit_code: The exit code of the extension (for UAC)
        message: The error message for status description
    """

    exit_code: int = 1
    message: str = "Execution Failed"

    def __init__(self, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            message: Optional message that will be appended to the default message.

        Note:
            To return result data with errors, use error_manager.set_result()
            before raising the exception.
        """
        if message:
            self.message = f"{self.message}: {message}"

        super().__init__(self.message)

class DataValidationError(ExecutionError):
    """Raised when an input field is invalid."""
    exit_code = 20
    message = "Data Validation Error"

class UnexpectedSystemError(ExecutionError):
    """Raised for unexpected system errors."""
    exit_code = 1
    message = "System Error"

class NetworkException(ExecutionError):
    """Raised when network communication fails (timeout, connection refused, DNS failure)."""
    exit_code = 1
    message = "Network Error"

class SSLException(ExecutionError):
    """Raised when SSL/TLS certificate validation fails."""
    exit_code = 1
    message = "SSL Certificate Error"

class AuthenticationException(ExecutionError):
    """Raised when authentication fails (401 Unauthorized or proxy authentication required)."""
    exit_code = 1
    message = "Authentication Failed"

class PermissionException(ExecutionError):
    """Raised when access is denied to a resource (403 Forbidden)."""
    exit_code = 1
    message = "Permission Denied"

class ResourceNotFoundException(ExecutionError):
    """Raised when a requested resource is not found (404 Not Found)."""
    exit_code = 1
    message = "Resource Not Found"

class ConcurrentEditException(ExecutionError):
    """Raised when a concurrent edit conflict is detected (409 Conflict or sys_updated_on mismatch)."""
    exit_code = 1
    message = "Concurrent Edit Conflict"

class RateLimitException(ExecutionError):
    """Raised when rate limit is exceeded (HTTP 429 Too Many Requests)."""
    exit_code = 1
    message = "Rate Limit Exceeded"

class TemporaryServiceException(ExecutionError):
    """Raised when a service is temporarily unavailable (5xx server error or service unavailable)."""
    exit_code = 1
    message = "Temporary Service Error"

class ConfigurationException(ExecutionError):
    """Raised when configuration is invalid (JSON parse error, missing required keys)."""
    exit_code = 20
    message = "Configuration Error"

class ValidationException(ExecutionError):
    """Raised when validation fails (field type mismatch, invalid field reference, Business Service not found, ambiguous account resolution)."""
    exit_code = 20
    message = "Validation Error"

class MappingException(ExecutionError):
    """Raised when field mapping or transformation fails (source field missing, transformation error, aggregation failed)."""
    exit_code = 1
    message = "Mapping Error"
