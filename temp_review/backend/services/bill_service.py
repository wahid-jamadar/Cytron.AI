
from database.models.bill import Bill
from database.database import get_db
from sqlalchemy.orm import Session

class BillService:
    def __init__(self, db: Session):
        self.db = db

    def get_bill_payment_details(self):
        bill = self.db.query(Bill).first()
        return bill