from typing import Optional
from datetime import datetime, time
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Time, func, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RoleRequirements(Base):
    __tablename__ = "role_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # null = entire store
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = every day
    start_time_local: Mapped[time] = mapped_column(Time, nullable=False)
    end_time_local: Mapped[time] = mapped_column(Time, nullable=False)
    requires_manager: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_keyholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_manager_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_modified_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (

        UniqueConstraint(
            'store_id', 'department_id', 'day_of_week', 'start_time_local', 'end_time_local',
            name='uix_role_requirements_unique_timeslot'
        ),
    )