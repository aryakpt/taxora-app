"""Verify "Sign in with Google" ID tokens (Google Identity Services).

The browser receives a signed ID token from Google and sends it here. It is trusted only if Google's
signature, our client ID (audience), Google's issuer, and the expiry all check out, and the email is
verified by Google. See https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
"""

import asyncio
from dataclasses import dataclass

import jwt

from app.core.config import settings

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_jwks = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600, timeout=10)


class InvalidGoogleCredential(Exception):
    """The token is not a valid, current Google ID token for this application."""


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str  # stable Google account id
    email: str
    name: str | None
    picture: str | None


async def _signing_key(token: str):
    """Google's public key for this token (fetched and cached by PyJWKClient; network call in a thread)."""
    return (await asyncio.to_thread(_jwks.get_signing_key_from_jwt, token)).key


async def verify_credential(token: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise InvalidGoogleCredential("Google sign-in is not configured")
    try:
        claims = jwt.decode(
            token, await _signing_key(token), algorithms=["RS256"], audience=settings.google_client_id,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidGoogleCredential("Invalid Google credential") from exc
    if claims["iss"] not in GOOGLE_ISSUERS:
        raise InvalidGoogleCredential("Token not issued by Google")
    if not claims.get("email") or claims.get("email_verified") is not True:
        raise InvalidGoogleCredential("Google account email is not verified")
    picture = claims.get("picture")
    return GoogleIdentity(
        subject=str(claims["sub"]),
        email=str(claims["email"]).strip().lower(),
        name=(claims.get("name") or "").strip()[:150] or None,
        picture=picture if isinstance(picture, str) and picture.startswith("https://") else None,
    )
