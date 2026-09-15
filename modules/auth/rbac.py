from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from modules.database.connection import get_db
from modules.database.models import User, Permission, Role
from modules.auth.service import verify_token

security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to extract JWT credentials and return the authenticated User."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or suspended",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """FastAPI dependency to optionally extract JWT credentials and return the authenticated User."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        return None
        
    try:
        payload = verify_token(token)
        if not payload or payload.get("type") != "access":
            return None
            
        user_id = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id, User.status == "active").first()
    except Exception:
        return None


class PermissionChecker:
    """Dependency checker to enforce RBAC permissions dynamically."""
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        # SUPER_ADMIN has bypass access to all operations
        user_roles = [role.name for role in current_user.roles]
        if "SUPER_ADMIN" in user_roles:
            return current_user
            
        # Compile all permissions for user roles
        user_permissions = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)
                
        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required permission: {self.required_permission}"
            )
            
        return current_user

class RoleChecker:
    """Dependency checker to enforce role checks directly."""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_roles = [role.name for role in current_user.roles]
        
        # SUPER_ADMIN bypasses role checks
        if "SUPER_ADMIN" in user_roles:
            return current_user
            
        if not any(role in user_roles for role in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires role in: {self.allowed_roles}"
            )
            
        return current_user

def has_permission(permission: str):
    """Shorthand wrapper for PermissionChecker dependency."""
    return PermissionChecker(permission)

def has_role(roles: list[str]):
    """Shorthand wrapper for RoleChecker dependency."""
    return RoleChecker(roles)
