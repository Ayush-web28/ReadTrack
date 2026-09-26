"""
security.py: passwords and JWT tokens. No web/route code here, just tools.

TWO SEPARATE JOBS:
  1. Passwords: we never store them, only a one-way HASH. At login we hash
     what the user typed and compare. bcrypt is deliberately slow and adds a
     random "salt", so stolen hashes are very hard to crack.
  2. Tokens: after a successful login we hand out a signed JWT. The client
     sends it back on every request (Authorization: Bearer <token>) and we
     verify the signature instead of asking for the password again.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# The SECRET KEY signs every token. Anyone who knows it can forge tokens for
# any user, so in real life it comes from the environment, never from git.
# The fallback below is for local development ONLY.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-32b")
ALGORITHM = "HS256"                 # HMAC-SHA256: one shared secret signs AND verifies
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))


def hash_password(password: str) -> str:
    # bcrypt works on bytes, so encode; gensalt() makes a fresh random salt.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    # checkpw re-hashes `password` using the salt stored inside the hash.
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    """Build and sign a JWT whose payload says who the user is and when it expires."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),                                     # subject = the user id
        "iat": now,                                              # issued at
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),    # expires at
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Return the user id inside a valid token, or None if the token is bad.
    jwt.decode() checks the signature AND the expiry for us. We pass the list
    of allowed algorithms explicitly so an attacker cannot pick a weaker one.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        # InvalidTokenError covers: bad signature, expired, malformed.
        return None
