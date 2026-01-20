"""
Service-to-Service Authentication

Verifies bearer tokens for secure microservice communication.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Service token for internal API calls
# In production, this should be a secure random token stored in env vars
SERVICE_TOKEN = os.getenv("SIGNUP_SYNC_SERVICE_TOKEN", "dev_signup_sync_token_change_in_production")


def verify_service_token(authorization: Optional[str]) -> bool:
    """
    Verify service-to-service authentication token.

    Args:
        authorization: Authorization header value (e.g., "Bearer token123")

    Returns:
        True if token is valid, False otherwise
    """
    if not authorization:
        logger.warning("No authorization header provided")
        return False

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Invalid authorization header format")
        return False

    token = parts[1]

    # Verify token matches service token
    if token != SERVICE_TOKEN:
        logger.warning("Invalid service token provided")
        return False

    return True


def get_service_token() -> str:
    """
    Get the service token for making outbound requests.

    Returns:
        Service token to use in Authorization header
    """
    return SERVICE_TOKEN
