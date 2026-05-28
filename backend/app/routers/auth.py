from fastapi import APIRouter, Depends, HTTPException, Cookie, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..auth.utils import verify_password, make_session_token, decode_session_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


def get_current_user(
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_session_token(session_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.get(User, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_session_token(user_id=user.id, org_id=user.org_id)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 30,
        samesite="lax",
    )
    return {"token": token, "org_id": user.org_id, "email": user.email}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "org_id": current_user.org_id}
