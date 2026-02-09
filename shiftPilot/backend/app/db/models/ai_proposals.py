from typing import Optional
from enum import Enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ProposalType(str, Enum):
    AVAILABILITY = "AVAILABILITY"
    COVERAGE = "COVERAGE"
    ROLE_REQUIREMENT = "ROLE_REQUIREMENT"
    LABOUR_BUDGET = "LABOUR_BUDGET"


class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AIProposals(Base):
    __tablename__ = "ai_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ai_output_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_outputs.id"), nullable=False, index=True)
    type: Mapped[ProposalType] = mapped_column(SQLEnum(ProposalType, name="proposal_type_enum"), nullable=False)
    store_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("stores.id"), nullable=True, index=True) # null = all stores but if ProposalType = availability, then null = null
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True, index=True) # null = all deps but if ProposalType = availability, then null = null
    status: Mapped[ProposalStatus] = mapped_column(SQLEnum(ProposalStatus, name="proposal_status_enum"), nullable=False, default=ProposalStatus.PENDING, index=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_actioned_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())