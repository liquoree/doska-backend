from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.auth import create_access_token, hash_password, verify_password, get_current_user
from app.database import get_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    nickname: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    login: str  # email или nickname
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    nickname: str


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if session.exec(select(User).where(User.nickname == body.nickname)).first():
        raise HTTPException(status_code=400, detail="Nickname already taken")

    user = User(
        nickname=body.nickname,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user_id=str(user.id), nickname=user.nickname)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    # пробуем найти по email, потом по nickname
    user = session.exec(select(User).where(User.email == body.login)).first()
    if not user:
        user = session.exec(select(User).where(User.nickname == body.login)).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user_id=str(user.id), nickname=user.nickname)


class UserResponse(BaseModel):
    id: str
    nickname: str


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=str(current_user.id), nickname=current_user.nickname)