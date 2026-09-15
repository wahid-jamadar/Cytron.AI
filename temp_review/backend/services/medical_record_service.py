
from database.models.medical_record import MedicalRecord
from database.database import get_db
from sqlalchemy.orm import Session

class MedicalRecordService:
    def __init__(self, db: Session):
        self.db = db

    def get_medical_record(self):
        medical_record = self.db.query(MedicalRecord).first()
        return medical_record