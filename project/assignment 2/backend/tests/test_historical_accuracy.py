from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from emission_engine import calculate_emission
from models import Base, AuditLog, EmissionFactor, EmissionRecord


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_calculate_emission_uses_factor_valid_on_activity_date():
    db = make_db()
    db.add_all([
        EmissionFactor(
            activity_type="Diesel Combustion",
            unit="Litre",
            co2e_value=2.50,
            source="Historical factor",
            scope=1,
            valid_from=date(2020, 1, 1),
            valid_to=date(2022, 12, 31),
        ),
        EmissionFactor(
            activity_type="Diesel Combustion",
            unit="Litre",
            co2e_value=2.68,
            source="Current factor",
            scope=1,
            valid_from=date(2023, 1, 1),
            valid_to=None,
        ),
    ])
    db.commit()

    old_emissions, old_factor = calculate_emission(db, "Diesel Combustion", date(2022, 6, 1), 100)
    new_emissions, new_factor = calculate_emission(db, "Diesel Combustion", date(2024, 6, 1), 100)

    assert old_emissions == 250.0
    assert old_factor.source == "Historical factor"
    assert new_emissions == 268.0
    assert new_factor.source == "Current factor"


def test_override_can_be_audited_at_database_level():
    db = make_db()
    factor = EmissionFactor(
        activity_type="Grid Electricity",
        unit="kWh",
        co2e_value=0.8,
        source="CEA",
        scope=2,
        valid_from=date(2023, 1, 1),
        valid_to=None,
    )
    db.add(factor)
    db.flush()
    record = EmissionRecord(
        activity_date=date(2024, 1, 15),
        activity_type="Grid Electricity",
        activity_amount=1000,
        factor_id=factor.id,
        calculated_emissions=800,
        scope=2,
    )
    db.add(record)
    db.flush()

    db.add(AuditLog(
        record_id=record.id,
        field_changed="calculated_emissions",
        old_value="800",
        new_value="775",
        reason="Corrected meter reading",
        changed_by="tester",
    ))
    record.calculated_emissions = 775
    record.is_overridden = True
    db.commit()

    audit = db.query(AuditLog).one()
    assert record.is_overridden is True
    assert audit.old_value == "800"
    assert audit.new_value == "775"
