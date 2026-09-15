
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID

class LaboratoryTest(Base, BaseMixin):
    __tablename__ = 'laboratory_tests'

    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)