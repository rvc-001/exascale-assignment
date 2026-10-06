from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models import EmissionFactor, EmissionRecord

def get_valid_factor(db: Session, activity_type: str, activity_date: date) -> EmissionFactor:
    """
    Returns the EmissionFactor that was valid on the given activity_date.
    Selects where:
      - activity_type matches
      - valid_from <= activity_date
      - valid_to >= activity_date OR valid_to is NULL (still active)
    """
    factor = db.query(EmissionFactor).filter(
        EmissionFactor.activity_type == activity_type,
        EmissionFactor.valid_from <= activity_date,
        or_(
            EmissionFactor.valid_to >= activity_date,
            EmissionFactor.valid_to.is_(None)
        )
    ).order_by(EmissionFactor.valid_from.desc()).first()

    if not factor:
        raise ValueError(
            f"No valid emission factor found for '{activity_type}' on {activity_date}"
        )
    return factor


def calculate_emission(db: Session, activity_type: str,
                       activity_date: date, amount: float) -> tuple:
    """
    Calculates GHG emissions using the historically correct factor.
    Returns: (calculated_kgco2e: float, factor: EmissionFactor)
    """
    factor = get_valid_factor(db, activity_type, activity_date)
    emissions = amount * factor.co2e_value
    return emissions, factor
