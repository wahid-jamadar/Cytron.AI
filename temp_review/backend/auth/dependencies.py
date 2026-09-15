
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt import verify_token

security = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    token = verify_token(token.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token