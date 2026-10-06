# Assignment 2: Carbon Emissions Reporting Platform

This project implements a GHG Protocol-based emissions reporting platform focused on Scope 1 and Scope 2 emissions. It provides emission record creation, historical factor accuracy, manual override auditing, business metrics, advanced analytics APIs, and an ESG dashboard.

## What This Solves

The assignment asks for a functional data application that differentiates GHG scopes, calculates emissions from activity data and emission factors, supports historical accuracy, and powers advanced reporting visualizations. This implementation provides:

- Versioned emission factor master data.
- Scope 1 and Scope 2 emission record creation.
- Historical factor lookup based on activity date.
- Manual override flow with audit log.
- Business metrics for intensity reporting.
- Year-over-year, intensity, hotspot, and monthly trend APIs.
- Dashboard with stacked bar, donut, KPI, and line chart visualizations.
- Dockerized frontend, backend, and PostgreSQL database.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Uvicorn |
| ORM | SQLAlchemy |
| Database | PostgreSQL in Docker, SQLite fallback for local development |
| Data seeding | Pandas reading `GHG_Sheet.xlsx` |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Deployment | Docker, Docker Compose, Nginx |
| Tests | Pytest |

## Architecture

```text
User Browser
    |
    v
Frontend (Nginx, HTML/CSS/JS, Chart.js)
    |
    | /api proxy
    v
Backend API (FastAPI)
    |
    | SQLAlchemy
    v
PostgreSQL / SQLite
```

## Folder Structure

```text
assignment 2/
├── README.md
├── docker-compose.yml
├── test_data.json
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── emission_engine.py
│   ├── seed.py
│   ├── GHG_Sheet.xlsx
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   ├── analytics.py
│   │   ├── emissions.py
│   │   └── metrics.py
│   └── tests/
│       └── test_historical_accuracy.py
└── frontend/
    ├── index.html
    ├── style.css
    ├── app.js
    ├── nginx.conf
    └── Dockerfile
```

## Data Model

| Table | Purpose |
| --- | --- |
| `emission_factors` | Versioned master data for activity type, unit, CO2e value, source, scope, and validity dates. |
| `emission_records` | Stores user activity data, the factor used, calculated emissions, scope, and override status. |
| `audit_log` | Stores manual override history with old value, new value, reason, user, and timestamp. |
| `business_metrics` | Stores production or business KPI values used for intensity calculations. |

## Historical Accuracy Logic

The core calculation engine selects the emission factor that was valid on the activity date:

```python
valid_from <= activity_date
and (valid_to >= activity_date or valid_to is null)
```

This prevents older records from being recalculated using the newest factor. Seed data creates expired 2020-2022 factors and current 2023+ factors for every activity type.

## Docker Run

From this folder:

```bash
docker compose up --build
```

Then open:

- Dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

The backend automatically creates tables and seeds the database from `backend/GHG_Sheet.xlsx` during startup when the database is empty.

## Local Backend Run

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Without `DATABASE_URL`, the backend uses a local SQLite database file for development. That file is intentionally ignored and not committed.

## API Reference

### Core Emissions

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/emissions/scope1` | POST | Create a Scope 1 emission record. |
| `/api/emissions/scope2` | POST | Create a Scope 2 emission record. |
| `/api/emissions/` | GET | List emission records, optionally filtered by scope. |
| `/api/emissions/{record_id}/override` | PATCH | Override calculated emissions and create an audit record. |
| `/api/emissions/audit-log` | GET | Return all audit log entries. |

### Analytics

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/analytics/yoy?year=2024` | GET | Current and previous year emissions totals by scope. |
| `/api/analytics/intensity?metric=Tons%20of%20Steel%20Produced&year=2024` | GET | Emissions per business metric unit. |
| `/api/analytics/hotspot?year=2024` | GET | Ranked emissions by source/activity type. |
| `/api/analytics/monthly?year=2024` | GET | Monthly emissions trend for the year. |

### Business Metrics

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/metrics/` | POST | Create a business metric. |
| `/api/metrics/` | GET | List business metrics. |

## Sample Requests

Create a historical Scope 1 record:

```bash
curl -X POST http://localhost:8000/api/emissions/scope1 \
  -H "Content-Type: application/json" \
  -d "{\"activity_date\":\"2022-06-15\",\"activity_type\":\"Anthracite Coal\",\"activity_amount\":10}"
```

Apply a manual override:

```bash
curl -X PATCH http://localhost:8000/api/emissions/1/override \
  -H "Content-Type: application/json" \
  -d "{\"new_emissions_value\":12345,\"reason\":\"Corrected meter reading\",\"changed_by\":\"tester\"}"
```

Check analytics:

```bash
curl "http://localhost:8000/api/analytics/yoy?year=2024"
curl "http://localhost:8000/api/analytics/intensity?metric=Tons%20of%20Steel%20Produced&year=2024"
curl "http://localhost:8000/api/analytics/hotspot?year=2024"
curl "http://localhost:8000/api/analytics/monthly?year=2024"
```

## Frontend Dashboard

The dashboard includes:

- Scope 1 and Scope 2 emission submission form.
- Business metric submission form.
- Year-over-year stacked bar chart.
- Emission hotspot donut chart.
- Emission intensity KPI card.
- Monthly emissions trend line chart.

## Tests

From `backend/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest
```

The tests verify:

- Historical factor lookup uses the factor valid on the activity date.
- Override behavior can be represented with an audit log record.

## Assignment Coverage

| Requirement | Status |
| --- | --- |
| Architecture and schema documentation | Complete |
| Versioned emission factors | Complete |
| Business metrics | Complete |
| Historical accuracy engine | Complete |
| Scope 1 and Scope 2 create APIs | Complete |
| Manual override with audit log | Complete |
| YoY emissions API | Complete |
| Emission intensity API | Complete |
| Emission hotspot API | Complete |
| Monthly trend API | Complete |
| Frontend submission forms | Complete |
| Three or more ESG visualizations | Complete, four included |
| Docker packaging | Complete |
