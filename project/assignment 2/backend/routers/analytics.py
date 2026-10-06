from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from database import get_db
from models import EmissionRecord, BusinessMetric

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/yoy")
def year_over_year(year: int = 2024, db: Session = Depends(get_db)):
    from datetime import date
    is_current_year = (year == date.today().year)
    cutoff = date.today()

    def get_year_data(y: int, apply_cutoff: bool = False):
        query = db.query(
            EmissionRecord.scope,
            func.sum(EmissionRecord.calculated_emissions).label("total")
        ).filter(
            extract('year', EmissionRecord.activity_date) == y
        )
        
        if apply_cutoff:
            try:
                # Handle leap years safely
                cutoff_date = date(y, cutoff.month, cutoff.day)
            except ValueError:
                cutoff_date = date(y, cutoff.month, cutoff.day - 1)
            query = query.filter(EmissionRecord.activity_date <= cutoff_date)

        result = query.group_by(EmissionRecord.scope).all()

        scopes = {row.scope: row.total for row in result}
        return {
            "scope1_kgco2e": scopes.get(1, 0.0),
            "scope2_kgco2e": scopes.get(2, 0.0),
            "total_kgco2e": sum(scopes.values())
        }

    current = get_year_data(year, apply_cutoff=False)
    previous = get_year_data(year - 1, apply_cutoff=is_current_year)

    change = None
    if previous["total_kgco2e"] > 0:
        change = ((current["total_kgco2e"] - previous["total_kgco2e"])
                  / previous["total_kgco2e"]) * 100
        change = round(change, 2)

    return {
        "year": year,
        "current_year": current,
        "previous_year": previous,
        "change_percent": change
    }

@router.get("/intensity")
def emission_intensity(metric: str = "Tons of Steel Produced",
                       year: int = 2024,
                       db: Session = Depends(get_db)):
    # Total emissions for the year
    total_emissions = db.query(
        func.sum(EmissionRecord.calculated_emissions)
    ).filter(
        extract('year', EmissionRecord.activity_date) == year
    ).scalar() or 0.0

    # Total production metric for the year
    total_metric = db.query(
        func.sum(BusinessMetric.value)
    ).filter(
        extract('year', BusinessMetric.date) == year,
        BusinessMetric.metric_name == metric
    ).scalar() or 0.0

    intensity = round(total_emissions / total_metric, 4) if total_metric > 0 else None

    from datetime import date
    display_metric = f"{metric} (YTD)" if year == date.today().year else metric

    return {
        "year": year,
        "metric_name": display_metric,
        "total_emissions_kgco2e": total_emissions,
        "total_metric_value": total_metric,
        "intensity": intensity,
        "unit": f"kgCO2e per {metric}"
    }

@router.get("/hotspot")
def emission_hotspot(year: int = 2024, db: Session = Depends(get_db)):
    results = db.query(
        EmissionRecord.activity_type,
        EmissionRecord.scope,
        func.sum(EmissionRecord.calculated_emissions).label("total")
    ).filter(
        extract('year', EmissionRecord.activity_date) == year
    ).group_by(
        EmissionRecord.activity_type, EmissionRecord.scope
    ).order_by(func.sum(EmissionRecord.calculated_emissions).desc()).all()

    total = sum(r.total for r in results)
    hotspots = [
        {
            "source": r.activity_type,
            "scope": r.scope,
            "emissions_kgco2e": round(r.total, 2),
            "percentage": round((r.total / total) * 100, 2) if total > 0 else 0
        }
        for r in results
    ]

    return {"year": year, "hotspots": hotspots, "total_kgco2e": round(total, 2)}

@router.get("/monthly")
def monthly_trend(year: int = 2024, db: Session = Depends(get_db)):
    results = db.query(
        extract('month', EmissionRecord.activity_date).label("month"),
        func.sum(EmissionRecord.calculated_emissions).label("total")
    ).filter(
        extract('year', EmissionRecord.activity_date) == year
    ).group_by("month").order_by("month").all()

    months = ['Jan','Feb','Mar','Apr','May','Jun',
              'Jul','Aug','Sep','Oct','Nov','Dec']

    data = {int(r.month): round(r.total, 2) for r in results}
    return {
        "year": year,
        "monthly": [
            {"month": months[m-1], "emissions_kgco2e": data.get(m, 0.0)}
            for m in range(1, 13)
        ]
    }
