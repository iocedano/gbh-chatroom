from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError as JWTInvalidTokenError

from infra.settings import get_settings

settings = get_settings()


class InvalidTokenError(ValueError):
    pass


def create_access_token(*, subject: str, expires_delta: timedelta | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTInvalidTokenError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc
