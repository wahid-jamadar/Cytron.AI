
from database.models.patient import Patient
from database.database import get_db
from sqlalchemy.orm import Session

class PatientService:
    def __init__(self, db: Session):
        self.db = db

    def register_patient(self, patient_request):
        patient = Patient(name=patient_request.name, email=patient_request.email, phone=patient_request.phone)
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient.id