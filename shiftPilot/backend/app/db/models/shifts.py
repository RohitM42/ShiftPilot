from sqlalchemy import Integer, DateTime, ForeignKey, Enum as SQLEnum, Index, func
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum
from typing import Optional
from app.db.database import Base


class ShiftStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class ShiftSource(str, Enum):
    MANUAL = "MANUAL"
    AI = "AI"
    IMPORT = "IMPORT"


class Shifts(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    start_datetime_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ShiftStatus] = mapped_column(SQLEnum(ShiftStatus, name="shift_status_enum"), nullable=False)
    source: Mapped[ShiftSource] = mapped_column(SQLEnum(ShiftSource, name="shift_source_enum"), nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_shifts_store_start", "store_id", "start_datetime_utc"),
        Index("ix_shifts_employee_start", "employee_id", "start_datetime_utc"),
    )
