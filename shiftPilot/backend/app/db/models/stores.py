from sqlalchemy import Column, Integer, String, DateTime, Time, func
from datetime import datetime, time
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Stores(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    opening_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(7, 0))
    closing_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(22, 0))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)