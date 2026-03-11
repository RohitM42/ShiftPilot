from datetime import datetime, timedelta, time as time_min
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    require_manager_or_admin,
    check_store_access,
    get_accessible_store_ids,
)
from app.db.models.shifts import Shifts, ShiftStatus, ShiftSource
from app.db.models.users import Users
from app.schemas.schedule import (
    GenerateScheduleRequest,
    GenerateScheduleResponse,
    UnmetCoverageItem,
    UnmetRoleItem,
    PublishBulkRequest,
    PublishBulkResponse,
)
from app.services.scheduling.generator import generate_schedule

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/generate", response_model=GenerateScheduleResponse, status_code=201)
def generate_schedule_endpoint(
    payload: GenerateScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    if not check_store_access(db, current_user, payload.store_id):
        raise HTTPException(status_code=403, detail="No access to this store")

    if payload.mode == "replace":
        week_start_dt = datetime.combine(payload.week_start, time_min.min)
        week_end_dt = datetime.combine(
            payload.week_start + timedelta(days=7), time_min.min
        )
        existing = (
            db.query(Shifts)
            .filter(
                Shifts.store_id == payload.store_id,
                Shifts.status != ShiftStatus.CANCELLED,
                Shifts.start_datetime_utc >= week_start_dt,
                Shifts.start_datetime_utc < week_end_dt,
            )
            .all()
        )
        for s in existing:
            s.status = ShiftStatus.CANCELLED
        # cancellations staged but not committed — committed together with new shifts below

    try:
        result = generate_schedule(db, payload.store_id, payload.week_start)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    shift_ids: list[int] = []
    for s in result.shifts:
        shift = Shifts(
            store_id=s.store_id,
            department_id=s.department_id,
            employee_id=s.employee_id,
            start_datetime_utc=s.start_datetime,
            end_datetime_utc=s.end_datetime,
            status=ShiftStatus.DRAFT,
            source=ShiftSource.AI,
            created_by_user_id=current_user.id,
        )
        db.add(shift)
        db.flush()
        shift_ids.append(shift.id)
    db.commit()

    return GenerateScheduleResponse(
        success=result.success,
        shifts_created=len(shift_ids),
        shift_ids=shift_ids,
        unmet_coverage=[
            UnmetCoverageItem(
                department_id=u.department_id,
                day_of_week=u.day_of_week,
                start_time=str(u.start_time),
                end_time=str(u.end_time),
                min_staff=u.min_staff,
            )
            for u in result.unmet_coverage
        ],
        unmet_role_requirements=[
            UnmetRoleItem(
                department_id=u.department_id,
                day_of_week=u.day_of_week,
                start_time=str(u.start_time),
                end_time=str(u.end_time),
                requires_keyholder=u.requires_keyholder,
                requires_manager=u.requires_manager,
                min_manager_count=u.min_manager_count,
            )
            for u in result.unmet_role_requirements
        ],
        unmet_contracted_hours={
            str(emp_id): shortfall
            for emp_id, shortfall in result.unmet_contracted_hours.items()
        },
        warnings=result.warnings,
    )


@router.post("/publish-bulk", response_model=PublishBulkResponse)
def publish_bulk(
    payload: PublishBulkRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_manager_or_admin),
):
    accessible_stores = get_accessible_store_ids(db, current_user)
    shifts = db.query(Shifts).filter(Shifts.id.in_(payload.shift_ids)).all()

    if len(shifts) != len(set(payload.shift_ids)):
        found_ids = {s.id for s in shifts}
        missing = [sid for sid in payload.shift_ids if sid not in found_ids]
        raise HTTPException(status_code=404, detail=f"Shifts not found: {missing}")

    for shift in shifts:
        if accessible_stores is not None and shift.store_id not in accessible_stores:
            raise HTTPException(
                status_code=403, detail=f"No access to shift {shift.id}"
            )
        if shift.status != ShiftStatus.DRAFT:
            raise HTTPException(
                status_code=409, detail=f"Shift {shift.id} is not in DRAFT status (current: {shift.status.value})"
            )
        shift.status = ShiftStatus.PUBLISHED

    db.commit()
    return PublishBulkResponse(published_count=len(shifts))
