
from pydantic import BaseModel

class BillingRequest(BaseModel):
    patient_id: int
    appointment_id: int
    amount: float

class BillingResponse(BaseModel):
    id: int
    patient_id: int
    appointment_id: int
    amount: float