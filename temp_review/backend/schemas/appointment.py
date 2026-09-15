
from pydantic import BaseModel

class AppointmentRequest(BaseModel):
    patient_id: int
    doctor_id: int
    date: str
    time: str

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    date: str
    time: str