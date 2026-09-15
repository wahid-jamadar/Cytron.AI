
from pydantic import BaseModel

class BillPaymentResponse(BaseModel):
    bill_id: int
    amount: float
    payment_status: str