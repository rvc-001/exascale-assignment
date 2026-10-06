from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date
from database import get_db
from models import EmissionRecord
from emission_engine import calculate_emission

router = APIRouter(prefix="/api/emissions", tags=["Emissions"])

class EmissionCreate(BaseModel):
    activity_date: date
    activity_type: str = Field(..., min_length=1)
    activity_amount: float = Field(..., gt=0)
    # scope is set automatically by the endpoint


@router.post("/scope1", status_code=201)
def create_scope1_emission(payload: EmissionCreate, db: Session = Depends(get_db)):
    """
    Record a Scope 1 (direct) emission.
    Validates that the resolved emission factor is also Scope 1.
    Prevents misuse like posting 'Grid Electricity' to the Scope 1 endpoint.
    """
    try:
        emissions_kgco2e, factor = calculate_emission(
            db, payload.activity_type, payload.activity_date, payload.activity_amount
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ── Scope validation: reject if factor is not Scope 1 ──
    if factor.scope != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Activity type '{payload.activity_type}' is Scope {factor.scope}, "
                   f"not Scope 1. Use /scope{factor.scope} instead."
        )

    record = EmissionRecord(
        activity_date=payload.activity_date,
        activity_type=payload.activity_type,
        activity_amount=payload.activity_amount,
        factor_id=factor.id,
        calculated_emissions=emissions_kgco2e,
        scope=1
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "calculated_emissions_kgco2e": emissions_kgco2e,
        "factor_used": {"id": factor.id, "co2e_value": factor.co2e_value, "source": factor.source}
    }


@router.post("/scope2", status_code=201)
def create_scope2_emission(payload: EmissionCreate, db: Session = Depends(get_db)):
    """Record a Scope 2 (indirect/purchased energy) emission."""
    try:
        emissions_kgco2e, factor = calculate_emission(
            db, payload.activity_type, payload.activity_date, payload.activity_amount
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ── Scope validation: reject if factor is not Scope 2 ──
    if factor.scope != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Activity type '{payload.activity_type}' is Scope {factor.scope}, "
                   f"not Scope 2. Use /scope{factor.scope} instead."
        )

    record = EmissionRecord(
        activity_date=payload.activity_date,
        activity_type=payload.activity_type,
        activity_amount=payload.activity_amount,
        factor_id=factor.id,
        calculated_emissions=emissions_kgco2e,
        scope=2
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "calculated_emissions_kgco2e": emissions_kgco2e}


@router.get("/")
def list_emissions(skip: int = 0, limit: int = 50,
                   scope: int = None, db: Session = Depends(get_db)):
    """List all emission records, optionally filter by scope."""
    query = db.query(EmissionRecord)
    if scope:
        query = query.filter(EmissionRecord.scope == scope)
    return query.offset(skip).limit(limit).all()

class OverridePayload(BaseModel):
    new_emissions_value: float = Field(..., ge=0)
    reason: str = Field(..., min_length=1)
    changed_by: str = Field(..., min_length=1)

@router.patch("/{record_id}/override")
def override_emission(record_id: int, payload: OverridePayload,
                      db: Session = Depends(get_db)):
    """
    Manually override an emission record's calculated value.
    Creates an immutable audit log entry.
    """
    from models import AuditLog

    record = db.query(EmissionRecord).filter(EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Emission record not found")

    # Create audit log BEFORE changing the value
    audit = AuditLog(
        record_id=record.id,
        field_changed="calculated_emissions",
        old_value=str(record.calculated_emissions),
        new_value=str(payload.new_emissions_value),
        reason=payload.reason,
        changed_by=payload.changed_by
    )
    db.add(audit)

    # Apply the override
    record.calculated_emissions = payload.new_emissions_value
    record.is_overridden = True
    db.commit()

    return {
        "message": "Override applied successfully",
        "record_id": record.id,
        "old_value": audit.old_value,
        "new_value": audit.new_value,
        "audit_id": audit.id
    }

@router.get("/audit-log")
def get_audit_log(db: Session = Depends(get_db)):
    """Return the full audit trail of all manual overrides."""
    from models import AuditLog
    return db.query(AuditLog).order_by(AuditLog.changed_at.desc()).all()
