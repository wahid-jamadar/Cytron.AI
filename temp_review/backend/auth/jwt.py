
from jose import jwt
from datetime import datetime, timedelta

def create_token(user_id: int):
    payload = {
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "sub": user_id
    }
    return jwt.encode(payload, "secret_key", algorithm="HS256")