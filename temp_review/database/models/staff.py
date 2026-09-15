
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID

class Staff(Base, BaseMixin):
    __tablename__ = 'staff'

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)