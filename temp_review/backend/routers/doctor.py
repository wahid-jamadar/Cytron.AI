
from fastapi import APIRouter, Depends
from database.models.doctor import Doctor
from database.database import get_db
from services.doctor_service import DoctorService
from schemas.doctor import DoctorAvailabilityResponse

router = APIRouter(prefix="/doctor", tags=["doctor"])

@router.get("/availability", response_model=list[DoctorAvailabilityResponse])
def get_doctor_availability(db = Depends(get_db)):
    doctor_service = DoctorService(db)
    doctors = doctor_service.get_doctor_availability()
    return doctors