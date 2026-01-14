from typing import Optional
from datetime import datetime, date
from sqlalchemy import Date, DateTime, Numeric, Integer, ForeignKeyConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class LabourBudgets(Base):
    __tablename__ = "labour_budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(['store_id', 'department_id'], ['store_departments.store_id', 'store_departments.department_id']),
        UniqueConstraint('store_id', 'department_id', 'week_start_date', name='uix_labour_budgets_unique_week'),
    )