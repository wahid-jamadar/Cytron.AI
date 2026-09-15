
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey
from sqlalchemy.orm import relationship

class Appointment(Base, BaseMixin):
    __tablename__ = 'appointments'

    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey('doctors.id'), nullable=False)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    patient = relationship('Patient', back_populates='appointments')
    doctor = relationship('Doctor', back_populates='appointments')
    bills = relationship('Bill', back_populates='appointment')