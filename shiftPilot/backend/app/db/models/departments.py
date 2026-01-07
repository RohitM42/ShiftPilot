from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Departments(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100),nullable=False,unique=True)
    code: Mapped[str] = mapped_column(String(20),nullable=False,unique=True)
    has_manager_role: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")