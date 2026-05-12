from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import jwt
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from .models import Actor, Role
from .settings import get_settings

security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _sign(message: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_demo_token(actor: Actor, expires_in_seconds: int = 3600) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": actor.user_id,
        "role": actor.role.value,
        "team": actor.team,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "iss": settings.jwt_issuer,
    }
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience

    if settings.auth_mode == "jwks":
        if not settings.jwks_private_key_pem:
            raise AuthError("missing_jwks_private_key")
        return jwt.encode(
            payload,
            settings.jwks_private_key_pem,
            algorithm="RS256",
            headers={"kid": settings.jwks_key_id, "typ": "JWT"},
        )

    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    return f"{signing_input}.{_sign(signing_input, settings.auth_secret)}"


def decode_token(token: str) -> Actor:
    settings = get_settings()
    if settings.auth_mode == "jwks":
        return _decode_jwks_token(token)

    try:
        encoded_header, encoded_payload, signature = token.split(".", maxsplit=2)
    except ValueError as exc:
        raise AuthError("malformed_token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected = _sign(signing_input, settings.auth_secret)
    if not hmac.compare_digest(signature, expected):
        raise AuthError("invalid_token_signature")

    try:
        header = json.loads(_b64url_decode(encoded_header))
        payload = json.loads(_b64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AuthError("invalid_token_payload") from exc

    if header.get("alg") != "HS256":
        raise AuthError("unsupported_token_algorithm")

    expires_at = int(payload.get("exp", 0))
    if expires_at < int(datetime.now(UTC).timestamp()):
        raise AuthError("token_expired")

    try:
        return Actor(user_id=payload["sub"], role=Role(payload["role"]), team=payload["team"])
    except (KeyError, ValidationError, ValueError) as exc:
        raise AuthError("invalid_actor_claims") from exc


def _decode_jwks_token(token: str) -> Actor:
    settings = get_settings()
    if not settings.jwks_public_key_pem:
        raise AuthError("missing_jwks_public_key")

    try:
        options = {"require": ["exp", "iat", "iss", "sub"]}
        payload = jwt.decode(
            token,
            settings.jwks_public_key_pem,
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options=options,
        )
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise AuthError("invalid_jwks_token") from exc

    if header.get("kid") != settings.jwks_key_id:
        raise AuthError("unknown_jwks_key_id")

    try:
        return Actor(user_id=payload["sub"], role=Role(payload["role"]), team=payload["team"])
    except (KeyError, ValidationError, ValueError) as exc:
        raise AuthError("invalid_actor_claims") from exc


def jwks_document() -> dict:
    settings = get_settings()
    if not settings.jwks_public_key_pem:
        return {"keys": []}

    public_key = load_pem_public_key(settings.jwks_public_key_pem.encode("utf-8"))
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": settings.jwks_key_id, "alg": "RS256", "use": "sig"})
    return {"keys": [jwk]}


def require_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Actor:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_manager_or_admin(actor: Annotated[Actor, Depends(require_actor)]) -> Actor:
    if actor.role not in {Role.manager, Role.admin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="manager_or_admin_required")
    return actor


def require_admin(actor: Annotated[Actor, Depends(require_actor)]) -> Actor:
    if actor.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return actor
