from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import SignupRequest


def signup_user(db: Session, data: SignupRequest) -> User:
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=Role.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user


def issue_access_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role.value)


def create_admin_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=Role.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
