"""
Call Structure Validator
Validates request structure before proceeding to authentication
"""
from fastapi import Request, HTTPException
from typing import Dict, Any, Optional
import re

class CallStructureValidator:
    """Validates API call structure"""
    
    def __init__(self):
        # Required query parameters for valid API calls
        self.required_params = ["key", "q"]
        self.optional_params = ["demo", "format", "limit", "order_by", "order_desc", "minutes"]
        
        # API key format validation (basic)
        self.api_key_pattern = re.compile(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$')
        
        # Query code validation (basic)
        self.query_code_pattern = re.compile(r'^[a-zA-Z0-9_-]{1,50}$')
    
    def validate_call_structure(self, request: Request) -> tuple[bool, str, Dict[str, Any]]:
        """
        Validate API call structure
        Returns: (is_valid, error_message, extracted_params)
        """
        try:
            # Extract query parameters
            params = dict(request.query_params)
            
            # Check required parameters exist
            for required_param in self.required_params:
                if required_param not in params:
                    return False, f"Missing required parameter: {required_param}", {}
            
            # Validate API key format
            api_key = params.get("key", "")
            if not self._is_valid_api_key(api_key):
                return False, "Invalid API key format", {}
            
            # Validate query code format
            query_code = params.get("q", "")
            if not self._is_valid_query_code(query_code):
                return False, "Invalid query code format", {}
            
            # Validate optional parameters
            validation_errors = []
            
            # Validate format parameter
            if "format" in params:
                format_val = params["format"].lower()
                if format_val not in ["json", "csv"]:
                    validation_errors.append("Format must be 'json' or 'csv'")
            
            # Validate demo parameter
            if "demo" in params:
                demo_val = params["demo"].lower()
                if demo_val not in ["true", "false"]:
                    validation_errors.append("Demo must be 'true' or 'false'")
            
            # Validate limit parameter
            if "limit" in params:
                try:
                    limit_val = int(params["limit"])
                    if limit_val <= 0 or limit_val > 10000:
                        validation_errors.append("Limit must be between 1 and 10000")
                except ValueError:
                    validation_errors.append("Limit must be a number")
            
            # Validate order_desc parameter
            if "order_desc" in params:
                order_desc_val = params["order_desc"].lower()
                if order_desc_val not in ["true", "false"]:
                    validation_errors.append("Order_desc must be 'true' or 'false'")
            
            # Note: We allow any additional parameters as they may be dynamic query parameters
            # The query service will validate them against the query parameter schema
            
            if validation_errors:
                return False, "; ".join(validation_errors), {}
            
            # Structure is valid
            return True, "", params
            
        except Exception as e:
            return False, f"Call structure validation error: {str(e)}", {}
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """Validate API key format (GUID format)"""
        if not api_key or len(api_key) < 8:
            return False
        
        # Check if it matches GUID pattern
        return bool(self.api_key_pattern.match(api_key.upper()))
    
    def _is_valid_query_code(self, query_code: str) -> bool:
        """Validate query code format"""
        if not query_code or len(query_code) == 0:
            return False
        
        # Basic validation - alphanumeric, underscore, dash, max 50 chars
        return bool(self.query_code_pattern.match(query_code))

# Global validator instance
call_validator = CallStructureValidator()
