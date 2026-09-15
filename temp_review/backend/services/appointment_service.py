
from database.models.appointment import Appointment
from database.database import get_db
from sqlalchemy.orm import Session

class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    def book_appointment(self, appointment_request):
        appointment = Appointment(patient_id=appointment_request.patient_id, doctor_id=appointment_request.doctor_id, date=appointment_request.date, time=appointment_request.time)
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment.id