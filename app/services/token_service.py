# app/services/token_service.py
from fastapi import HTTPException
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os
from .auth import resolve_account_from_header
from .error_codes import ErrorCode, get_error_response

# Secret key for JWT signing (in production, use environment variable)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

class TokenService:
    """Service for JWT token management"""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.expiration_minutes = JWT_EXPIRATION_MINUTES
    
    async def create_token(self, authorization: str) -> dict:
        """
        Create a JWT token from an API key in Authorization header
        """
        try:
            # Authenticate using the API key
            client_id = await resolve_account_from_header(authorization)
            
            # Extract the API key for logging
            api_key = authorization
            if authorization.startswith('Bearer '):
                api_key = authorization[7:]
            
            # Create JWT payload
            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=self.expiration_minutes)
            
            payload = {
                "client_id": client_id,
                "api_key_hash": api_key[:8] + "...",  # Partial key for identification
                "iat": now,
                "exp": expires_at,
                "iss": "enervibe-api",
                "sub": str(client_id)
            }
            
            # Generate JWT token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            return {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": self.expiration_minutes * 60,
                "expires_at": expires_at.isoformat(),
                "client_id": client_id
            }
            
        except HTTPException:
            # Re-raise authentication errors
            raise
        except Exception as e:
            error_response = get_error_response(ErrorCode.AUTH_SERVICE_UNAVAILABLE)
            raise HTTPException(status_code=500, detail=error_response)
    
    def verify_token(self, token: str) -> dict:
        """
        Verify and decode a JWT token
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

# Global token service instance
token_service = TokenService()
