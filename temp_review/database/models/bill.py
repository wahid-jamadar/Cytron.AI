
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey
from sqlalchemy.orm import relationship

class Bill(Base, BaseMixin):
    __tablename__ = 'bills'

    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.id'), nullable=False)
    amount = Column(Float, nullable=False)
    patient = relationship('Patient', back_populates='bills')
    appointment = relationship('Appointment', back_populates='bills')