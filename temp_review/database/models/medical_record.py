
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey
from sqlalchemy.orm import relationship

class MedicalRecord(Base, BaseMixin):
    __tablename__ = 'medical_records'

    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    description = Column(String, nullable=False)
    patient = relationship('Patient', back_populates='medical_records')