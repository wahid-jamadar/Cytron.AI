
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.database import get_db
from services.billing import generate_bill, get_bill
from schemas.billing import BillingRequest, BillingResponse

router = APIRouter(prefix='/api/v1/billing', tags=['billing'])

@router.post('/generate')
def generate_bill(bill: BillingRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return generate_bill(db, bill)

@router.get('/{bill_id}')
def get_bill_info(bill_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return get_bill(db, bill_id)