import os
import pandas as pd
from datetime import date
from database import SessionLocal, engine
from models import Base, EmissionFactor, EmissionRecord, BusinessMetric


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(EmissionFactor).count() > 0:
        print("Database already seeded - skipping.")
        db.close()
        return

    print("Seeding database from Excel file...")

    excel_path = os.path.join(os.path.dirname(__file__), "GHG_Sheet.xlsx")
    if not os.path.exists(excel_path):
        print(f"Error: {excel_path} not found.")
        db.close()
        return

    xl = pd.ExcelFile(excel_path)
    factors = {}
    records = []

    def add_factor_versions(activity_type, unit, co2e_value, source, scope):
        """Create expired and current versions for historical accuracy checks."""
        if activity_type in factors:
            return factors[activity_type]

        old_factor = EmissionFactor(
            activity_type=activity_type,
            unit=unit,
            co2e_value=round(co2e_value * 0.94, 6),
            source=f"{source} - historical 2020-2022",
            scope=scope,
            valid_from=date(2020, 1, 1),
            valid_to=date(2022, 12, 31),
        )
        current_factor = EmissionFactor(
            activity_type=activity_type,
            unit=unit,
            co2e_value=round(co2e_value, 6),
            source=f"{source} - current 2023+",
            scope=scope,
            valid_from=date(2023, 1, 1),
            valid_to=None,
        )
        db.add_all([old_factor, current_factor])
        db.flush()
        factors[activity_type] = {"old": old_factor, "current": current_factor}
        return factors[activity_type]

    def add_monthly_records(activity_type, scope, annual_amount):
        versions = factors[activity_type]
        for year, scale, factor_key in [(2022, 0.88, "old"), (2023, 0.94, "current"), (2024, 1.0, "current")]:
            for month in range(1, 13):
                factor = versions[factor_key]
                seasonal = 1 + ((month % 4) - 1.5) * 0.025
                amount = max((annual_amount / 12) * scale * seasonal, 0)
                records.append(EmissionRecord(
                    activity_date=date(year, month, 15),
                    activity_type=activity_type,
                    activity_amount=round(amount, 4),
                    factor_id=factor.id,
                    calculated_emissions=round(amount * factor.co2e_value, 4),
                    scope=scope,
                ))

    if "Scope 1" in xl.sheet_names:
        df1 = xl.parse("Scope 1")
        for _, row in df1.iterrows():
            if pd.isna(row.get("Material")):
                continue

            activity_type = str(row["Material"]).strip()
            unit = str(row["Unit of Material"]).strip()
            co2e_value = float(row["Emission Factor"]) * 1000
            source = str(row.get("Data Source for Emission Factor", "Unknown")).strip()
            add_factor_versions(activity_type, unit, co2e_value, source, scope=1)

            amount = float(row.get("Q1 Quantity", 0) or 0)
            if amount > 0:
                add_monthly_records(activity_type, scope=1, annual_amount=amount)

    if "Scope 2" in xl.sheet_names:
        df2 = xl.parse("Scope 2")
        for _, row in df2.iterrows():
            if pd.isna(row.get("Energy Type")):
                continue

            activity_type = str(row["Energy Type"]).strip() + " - " + str(row.get("Supplier/Source", "")).strip()
            unit = str(row.get("Unit", "kWh")).strip()
            ef_col = [c for c in df2.columns if "Emission Factor" in c][0]
            if "kwh" in unit.lower():
                co2e_value = float(row[ef_col])
            else:
                co2e_value = float(row[ef_col]) * 1000

            source_cols = [c for c in df2.columns if "Source" in c and "Grid" in c]
            source = str(row[source_cols[0]]).strip() if source_cols else "Unknown"
            add_factor_versions(activity_type, unit, co2e_value, source, scope=2)

            amount = float(row.get("Energy Consumed", 0) or 0)
            if amount > 0:
                add_monthly_records(activity_type, scope=2, annual_amount=amount)

    db.add_all(records)

    metrics = []
    for year in range(2021, 2027):
        for month in range(1, 13):
            metric_date = date(year, month, 28)
            if metric_date > date.today():
                continue

            metrics.append(BusinessMetric(
                date=metric_date,
                metric_name="Tons of Steel Produced",
                value=40000 + (year - 2023) * 5000 + month * 400,
            ))
            metrics.append(BusinessMetric(
                date=metric_date,
                metric_name="Number of Employees",
                value=1200,
            ))
    db.add_all(metrics)

    db.commit()
    db.close()
    print(
        f"Successfully seeded {len(records)} emission records, "
        f"{sum(len(v) for v in factors.values())} versioned factors, and {len(metrics)} metrics."
    )


if __name__ == "__main__":
    seed_database()
