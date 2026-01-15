from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.core.security import decode_access_token
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role

security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Users:
    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(Users).filter(Users.id == token_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return user

def get_user_roles(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> List[UserRoles]:
    """Get all roles for current user"""
    return db.query(UserRoles).filter(UserRoles.user_id == current_user.id).all()

def require_admin(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> Users:
    """Require user to have ADMIN role (store_id=None means global admin)"""
    admin_role = db.query(UserRoles).filter(
        UserRoles.user_id == current_user.id,
        UserRoles.role == Role.ADMIN,
        UserRoles.store_id.is_(None)
    ).first()
    
    if not admin_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    return current_user

def require_manager_or_admin(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> Users:
    """Require user to have MANAGER or ADMIN role"""
    role = db.query(UserRoles).filter(
        UserRoles.user_id == current_user.id,
        UserRoles.role.in_([Role.ADMIN, Role.MANAGER])
    ).first()
    
    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin access required")
    
    return current_user


def require_store_access(store_id: int):
    """Factory that returns a dependency checking user has access to specific store"""
    def check_store_access(
        db: Session = Depends(get_db),
        current_user: Users = Depends(get_current_user),
    ) -> Users:
        # Global admin can access any store
        global_admin = db.query(UserRoles).filter(
            UserRoles.user_id == current_user.id,
            UserRoles.role == Role.ADMIN,
            UserRoles.store_id.is_(None)
        ).first()
        if global_admin:
            return current_user
        
        # Check for store-specific role
        store_role = db.query(UserRoles).filter(
            UserRoles.user_id == current_user.id,
            UserRoles.store_id == store_id,
            UserRoles.role.in_([Role.ADMIN, Role.MANAGER])
        ).first()
        
        if not store_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this store")
        
        return current_user
    
    return check_store_access


class StoreAccessChecker:
    """Dependency class for checking store access from path parameter"""
    def __init__(self, allow_employee: bool = False):
        self.allow_employee = allow_employee
    
    def __call__(
        self,
        store_id: int,
        db: Session = Depends(get_db),
        current_user: Users = Depends(get_current_user),
    ) -> Users:
        # Global admin can access any store
        global_admin = db.query(UserRoles).filter(
            UserRoles.user_id == current_user.id,
            UserRoles.role == Role.ADMIN,
            UserRoles.store_id.is_(None)
        ).first()
        if global_admin:
            return current_user
        
        allowed_roles = [Role.ADMIN, Role.MANAGER]
        if self.allow_employee:
            allowed_roles.append(Role.EMPLOYEE)
        
        # Check for store-specific role
        store_role = db.query(UserRoles).filter(
            UserRoles.user_id == current_user.id,
            UserRoles.store_id == store_id,
            UserRoles.role.in_(allowed_roles)
        ).first()
        
        if not store_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this store")
        
        return current_user
    

# Instances of StoreAccessChecker for reuse
require_store_manager = StoreAccessChecker(allow_employee=False)
require_store_member = StoreAccessChecker(allow_employee=True)
