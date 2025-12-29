import os
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError

# ===========================
# ENV CONFIG (safe defaults)
# ===========================

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key!!!")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
)  # 7 days


# ===========================
# PASSWORD HASHING
# ===========================

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a stored password."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ===========================
# JWT TOKEN CREATION
# ===========================

def create_access_token(data: dict):
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ===========================
# TOKEN DECODING
# ===========================

def decode_token(token: str) -> dict:
    """Decode a JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise e
