from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional


from app.db.database import Base


class AIInputs(Base):
    __tablename__ = "ai_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    req_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_tables: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())