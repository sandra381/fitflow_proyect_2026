import os

import jwt
import structlog
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_SECRET_PREVIOUS = os.getenv("JWT_SECRET_PREVIOUS") or None

JWT_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def _decode_with_rotation(token: str) -> dict:
    """Intenta decodificar con el secreto actual; si falla por firma
    inválida y hay un secreto anterior configurado, lo intenta con ese
    antes de rendirse. ExpiredSignatureError se propaga de inmediato -- un
    token expirado sigue expirado sin importar qué secreto se use."""
    secrets_to_try = [JWT_SECRET] + ([JWT_SECRET_PREVIOUS] if JWT_SECRET_PREVIOUS else [])

    last_error: jwt.InvalidTokenError | None = None
    for secret in secrets_to_try:
        try:
            return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as exc:
            last_error = exc
            continue

    raise last_error


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = credentials.credentials
    try:
        payload = _decode_with_rotation(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token")

    user_id = int(payload["sub"])
    structlog.contextvars.bind_contextvars(user_id=user_id)
    return user_id

