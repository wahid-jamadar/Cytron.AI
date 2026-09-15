
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey
from sqlalchemy.orm import relationship

class Patient(Base, BaseMixin):
    __tablename__ = 'patients'

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    appointments = relationship('Appointment', back_populates='patient')
    bills = relationship('Bill', back_populates='patient')
    medical_records = relationship('MedicalRecord', back_populates='patient')