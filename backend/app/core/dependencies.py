from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles import Role
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

ACCESS_TOKEN_COOKIE = "access_token"


def _get_token_from_request(
    credentials: HTTPAuthorizationCredentials | None,
    access_token: str | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return access_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    token = _get_token_from_request(credentials, access_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_roles(*allowed_roles: Role) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
