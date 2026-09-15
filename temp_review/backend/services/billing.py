
from database.models.billing import Bill
from database.database import get_db
from schemas.billing import BillingRequest

def generate_bill(db: Session, bill: BillingRequest):
    new_bill = Bill(patient_id=bill.patient_id, appointment_id=bill.appointment_id, amount=bill.amount)
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)
    return new_bill

def get_bill(db: Session, bill_id: int):
    return db.query(Bill).filter(Bill.id == bill_id).first()