import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth


def test_google_auth_rejects_missing_bearer_token() -> None:
    with pytest.raises(HTTPException) as error:
        auth.verify_google_user(None)

    assert error.value.status_code == 401


def test_google_auth_verifies_token_and_returns_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id.apps.googleusercontent.com")

    def fake_verify(token: str, request: object, audience: str) -> dict[str, str]:
        assert token == "valid-token"
        assert audience == "client-id.apps.googleusercontent.com"
        return {
            "iss": "https://accounts.google.com",
            "sub": "google-user-123",
            "email": "learner@example.com",
            "name": "Learner",
        }

    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", fake_verify)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

    user = auth.verify_google_user(credentials)

    assert user.user_id == "google-user-123"
    assert user.email == "learner@example.com"


def test_google_auth_rejects_invalid_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth.id_token,
        "verify_oauth2_token",
        lambda *args: {"iss": "https://invalid.example", "sub": "google-user-123"},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as error:
        auth.verify_google_user(credentials)

    assert error.value.status_code == 401
