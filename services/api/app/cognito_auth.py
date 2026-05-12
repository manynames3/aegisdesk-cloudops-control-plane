from __future__ import annotations

import base64
import hashlib
import hmac

import boto3
from botocore.exceptions import ClientError

from .models import Actor, Role
from .settings import Settings


class CognitoSessionError(Exception):
    pass


def create_persona_session(role: Role, team: str | None, settings: Settings) -> tuple[str, Actor]:
    if not settings.persona_auth_enabled:
        raise CognitoSessionError("persona_auth_disabled")
    if not settings.cognito_user_pool_id or not settings.cognito_client_id:
        raise CognitoSessionError("missing_cognito_configuration")

    resolved_team = team or ("platform" if role == Role.admin else "payments")
    username = f"aegisdesk-{role.value}"
    password = _persona_password(settings.persona_password_seed, role)
    actor = Actor(user_id=username, role=role, team=resolved_team)
    client = boto3.client("cognito-idp", region_name=settings.cognito_region)

    _ensure_user(client, settings.cognito_user_pool_id, username, password, role, resolved_team)
    id_token = _initiate_auth(client, settings.cognito_user_pool_id, settings.cognito_client_id, username, password)
    return id_token, actor


def _ensure_user(client, user_pool_id: str, username: str, password: str, role: Role, team: str) -> None:
    attributes = [
        {"Name": "preferred_username", "Value": username},
        {"Name": "custom:team", "Value": team},
    ]
    try:
        client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            TemporaryPassword=password,
            MessageAction="SUPPRESS",
            UserAttributes=attributes,
        )
        client.admin_set_user_password(UserPoolId=user_pool_id, Username=username, Password=password, Permanent=True)
    except client.exceptions.UsernameExistsException:
        client.admin_update_user_attributes(UserPoolId=user_pool_id, Username=username, UserAttributes=attributes)

    try:
        client.admin_add_user_to_group(UserPoolId=user_pool_id, Username=username, GroupName=role.value)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise


def _initiate_auth(client, user_pool_id: str, client_id: str, username: str, password: str) -> str:
    try:
        response = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
    except ClientError as exc:
        raise CognitoSessionError("cognito_auth_failed") from exc

    token = response.get("AuthenticationResult", {}).get("IdToken")
    if not token:
        raise CognitoSessionError("missing_cognito_id_token")
    return token


def _persona_password(seed: str, role: Role) -> str:
    digest = hmac.new(seed.encode("utf-8"), role.value.encode("utf-8"), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")[:24]
    return f"AegisDesk1!{token}a"
