
from fastapi import APIRouter, Depends
from database.models.medical_record import MedicalRecord
from database.database import get_db
from services.medical_record_service import MedicalRecordService
from schemas.medical_record import MedicalRecordResponse

router = APIRouter(prefix="/medical-record", tags=["medical-record"])

@router.get("/", response_model=MedicalRecordResponse)
def get_medical_record(db = Depends(get_db)):
    medical_record_service = MedicalRecordService(db)
    medical_record = medical_record_service.get_medical_record()
    return medical_record