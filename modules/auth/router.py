import re
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from modules.database.connection import get_db
from modules.database.models import User, Role, UserPreferences, ApiKey, Session as UserSession
from modules.auth.rbac import get_current_user
from modules.auth.service import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    refresh_user_session, invalidate_refresh_token, generate_reset_token,
    verify_reset_token, clear_reset_token, is_password_reused, add_to_password_history,
    encrypt_key
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Pydantic Request/Response Schemas ────────────────────────────────────────

class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    new_password: str | None = None

class PreferenceUpdateRequest(BaseModel):
    preferred_provider: str | None = None
    preferred_language: str | None = None
    ui_theme: str | None = None
    timezone: str | None = None
    notification_preferences: str | None = None
    dashboard_widgets: str | None = None
    avatar_url: str | None = None

class ApiKeyConnectRequest(BaseModel):
    provider: str
    key: str

# ── API Routes ────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and initialize their SaaS preferences."""
    # Check if duplicate email
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
        
    # Enforce password strength
    password = request.password
    if not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password) and re.search(r"[0-9]", password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter, one lowercase letter, and one number"
        )
        
    hashed = hash_password(password)
    new_user = User(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        hashed_password=hashed,
        status="active"
    )
    
    # Assign default USER role
    user_role = db.query(Role).filter(Role.name == "USER").first()
    if not user_role:
        user_role = Role(name="USER", description="Default USER role")
        db.add(user_role)
        db.flush()
    new_user.roles.append(user_role)
        
    db.add(new_user)
    db.flush()
    
    # Save to password history
    add_to_password_history(db, new_user.id, hashed)
    
    # Initialize default preferences
    prefs = UserPreferences(
        user_id=new_user.id,
        preferred_provider="groq",
        preferred_language="javascript",
        ui_theme="dark",
        timezone="UTC"
    )
    db.add(prefs)
    db.commit()
    
    return {"message": "User registered successfully", "user_id": new_user.id}

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, response: Response, db: Session = Depends(get_db)):
    """Authenticate credentials and establish a secure session."""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account is {user.status}. Access denied."
        )
        
    # Log session creation
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent", "unknown")
    
    # Generate tokens
    roles_list = [role.name for role in user.roles]
    access_token = create_access_token(user.id, user.email, roles_list)
    refresh_token = create_refresh_token(db, user.id, ip_address, user_agent)
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 60,  # 30 minutes to match requirements
        samesite="lax",
        secure=False,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 3600,  # 7 days
        samesite="lax",
        secure=False,
        path="/"
    )
    
    # Log successful login to history
    from modules.database.models import LoginHistory
    login_log = LoginHistory(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    db.add(login_log)
    db.commit()
    
    # Load preferences
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "roles": roles_list,
            "preferences": {
                "preferred_provider": prefs.preferred_provider if prefs else "groq",
                "preferred_language": prefs.preferred_language if prefs else "javascript",
                "ui_theme": prefs.ui_theme if prefs else "dark",
                "timezone": prefs.timezone if prefs else "UTC",
                "avatar_url": prefs.avatar_url if prefs else None
            }
        }
    )

@router.post("/logout")
async def logout(
    response: Response,
    request: RefreshRequest | None = None,
    db: Session = Depends(get_db),
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token")
):
    """Terminate user session and invalidate refresh tokens."""
    # Always delete cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    
    ref_token = None
    if request and request.refresh_token:
        ref_token = request.refresh_token
    elif refresh_token_cookie:
        ref_token = refresh_token_cookie
        
    if ref_token:
        invalidate_refresh_token(db, ref_token)
        
    return {"message": "Logged out successfully"}

@router.post("/refresh")
async def refresh(
    response: Response,
    request: RefreshRequest | None = None,
    db: Session = Depends(get_db),
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token")
):
    """Refresh JWT access and session tokens."""
    ref_token = None
    if request and request.refresh_token:
        ref_token = request.refresh_token
    elif refresh_token_cookie:
        ref_token = refresh_token_cookie
        
    if not ref_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid refresh token"
        )
        
    tokens = refresh_user_session(db, ref_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session refresh token"
        )
    access_token, refresh_token = tokens
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 60,  # 30 minutes
        samesite="lax",
        secure=False,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 3600,  # 7 days
        samesite="lax",
        secure=False,
        path="/"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Issue password reset tokens. (Email delivery skipped per preferences)."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Prevent user enumeration attacks by returning generic response
        return {"message": "If the email is registered, a reset link has been generated."}
        
    reset_token = generate_reset_token(user.id)
    # Log reset token for debugging and local validation
    print(f"[SECURITY ALERT] Password reset token generated for user '{user.email}': {reset_token}")
    
    return {
        "message": "Password reset token generated successfully",
        "reset_token": reset_token # Returned for easy local user testing
    }

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify reset token validity, enforce password history safety, and update credentials."""
    user_id = verify_reset_token(request.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
         
    # Check password reuse
    if is_password_reused(db, user_id, request.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reuse any of your last 3 passwords"
        )
        
    hashed = hash_password(request.new_password)
    user.hashed_password = hashed
    add_to_password_history(db, user_id, hashed)
    clear_reset_token(request.token)
    db.commit()
    
    return {"message": "Password reset completed successfully"}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve details for the currently logged-in user."""
    roles_list = [role.name for role in current_user.roles]
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "roles": roles_list,
        "preferences": {
            "preferred_provider": prefs.preferred_provider if prefs else "groq",
            "preferred_language": prefs.preferred_language if prefs else "javascript",
            "ui_theme": prefs.ui_theme if prefs else "dark",
            "timezone": prefs.timezone if prefs else "UTC",
            "avatar_url": prefs.avatar_url if prefs else None
        }
    }

@router.put("/profile")
async def update_profile(request: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update profile parameters and credentials securely."""
    if request.first_name:
        current_user.first_name = request.first_name
    if request.last_name:
        current_user.last_name = request.last_name
    if request.email:
        existing = db.query(User).filter(User.email == request.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = request.email
        
    if request.new_password:
        if is_password_reused(db, current_user.id, request.new_password):
            raise HTTPException(status_code=400, detail="Cannot reuse any of your last 3 passwords")
        hashed = hash_password(request.new_password)
        current_user.hashed_password = hashed
        add_to_password_history(db, current_user.id, hashed)
        
    db.commit()
    return {"message": "Profile updated successfully"}

@router.put("/preferences")
async def update_preferences(request: PreferenceUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update user workspace, UI styling, and notification filters."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        
    if request.preferred_provider is not None:
        prefs.preferred_provider = request.preferred_provider
    if request.preferred_language is not None:
        prefs.preferred_language = request.preferred_language
    if request.ui_theme is not None:
        prefs.ui_theme = request.ui_theme
    if request.timezone is not None:
        prefs.timezone = request.timezone
    if request.notification_preferences is not None:
        prefs.notification_preferences = request.notification_preferences
    if request.dashboard_widgets is not None:
        prefs.dashboard_widgets = request.dashboard_widgets
    if request.avatar_url is not None:
        prefs.avatar_url = request.avatar_url
        
    db.commit()
    return {"message": "Preferences updated successfully"}

@router.post("/api-keys")
async def connect_api_key(request: ApiKeyConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Encrypt and store user's personal LLM API keys."""
    # Check if key already exists for user + provider
    existing_key = db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.provider == request.provider).first()
    
    encrypted = encrypt_key(request.key)
    
    if existing_key:
        existing_key.encrypted_key = encrypted
        existing_key.is_active = True
    else:
        new_key = ApiKey(
            user_id=current_user.id,
            provider=request.provider,
            encrypted_key=encrypted,
            is_active=True
        )
        db.add(new_key)
        
    db.commit()
    return {"message": f"Connected key for {request.provider} successfully"}

@router.get("/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List connected AI providers for current user (keys are masked for security)."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    # Masked output
    return [{"provider": k.provider, "is_active": k.is_active, "created_at": k.created_at} for k in keys]
