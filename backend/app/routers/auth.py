from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload["sub"]


# bcrypt hash of a random, unusable value — verified against on unknown users so that
# login timing doesn't reveal whether the email matched (avoids user-enumeration via timing).
_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeOWn8QVvV9m7mNqvKfeCf5Z1xC1c3vJ8O"


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    valid_user = body.email == settings.app_username
    hash_to_check = settings.app_password_hash if valid_user else _DUMMY_HASH
    valid_password = verify_password(body.password, hash_to_check)

    if not (valid_user and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=body.email)
    return LoginResponse(token=token)


@router.get("/verify")
async def verify(current_user: str = Depends(get_current_user)):
    return {"valid": True, "user": current_user}
