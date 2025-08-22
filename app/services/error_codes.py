# app/services/error_codes.py
from enum import Enum

class ErrorCode(Enum):
    # Authentication Errors (1000-1999)
    AUTH_INVALID_FORMAT = 1001
    AUTH_ACCESS_DENIED = 1002
    AUTH_SERVICE_UNAVAILABLE = 1003
    
    # Query Service Errors (2000-2999)
    QUERY_NOT_FOUND = 2001
    QUERY_SERVICE_UNAVAILABLE = 2002
    QUERY_REQUIRED_INFO_MISSING = 2003
    QUERY_PROCESSING_FAILED = 2004
    QUERY_INVALID_VALUE = 2005
    QUERY_VALUE_OUT_OF_BOUNDS = 2006
    QUERY_NOT_AVAILABLE = 2007
    
    # Database Errors (3000-3999)
    DB_CONNECTION_FAILED = 3001
    DB_SCHEMA_ERROR = 3002
    DB_EXECUTION_ERROR = 3003
    
    # General System Errors (9000-9999)
    SYSTEM_INTERNAL_ERROR = 9001
    SYSTEM_UNAVAILABLE = 9002

class CodedError(Exception):
    """Custom exception that carries both user message and error code"""
    def __init__(self, error_code: ErrorCode, user_message: str = None):
        self.error_code = error_code
        self.user_message = user_message or ERROR_MESSAGES.get(error_code, "An error occurred")
        super().__init__(self.user_message)
    
    def to_dict(self) -> dict:
        return {
            "error": self.user_message,
            "code": self.error_code.value,
            "ref": self.error_code.name
        }

def create_error_response(error_code: ErrorCode, user_message: str) -> dict:
    """Create a standardized error response with both user message and error code"""
    return {
        "error": user_message,
        "code": error_code.value,
        "ref": error_code.name
    }

# Error code mapping for quick lookup
ERROR_MESSAGES = {
    ErrorCode.AUTH_INVALID_FORMAT: "Invalid API key format",
    ErrorCode.AUTH_ACCESS_DENIED: "Access denied",
    ErrorCode.AUTH_SERVICE_UNAVAILABLE: "Service temporarily unavailable",
    
    ErrorCode.QUERY_NOT_FOUND: "Query not found",
    ErrorCode.QUERY_SERVICE_UNAVAILABLE: "Service temporarily unavailable",
    ErrorCode.QUERY_REQUIRED_INFO_MISSING: "Required information missing",
    ErrorCode.QUERY_PROCESSING_FAILED: "Unable to process request",
    ErrorCode.QUERY_INVALID_VALUE: "Invalid value provided",
    ErrorCode.QUERY_VALUE_OUT_OF_BOUNDS: "Value outside allowed range",
    ErrorCode.QUERY_NOT_AVAILABLE: "Query is not available",
    
    ErrorCode.DB_CONNECTION_FAILED: "Service temporarily unavailable",
    ErrorCode.DB_SCHEMA_ERROR: "Service temporarily unavailable",
    ErrorCode.DB_EXECUTION_ERROR: "Unable to process request",
    
    ErrorCode.SYSTEM_INTERNAL_ERROR: "Service temporarily unavailable",
    ErrorCode.SYSTEM_UNAVAILABLE: "Service temporarily unavailable",
}

def get_error_response(error_code: ErrorCode) -> dict:
    """Get standardized error response for an error code"""
    message = ERROR_MESSAGES.get(error_code, "An error occurred")
    return create_error_response(error_code, message)

def raise_coded_error(error_code: ErrorCode, custom_message: str = None):
    """Raise a CodedError with the specified error code"""
    raise CodedError(error_code, custom_message)
