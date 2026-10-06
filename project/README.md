# Exascale Data Developer Intern Assignments

This repository contains two independent, end-to-end prototypes built from the Exascale Deeptech & AI assignment brief.

## Repository Layout

```text
project/
├── README.md
├── TESTING.md
├── .gitignore
├── assignment 1/
│   ├── README.md
│   ├── pipeline.py
│   ├── notebooks/
│   ├── data/
│   ├── models/
│   ├── backend/
│   ├── frontend/
│   └── docker-compose.yml
└── assignment 2/
    ├── README.md
    ├── test_data.json
    ├── backend/
    ├── frontend/
    └── docker-compose.yml
```

## Assignment 1: Intelligent Power Demand Forecasting

Builds a forecasting system for Apex Power & Utilities in Dhanbad, Jharkhand. The solution cleans 10-minute feeder load data, aggregates it into 30-minute blocks, enriches it with Open-Meteo weather and localized Jharkhand/Dhanbad holiday features, trains candidate models, and serves a 24-hour forecast through FastAPI.

Key deliverables:

- EDA and model justification notebook.
- Cleaned 30-minute load dataset.
- Weather and local holiday datasets.
- Random Forest model artifact and feature list.
- Backend API with forecast, weather, holidays, and health endpoints.
- Single-page frontend dashboard using Chart.js.
- Dockerfiles and Docker Compose setup.

Open `assignment 1/README.md` for the full run instructions and API details.

## Assignment 2: Carbon Emissions Reporting Platform

Builds a GHG Protocol reporting prototype focused on Scope 1 and Scope 2 emissions. The platform uses versioned emission factors, stores business metrics, creates emission records, supports manual override auditing, and exposes advanced analytics endpoints for ESG visualizations.

Key deliverables:

- Versioned emission factor schema.
- Historical accuracy calculation engine.
- Scope 1 and Scope 2 record creation APIs.
- Manual override API with immutable audit log.
- YoY, intensity, hotspot, and monthly trend analytics APIs.
- Single-page frontend dashboard with multiple ESG charts.
- Dockerfiles and Docker Compose setup with PostgreSQL.
- Backend unit tests for historical factor selection and audit behavior.

Open `assignment 2/README.md` for the full run instructions and API details.

## Running Both Assignments

Run each assignment separately because both expose frontend port `3000` and backend port `8000`.

```bash
cd "assignment 1"
docker compose up --build
```

```bash
cd "assignment 2"
docker compose up --build
```

## Notes

- Python virtual environments are intentionally not committed. Recreate them from each backend `requirements.txt`.
- Runtime caches, local databases, and secrets are intentionally ignored.
- Assignment 2 seeds its database automatically from `backend/GHG_Sheet.xlsx`.
