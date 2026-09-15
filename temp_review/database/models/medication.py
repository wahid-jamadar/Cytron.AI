
from sqlalchemy import Column, String, UUID
from models.base import Base, BaseMixin

class Medication(Base, BaseMixin):
    __tablename__ = 'medications'
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)