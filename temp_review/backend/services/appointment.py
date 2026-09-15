
from database.models.appointment import Appointment
from database.database import get_db
from schemas.appointment import AppointmentRequest

def book_appointment(db: Session, appointment: AppointmentRequest):
    new_appointment = Appointment(patient_id=appointment.patient_id, doctor_id=appointment.doctor_id, date=appointment.date, time=appointment.time)
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return new_appointment

def get_appointment(db: Session, appointment_id: int):
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()