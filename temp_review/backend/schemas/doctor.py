
from pydantic import BaseModel

class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int
    name: str
    availability: bool