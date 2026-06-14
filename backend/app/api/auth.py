
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Cookie
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
COOKIE_NAME = "filysis_session"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year

DEV_USER = {
    "union_id": "dev-local-user",
    "name": "Dev User",
    "email": "dev@filysis.local",
    "role": "admin",
}


def create_token(user_id: int, union_id: str) -> str:

    payload = {
        "user_id": user_id,
        "union_id": union_id,
        "exp": datetime.utcnow() + timedelta(days=365),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.app_secret, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:

    try:
        payload = jwt.decode(token, settings.app_secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    
    payload = verify_token(token)
    if not payload:
        return None
    
    return db.query(User).filter(User.id == payload["user_id"]).first()


def ensure_dev_user(db: Session) -> User:

    user = db.query(User).filter(User.union_id == DEV_USER["union_id"]).first()
    if not user:
        user = User(
            union_id=DEV_USER["union_id"],
            name=DEV_USER["name"],
            email=DEV_USER["email"],
            role=DEV_USER["role"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created dev user: {user.name} (id={user.id})")
    return user


@router.post("/dev-login")
def dev_login(response: Response, db: Session = Depends(get_db)):
  


    user = ensure_dev_user(db)
    
    user.last_sign_in_at = datetime.utcnow()
    db.commit()
    
    token = create_token(user.id, user.union_id)
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
    }


@router.post("/logout")
def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"success": True}
