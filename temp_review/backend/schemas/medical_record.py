
from pydantic import BaseModel

class MedicalRecordResponse(BaseModel):
    medical_record_id: int
    patient_id: int
    record: str