
from pydantic import BaseModel

class PatientRequest(BaseModel):
    name: str
    email: str
    phone: str

class PatientResponse(BaseModel):
    id: int
    name: str
    email: str