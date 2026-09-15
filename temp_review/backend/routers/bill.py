
from fastapi import APIRouter, Depends
from database.models.bill import Bill
from database.database import get_db
from services.bill_service import BillService
from schemas.bill import BillPaymentResponse

router = APIRouter(prefix="/bill", tags=["bill"])

@router.get("/payment", response_model=BillPaymentResponse)
def get_bill_payment_details(db = Depends(get_db)):
    bill_service = BillService(db)
    bill = bill_service.get_bill_payment_details()
    return bill