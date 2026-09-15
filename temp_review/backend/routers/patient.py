
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.database import get_db
from services.patient import create_patient, get_patient
from schemas.patient import PatientRequest, PatientResponse

router = APIRouter(prefix='/api/v1/patient', tags=['patient'])

@router.post('/register')
def register_patient(patient: PatientRequest, db: Session = Depends(get_db)):
    return create_patient(db, patient)

@router.get('/{patient_id}')
def get_patient_info(patient_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return get_patient(db, patient_id)