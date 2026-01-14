from sqlalchemy import Integer, DateTime, Boolean, func, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from enum import Enum
from app.db.database import Base

class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LEAVER = "LEAVER"
    ON_LEAVE = "ON_LEAVE"

class Employees(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    is_keyholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_manager: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(SQLEnum(EmploymentStatus, name="employment_status_enum", native_enum=True), nullable=False)
    contracted_weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    dob: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
