from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models.time_off_requests import TimeOffRequests, TimeOffStatus
from app.db.models.employees import Employees
from app.db.models.users import Users
from app.schemas.time_off_requests import TimeOffRequestCreate, TimeOffRequestUpdate, TimeOffRequestResponse

router = APIRouter(prefix="/time-off-requests", tags=["time-off-requests"])


@router.post("", response_model=TimeOffRequestResponse, status_code=status.HTTP_201_CREATED)
def create_time_off_request(
    payload: TimeOffRequestCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    employee = db.query(Employees).filter(Employees.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    request = TimeOffRequests(**payload.model_dump(), status=TimeOffStatus.PENDING)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("", response_model=List[TimeOffRequestResponse])
def list_time_off_requests(
    employee_id: Optional[int] = None,
    status: Optional[TimeOffStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    query = db.query(TimeOffRequests)
    if employee_id:
        query = query.filter(TimeOffRequests.employee_id == employee_id)
    if status:
        query = query.filter(TimeOffRequests.status == status)

    return query.offset(skip).limit(limit).all()


@router.get("/{request_id}", response_model=TimeOffRequestResponse)
def get_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")
    return request


@router.put("/{request_id}", response_model=TimeOffRequestResponse)
def update_time_off_request(
    request_id: int,
    payload: TimeOffRequestUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    update_data = payload.model_dump(exclude_unset=True)
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
    request = db.query(TimeOffRequests).filter(TimeOffRequests.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    db.delete(request)
    db.commit()