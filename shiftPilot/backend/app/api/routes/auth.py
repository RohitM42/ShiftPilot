from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.models.users import Users
from app.schemas.auth import Token, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Users).filter(Users.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = Users(
        email=payload.email,
        firstname=payload.firstname,
        surname=payload.surname,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=token)