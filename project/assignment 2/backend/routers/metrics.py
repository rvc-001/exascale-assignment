from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from database import get_db
from models import BusinessMetric

router = APIRouter(prefix="/api/metrics", tags=["Business Metrics"])

class MetricCreate(BaseModel):
    date: date
    metric_name: str
    value: float

@router.post("/", status_code=201)
def create_metric(payload: MetricCreate, db: Session = Depends(get_db)):
    # .dict() is deprecated in Pydantic v2 — use .model_dump() instead
    metric = BusinessMetric(**payload.model_dump())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric

@router.get("/")
def list_metrics(db: Session = Depends(get_db)):
    return db.query(BusinessMetric).order_by(BusinessMetric.date.desc()).all()
