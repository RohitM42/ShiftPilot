from typing import Optional
from enum import Enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, func, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TimeOffStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class TimeOffReason(str, Enum):
    SICK_LEAVE = "SICK_LEAVE"
    HOLIDAY = "HOLIDAY"
    UNPAID = "UNPAID"
    OTHER = "OTHER"


class TimeOffRequests(Base):
    __tablename__ = "time_off_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TimeOffStatus] = mapped_column(SQLEnum(TimeOffStatus, name="time_off_request_status_enum"), nullable=False)
    reason_type: Mapped[TimeOffReason] = mapped_column(SQLEnum(TimeOffReason, name="time_off_request_reason_type_enum"), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_modified_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)