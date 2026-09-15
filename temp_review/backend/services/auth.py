
from database.models.user import User
from database.database import get_db
from schemas.auth import LoginRequest, RegisterRequest
from auth.jwt import create_access_token
from auth.dependencies import get_password_hash

def login(db: Session, login: LoginRequest):
    user = db.query(User).filter(User.username == login.username).first()
    if not user or not user.check_password(login.password):
        raise HTTPException(status_code=401, detail='Invalid username or password')
    access_token = create_access_token(data={'sub': user.username})
    return {'access_token': access_token