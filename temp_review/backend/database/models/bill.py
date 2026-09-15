
from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    amount = Column(Float, nullable=False)
    payment_status = Column(String, nullable=False)

    patient = relationship("Patient", backref="bills")