from typing import Optional
from enum import Enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AIOutputStatus(str, Enum):
    COMPLETE = "COMPLETE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INVALID = "INVALID"


class AIOutputs(Base):
    __tablename__ = "ai_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_inputs.id"), nullable=False, index=True)
    affects_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[AIOutputStatus] = mapped_column(SQLEnum(AIOutputStatus, name="ai_output_status_enum"), nullable=False, index=True, default=AIOutputStatus.COMPLETE)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())