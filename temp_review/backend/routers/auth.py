
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.database import get_db
from services.auth import login, register
from schemas.auth import LoginRequest, RegisterRequest

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])

@router.post('/login')
def login_user(login: LoginRequest, db: Session = Depends(get_db)):
    return login(db, login)

@router.post('/register')
def register_user(register: RegisterRequest, db: Session = Depends(get_db)):
    return register(db, register)