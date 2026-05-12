from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import jwt
from jwt import PyJWKClient
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
    if settings.auth_mode == "cognito":
        return _decode_cognito_token(token)

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


def _decode_cognito_token(token: str) -> Actor:
    settings = get_settings()
    if not settings.cognito_user_pool_id or not settings.cognito_client_id:
        raise AuthError("missing_cognito_configuration")

    jwks_url = _cognito_jwks_url()
    try:
        signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "token_use"]},
        )
    except InvalidTokenError as exc:
        raise AuthError("invalid_cognito_token") from exc

    if payload.get("token_use") != "id":
        raise AuthError("invalid_cognito_token_use")

    groups = payload.get("cognito:groups", [])
    if isinstance(groups, str):
        groups = [groups]

    role = _role_from_groups(groups)
    team = payload.get("custom:team") or payload.get("team") or ("platform" if role == Role.admin else "payments")
    user_id = payload.get("cognito:username") or payload["sub"]

    try:
        return Actor(user_id=user_id, role=role, team=team)
    except (ValidationError, ValueError) as exc:
        raise AuthError("invalid_actor_claims") from exc


def _role_from_groups(groups: list[str]) -> Role:
    group_set = set(groups)
    if "admin" in group_set:
        return Role.admin
    if "manager" in group_set:
        return Role.manager
    if "employee" in group_set:
        return Role.employee
    raise AuthError("missing_cognito_role_group")


def _cognito_jwks_url() -> str:
    settings = get_settings()
    return (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )


def jwks_document() -> dict:
    settings = get_settings()
    if settings.auth_mode == "cognito":
        if not settings.cognito_user_pool_id:
            return {"keys": []}
        try:
            response = httpx.get(_cognito_jwks_url(), timeout=settings.opa_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError:
            return {"keys": []}
        return response.json()

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
