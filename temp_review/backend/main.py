
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database.database import get_db
from auth.dependencies import get_current_user
from routers import patient_router, appointment_router, billing_router, auth_router

app = FastAPI()

origins = [
    '*'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(patient_router)
app.include_router(appointment_router)
app.include_router(billing_router)
app.include_router(auth_router)

@app.get('/health')
def health_check():
    return {'status': 'ok'}