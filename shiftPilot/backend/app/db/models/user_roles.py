from sqlalchemy import Integer, DateTime, func, UniqueConstraint, ForeignKey, Enum as SQLEnum
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum
from app.db.database import Base

class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

class UserRoles(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    role: Mapped[Role] = mapped_column(SQLEnum(Role, name="role_enum", native_enum=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'store_id', 'role'),
    )