import jwt
import bcrypt
import os
import base64
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from config.settings import settings
from modules.database.models import User, Session as UserSession, PasswordHistory, ApiKey, UserPreferences

# Secure encryption key for personal API keys
# In production, this should be loaded from environment settings
ENCRYPTION_KEY = base64.urlsafe_b64encode(settings.jwt_secret.encode('utf-8').ljust(32)[:32])
cipher_suite = Fernet(ENCRYPTION_KEY)

# ── Hashing Helpers ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ── Encryption Helpers for API Keys ───────────────────────────────────────────

def encrypt_key(plain_key: str) -> str:
    """Encrypt an API key before storage."""
    return cipher_suite.encrypt(plain_key.encode('utf-8')).decode('utf-8')

def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an API key for usage."""
    return cipher_suite.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')

# ── JWT Helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, roles: list[str]) -> str:
    """Create a short-lived JWT Access Token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def verify_token(token: str) -> dict | None:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None

# ── Session & Refresh Token Management ───────────────────────────────────────

def create_refresh_token(db: Session, user_id: int, ip_address: str = None, user_agent: str = None) -> str:
    """Generate a long-lived Refresh Token and store the session in the database."""
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    # Deactivate existing sessions for this user to enforce security
    db.query(UserSession).filter(
        UserSession.user_id == user_id, 
        UserSession.is_active == True
    ).update({"is_active": False})
    
    session = UserSession(
        user_id=user_id,
        refresh_token=token,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=True,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    return token

def refresh_user_session(db: Session, refresh_token: str) -> tuple[str, str] | None:
    """Verify refresh token and issue a new access token and a rotated refresh token."""
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        return None
        
    user = db.query(User).filter(User.id == session.user_id, User.status == "active").first()
    if not user:
        return None
        
    # Rotate refresh token
    new_refresh = str(uuid4())
    session.refresh_token = new_refresh
    session.expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    db.commit()
    
    roles_list = [role.name for role in user.roles]
    new_access = create_access_token(user.id, user.email, roles_list)
    return new_access, new_refresh

def invalidate_refresh_token(db: Session, refresh_token: str) -> bool:
    """Invalidate a session token upon user logout."""
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if session:
        session.is_active = False
        db.commit()
        return True
    return False

# ── Password History Management ───────────────────────────────────────────────

def add_to_password_history(db: Session, user_id: int, hashed_password: str):
    """Save the hashed password to history, keeping only the 3 most recent entries."""
    # Add new record
    history_entry = PasswordHistory(user_id=user_id, hashed_password=hashed_password)
    db.add(history_entry)
    db.flush()
    
    # Retrieve history, sort descending by date
    history = db.query(PasswordHistory).filter(PasswordHistory.user_id == user_id).order_by(PasswordHistory.created_at.desc()).all()
    
    # If history is larger than 3 entries, remove older ones
    if len(history) > 3:
        for old in history[3:]:
            db.delete(old)
    db.commit()

def is_password_reused(db: Session, user_id: int, password: str) -> bool:
    """Verify if the password matches any of the user's last 3 passwords."""
    history = db.query(PasswordHistory).filter(PasswordHistory.user_id == user_id).all()
    for entry in history:
        if verify_password(password, entry.hashed_password):
            return True
    return False

# ── Forgot / Reset Password Tokens ───────────────────────────────────────────
# In-memory dictionary for password reset tokens mapping reset_token -> (user_id, expires_at)
# This serves as a lightweight, clean store suitable for both local development and scale-out.
reset_tokens: dict[str, tuple[int, datetime]] = {}

def generate_reset_token(user_id: int) -> str:
    """Generate a password reset token valid for 30 minutes."""
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    reset_tokens[token] = (user_id, expires_at)
    return token

def verify_reset_token(token: str) -> int | None:
    """Verify a reset token and return the associated user_id if valid."""
    if token not in reset_tokens:
        return None
    user_id, expires_at = reset_tokens[token]
    if datetime.utcnow() > expires_at:
        del reset_tokens[token] # Clean expired
        return None
    return user_id

def clear_reset_token(token: str):
    """Remove a reset token after successful use."""
    if token in reset_tokens:
        del reset_tokens[token]
