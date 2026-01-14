from sqlalchemy import Integer, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class EmployeeDepartments(Base):
    __tablename__ = "employee_departments"

    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        PrimaryKeyConstraint("employee_id", "department_id"),
    )
