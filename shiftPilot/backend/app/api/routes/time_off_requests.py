from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, is_manager_or_admin, get_employee_for_user
from app.db.models.time_off_requests import TimeOffRequests, TimeOffStatus
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.db.models.user_roles import UserRoles, Role
from app.schemas.time_off_requests import TimeOffRequestCreate, TimeOffRequestUpdate, TimeOffRequestResponse

router = APIRouter(prefix="/time-off-requests", tags=["time-off-requests"])


@router.post("", response_model=TimeOffRequestResponse, status_code=status.HTTP_201_CREATED)
def create_time_off_request(
    payload: TimeOffRequestCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create time off request - employees can create for themselves, managers/admins can create for anyone"""
    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check permission: must be own request OR manager/admin
    current_employee = get_employee_for_user(db, current_user)
    is_own_request = current_employee and current_employee.id == payload.employee_id

    if not is_own_request and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Can only create time off requests for yourself")

    request = TimeOffRequests(**payload.model_dump(), status=TimeOffStatus.PENDING)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("", response_model=List[TimeOffRequestResponse])
def list_time_off_requests(
    employee_id: Optional[int] = None,
    request_status: Optional[TimeOffStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """List time off requests - managers/admins see all, employees see only their own"""
    query = db.query(TimeOffRequests)

    # If not manager/admin, restrict to own requests only
    if not is_manager_or_admin(db, current_user):
        current_employee = get_employee_for_user(db, current_user)
        if not current_employee:
            return []  # No employee record = no requests
        query = query.filter(TimeOffRequests.employee_id == current_employee.id)
    elif employee_id:
        # Manager/admin filtering by specific employee
        query = query.filter(TimeOffRequests.employee_id == employee_id)

    if request_status:
        query = query.filter(TimeOffRequests.status == request_status)

    return query.order_by(TimeOffRequests.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{request_id}", response_model=TimeOffRequestResponse)
def get_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get single time off request - own request OR manager/admin"""
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    # Check permission
    current_employee = get_employee_for_user(db, current_user)
    is_own_request = current_employee and current_employee.id == request.employee_id

    if not is_own_request and not is_manager_or_admin(db, current_user):
        raise HTTPException(status_code=403, detail="No access to this request")

    return request


@router.put("/{request_id}", response_model=TimeOffRequestResponse)
def update_time_off_request(
    request_id: int,
    payload: TimeOffRequestUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Update time off request:
    - Employees can update dates/reason/comments on their own PENDING requests
    - Only managers/admins can change status (approve/reject)
    """
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    current_employee = get_employee_for_user(db, current_user)
    is_own_request = current_employee and current_employee.id == request.employee_id
    user_is_manager_or_admin = is_manager_or_admin(db, current_user)

    update_data = payload.model_dump(exclude_unset=True)

    # Check if trying to change status
    if "status" in update_data:
        if not user_is_manager_or_admin:
            raise HTTPException(status_code=403, detail="Only managers/admins can approve or reject requests")

    # For non-status updates, check ownership or manager/admin
    if not is_own_request and not user_is_manager_or_admin:
        raise HTTPException(status_code=403, detail="No access to modify this request")

    # Employees can only modify PENDING requests
    if is_own_request and not user_is_manager_or_admin:
        if request.status != TimeOffStatus.PENDING:
            raise HTTPException(status_code=400, detail="Can only modify pending requests")

    for field, value in update_data.items():
        setattr(request, field, value)

    request.last_modified_by_user_id = current_user.id
    db.commit()
    db.refresh(request)
    return request


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Delete time off request - own PENDING request OR admin only"""
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    current_employee = get_employee_for_user(db, current_user)
    is_own_request = current_employee and current_employee.id == request.employee_id

    # Check for admin role specifically (not just manager)
    is_admin = db.query(UserRoles).filter(
        UserRoles.user_id == current_user.id,
        UserRoles.role == Role.ADMIN
    ).first() is not None

    if is_admin:
        # Admin can delete any request
        pass
    elif is_own_request:
        # Employee can only delete their own PENDING requests
        if request.status != TimeOffStatus.PENDING:
            raise HTTPException(status_code=400, detail="Can only delete pending requests")
    else:
        raise HTTPException(status_code=403, detail="No access to delete this request")

    db.delete(request)
    db.commit()