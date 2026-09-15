
from database.models.doctor import Doctor
from database.database import get_db
from sqlalchemy.orm import Session

class DoctorService:
    def __init__(self, db: Session):
        self.db = db

    def get_doctor_availability(self):
        doctors = self.db.query(Doctor).all()
        return doctors