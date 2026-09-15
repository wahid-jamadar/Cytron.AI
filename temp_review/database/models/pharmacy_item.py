
from models.base import Base, BaseMixin
from sqlalchemy import Column, String, Integer, Float, UUID

class PharmacyItem(Base, BaseMixin):
    __tablename__ = 'pharmacy_items'

    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)