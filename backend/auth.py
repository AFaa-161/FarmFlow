"""Basic FarmFlow email/password authentication for the hackathon prototype.

Uses SQLite + PBKDF2 password hashes and HMAC-signed bearer tokens.
Set FARMFLOW_SECRET_KEY to a long random secret before deployment.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)
DB_PATH = Path(__file__).resolve().parent / "users.db"
SECRET_KEY = os.getenv("FARMFLOW_SECRET_KEY", "CHANGE_THIS_DEV_SECRET_BEFORE_DEPLOYMENT").encode("utf-8")
TOKEN_TTL_SECONDS = 60 * 60 * 12


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_auth_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derived).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_text, hash_text = stored.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(hash_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_token(user_id: int, email: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({"sub": user_id, "email": email, "exp": int(time.time()) + TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode()
        expected = b64url(hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(decoded.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return decoded
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired login session. Please log in again.") from exc


class SignupBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def auth_response(user_id: int, email: str, full_name: str):
    return {
        "access_token": create_token(user_id, email),
        "token_type": "bearer",
        "email": email,
        "full_name": full_name,
        "expires_in": TOKEN_TTL_SECONDS,
    }


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupBody):
    email = str(body.email).strip().lower()
    full_name = body.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (full_name, email, hash_password(body.password), int(time.time())),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Log in instead.") from exc
    return auth_response(user_id, email, full_name)


@router.post("/login")
def login(body: LoginBody):
    email = str(body.email).strip().lower()
    with get_connection() as connection:
        user = connection.execute("SELECT id, full_name, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return auth_response(user["id"], user["email"], user["full_name"])


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Please log in to continue.")
    claims = decode_token(credentials.credentials)
    with get_connection() as connection:
        user = connection.execute("SELECT id, full_name, email FROM users WHERE id = ?", (claims.get("sub"),)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please log in again.")
    return dict(user)


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "full_name": user["full_name"]}
