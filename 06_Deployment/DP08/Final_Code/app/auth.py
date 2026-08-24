"""Google ID token verification dependency for protected API routes."""

from dataclasses import dataclass

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from app.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


@dataclass(frozen=True)
class AuthenticatedUser:
    """The small, verified subset of claims the API needs."""

    user_id: str
    email: str | None
    name: str | None


def verify_google_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser:
    """Validate a Google ID token supplied through the Bearer scheme."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token is required.",
        )

    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the API server.",
        )

    try:
        claims = id_token.verify_oauth2_token(
            credentials.credentials,
            GoogleRequest(),
            settings.google_oauth_client_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token is invalid or expired.",
        ) from error

    if claims.get("iss") not in GOOGLE_ISSUERS or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token has invalid identity claims.",
        )

    return AuthenticatedUser(
        user_id=claims["sub"],
        email=claims.get("email"),
        name=claims.get("name"),
    )
