
from database.models.staff import Staff
from database.database import get_db
from sqlalchemy.orm import Session
from auth.jwt import create_token

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, login_request):
        staff = self.db.query(Staff).filter(Staff.username == login_request.username).first()
        if staff and staff.password == login_request.password:
            token = create_token(staff.id)
            return token
        else:
            return None