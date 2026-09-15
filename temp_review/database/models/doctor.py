
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey
from sqlalchemy.orm import relationship

class Doctor(Base, BaseMixin):
    __tablename__ = 'doctors'

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    appointments = relationship('Appointment', back_populates='doctor')