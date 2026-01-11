from typing import Optional
from enum import Enum
from datetime import datetime, time
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AvailabilityRuleType(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PREFERRED = "PREFERRED"


class AvailabilityRules(Base):
    __tablename__ = "availability_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–6
    start_time_local: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time_local: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    rule_type: Mapped[AvailabilityRuleType] = mapped_column(SQLEnum(AvailabilityRuleType, name="availability_rule_type_enum"),nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True),nullable=True,server_default=func.now(),onupdate=func.now())
