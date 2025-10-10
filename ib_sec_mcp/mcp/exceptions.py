"""Custom exceptions for IB Analytics MCP Server

These exceptions provide clear error messages to MCP clients while protecting
sensitive internal information.
"""

from fastmcp.exceptions import ToolError


class IBAnalyticsError(ToolError):
    """Base exception for IB Analytics MCP errors

    This exception and its subclasses are always visible to MCP clients,
    regardless of mask_error_details setting.
    """

    pass


class ValidationError(IBAnalyticsError):
    """Exception raised when input validation fails"""

    def __init__(self, message: str, field: str = None):
        self.field = field
        if field:
            super().__init__(f"Validation error for '{field}': {message}")
        else:
            super().__init__(f"Validation error: {message}")


class APIError(IBAnalyticsError):
    """Exception raised when IB API calls fail"""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        if status_code:
            super().__init__(f"IB API error ({status_code}): {message}")
        else:
            super().__init__(f"IB API error: {message}")


class DataNotFoundError(IBAnalyticsError):
    """Exception raised when requested data is not found"""

    pass


class FileOperationError(IBAnalyticsError):
    """Exception raised when file operations fail"""

    pass


class ConfigurationError(IBAnalyticsError):
    """Exception raised when configuration is invalid or missing"""

    pass


class IBTimeoutError(IBAnalyticsError):
    """Exception raised when operation times out"""

    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        if operation:
            super().__init__(f"Timeout during '{operation}': {message}")
        else:
            super().__init__(f"Timeout: {message}")


class YahooFinanceError(IBAnalyticsError):
    """Exception raised when Yahoo Finance API calls fail"""

    pass
