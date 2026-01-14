from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class StoreDepartment(Base):
    __tablename__ = "store_departments"

    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id"), primary_key=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), primary_key=True)

