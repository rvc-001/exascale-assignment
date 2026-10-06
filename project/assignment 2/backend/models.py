from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class EmissionFactor(Base):
    __tablename__ = "emission_factors"
    id = Column(Integer, primary_key=True, index=True)
    activity_type = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=False)
    co2e_value = Column(Float, nullable=False)
    source = Column(String(100))
    scope = Column(Integer, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)  # None = currently active


class EmissionRecord(Base):
    __tablename__ = "emission_records"
    id = Column(Integer, primary_key=True, index=True)
    activity_date = Column(Date, nullable=False)
    activity_type = Column(String(100), nullable=False)
    activity_amount = Column(Float, nullable=False)
    factor_id = Column(Integer, ForeignKey("emission_factors.id"))
    calculated_emissions = Column(Float, nullable=False)
    scope = Column(Integer, nullable=False)
    is_overridden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    factor = relationship("EmissionFactor")
    audit_logs = relationship("AuditLog", back_populates="record")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("emission_records.id"))
    field_changed = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    reason = Column(Text)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
    record = relationship("EmissionRecord", back_populates="audit_logs")


class BusinessMetric(Base):
    __tablename__ = "business_metrics"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
