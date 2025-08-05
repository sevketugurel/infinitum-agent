"""
Authentication and Authorization Middleware
Handles Firebase Auth integration and JWT token validation
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from typing import Optional, Dict, Any
import logging
import time
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()

class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify Firebase ID token and return decoded token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Dict containing decoded token information
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Verify the token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        
        logger.info(f"Successfully authenticated user: {decoded_token.get('uid')}")
        
        return decoded_token
        
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid ID token: {str(e)}")
        raise AuthenticationError("Invalid authentication token")
        
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired ID token: {str(e)}")
        raise AuthenticationError("Authentication token has expired")
        
    except auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked ID token: {str(e)}")
        raise AuthenticationError("Authentication token has been revoked")
        
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise AuthenticationError("Authentication failed")

async def get_current_user(token_data: Dict[str, Any] = Depends(verify_firebase_token)) -> Dict[str, Any]:
    """
    Get current authenticated user information
    
    Args:
        token_data: Decoded Firebase token
        
    Returns:
        Dict containing user information
    """
    try:
        # Extract user information from token
        user_info = {
            "uid": token_data.get("uid"),
            "email": token_data.get("email"),
            "email_verified": token_data.get("email_verified", False),
            "name": token_data.get("name"),
            "picture": token_data.get("picture"),
            "firebase": {
                "sign_in_provider": token_data.get("firebase", {}).get("sign_in_provider"),
                "identities": token_data.get("firebase", {}).get("identities", {})
            },
            "auth_time": token_data.get("auth_time"),
            "iat": token_data.get("iat"),
            "exp": token_data.get("exp")
        }
        
        return user_info
        
    except Exception as e:
        logger.error(f"Failed to extract user info: {str(e)}")
        raise AuthenticationError("Failed to get user information")

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None
    Useful for endpoints that work with or without authentication
    
    Args:
        credentials: Optional HTTP Authorization credentials
        
    Returns:
        Dict containing user information or None if not authenticated
    """
    if not credentials:
        return None
        
    try:
        # Verify token directly instead of calling dependency function
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        
        # Extract user information from token
        user_info = {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "firebase": {
                "sign_in_provider": decoded_token.get("firebase", {}).get("sign_in_provider"),
                "identities": decoded_token.get("firebase", {}).get("identities", {})
            },
            "auth_time": decoded_token.get("auth_time"),
            "iat": decoded_token.get("iat"),
            "exp": decoded_token.get("exp")
        }
        
        return user_info
        
    except Exception as e:
        logger.warning(f"Optional auth failed: {str(e)}")
        return None

def require_roles(*required_roles: str):
    """
    Decorator to require specific roles for endpoint access
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (should be injected by dependency)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise AuthorizationError("Authentication required")
            
            # Check if user has required roles
            user_roles = current_user.get('custom_claims', {}).get('roles', [])
            
            if not any(role in user_roles for role in required_roles):
                raise AuthorizationError(f"Required roles: {', '.join(required_roles)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_email_verified(func):
    """
    Decorator to require email verification
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user:
            raise AuthorizationError("Authentication required")
        
        if not current_user.get('email_verified', False):
            raise AuthorizationError("Email verification required")
        
        return await func(*args, **kwargs)
    return wrapper

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    async def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean old requests
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > window_start
            ]
        else:
            self.requests[user_id] = []
        
        # Check if under limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(current_time)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter()

async def check_rate_limit(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Check rate limits for authenticated users
    
    Args:
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    user_id = current_user.get('uid')
    if not await rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )