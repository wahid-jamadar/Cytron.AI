
from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base, BaseMixin

class TestResult(Base, BaseMixin):
    __tablename__ = 'test_results'
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    test_name = Column(String, nullable=False)
    result = Column(String, nullable=False)
    patient = relationship('Patient', back_populates='test_results')