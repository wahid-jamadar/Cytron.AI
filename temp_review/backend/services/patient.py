
from database.models.patient import Patient
from database.database import get_db
from schemas.patient import PatientRequest

def create_patient(db: Session, patient: PatientRequest):
    new_patient = Patient(name=patient.name, email=patient.email, phone=patient.phone)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

def get_patient(db: Session, patient_id: int):
    return db.query(Patient).filter(Patient.id == patient_id).first()