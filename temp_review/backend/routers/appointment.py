
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.database import get_db
from services.appointment import book_appointment, get_appointment
from schemas.appointment import AppointmentRequest, AppointmentResponse

router = APIRouter(prefix='/api/v1/appointment', tags=['appointment'])

@router.post('/book')
def book_appointment(appointment: AppointmentRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return book_appointment(db, appointment)

@router.get('/{appointment_id}')
def get_appointment_info(appointment_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return get_appointment(db, appointment_id)