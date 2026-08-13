from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import ACCESS_TOKEN_COOKIE, get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services.auth import authenticate_user, issue_access_token, signup_user

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    return signup_user(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    token = issue_access_token(user)
    set_auth_cookie(response, token)
    return TokenResponse()


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
