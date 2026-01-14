from typing import Optional
from enum import Enum
from datetime import datetime, time
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Time, func, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base




class CoverageRequirements(Base):
    __tablename__ = "coverage_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–6
    start_time_local: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time_local: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    min_staff: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_staff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) #no formal maximums in place at the moment
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_modified_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(['store_id', 'department_id'], ['store_departments.store_id', 'store_departments.department_id']),
        UniqueConstraint('store_id', 'department_id', 'day_of_week', 'start_time_local', 'end_time_local', name='uix_coverage_requirements_unique_timeslot')
    )