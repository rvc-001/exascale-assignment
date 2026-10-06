# Assignment 1: Intelligent Power Demand Forecasting

## Live Deployment

- **Frontend Dashboard:** [https://exascale-assignment-frontend.vercel.app/](https://exascale-assignment-frontend.vercel.app/)
- **Backend API Base URL:** [https://exascale-assignment.onrender.com](https://exascale-assignment.onrender.com)
  - **Interactive API Docs (Swagger):** [https://exascale-assignment.onrender.com/docs](https://exascale-assignment.onrender.com/docs)

---

This project implements an end-to-end power demand forecasting prototype for Apex Power & Utilities in Dhanbad, Jharkhand. It converts the provided 10-minute feeder consumption data into 30-minute demand blocks, enriches the data with weather and localized holiday signals, trains a forecasting model, and serves the result through a web dashboard.

## What This Solves

The assignment asks for a deployable prototype that predicts electricity demand for every 30-minute block over the next 24 hours. This implementation provides:

- Load data cleaning for gaps, errors, and outliers.
- Resampling from 10-minute readings to 30-minute blocks.
- Weather integration for Dhanbad using Open-Meteo.
- Local holiday features for Jharkhand and Dhanbad-specific events.
- Candidate model comparison and final model selection.
- FastAPI backend for forecasts and supporting metadata.
- Single-page dashboard with Chart.js visualization.
- Dockerized backend and frontend services.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Data processing | Python, Pandas, NumPy |
| Modeling | Scikit-learn RandomForestRegressor, LinearRegression, DummyRegressor |
| Notebook | Jupyter Notebook |
| Backend | FastAPI, Uvicorn |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Deployment | Docker, Docker Compose, Nginx |

## Folder Structure

```text
assignment 1/
├── README.md
├── pipeline.py
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── favicon.jpg
│   ├── nginx.conf
│   └── Dockerfile
├── data/
│   ├── raw/
│   │   ├── Utility_consumption.csv
│   │   ├── weather_data.csv
│   │   └── jharkhand_holidays.csv
│   └── processed/
│       └── load_cleaned_30min.csv
├── models/
│   ├── forecast_model.joblib
│   ├── feature_list.json
│   └── model_comparison.csv
└── notebooks/
    └── eda_and_modeling.ipynb
```

## Data Sources

| Data | File or Source | Purpose |
| --- | --- | --- |
| Historical load | `data/raw/Utility_consumption.csv` | Provided feeder-level load data. |
| Weather | Open-Meteo archive and forecast APIs | Temperature, humidity, cloud cover, and wind speed for Dhanbad. |
| Holidays | `data/raw/jharkhand_holidays.csv` | Jharkhand/Dhanbad events including Sarhul, Karma Puja, Chhath Puja, Jharkhand Foundation Day, and BCCL maintenance. |

## Modeling Approach

The pipeline compares three models on a time-based validation split:

| Model | MAE | RMSE | MAPE | R2 |
| --- | ---: | ---: | ---: | ---: |
| Random Forest | 1530.845 kW | 2198.926 kW | 2.358% | 0.97610 |
| Linear Regression | 1575.918 kW | 2152.431 kW | 2.540% | 0.97710 |
| Mean baseline | 14590.772 kW | 16848.582 kW | 25.968% | -0.40307 |

The final API uses Random Forest because it performs best on MAE and handles nonlinear relationships among demand, hour-of-day patterns, weather interactions, holidays, and lag features.

## Engineered Features

- Hour and day-of-week features.
- Cyclical hour and weekday encodings.
- Weekend flag.
- Local holiday flag.
- Temperature, humidity, cloud cover, and wind speed.
- Temperature-humidity interaction.
- Feels-like estimate.
- Lag features for prior day, prior two days, and prior week.

## Backend API

Run locally from this folder after installing requirements:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Health check and model-load status. |
| `/forecast` | GET | Returns 48 half-hour demand predictions for the next 24 hours. |
| `/weather` | GET | Returns Dhanbad weather forecast data at 30-minute resolution. |
| `/holidays` | GET | Returns upcoming localized holidays within the next 60 days. |

## Frontend Dashboard

The frontend renders:

- A 24-hour demand forecast chart.
- Weather summary cards.
- Upcoming local holiday table.
- API status messaging.

When served through Docker Compose, the dashboard is available at:

```text
http://localhost:3000
```

## Docker Run

From this folder:

```bash
docker compose up --build
```

Then open:

- Dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Forecast JSON: `http://localhost:8000/forecast`

## Rebuilding Data and Model Artifacts

The cleaned data, feature list, model, and model comparison file are already included. To rebuild them:

```bash
python -m venv venv
venv\Scripts\activate
pip install pandas numpy requests scikit-learn joblib
python pipeline.py
```

The script expects the raw load CSV at:

```text
data/raw/Utility_consumption.csv
```

## Assignment Coverage

| Requirement | Status |
| --- | --- |
| EDA notebook | Complete: `notebooks/eda_and_modeling.ipynb` |
| Load cleaning and outlier handling | Complete: `pipeline.py` and processed CSV |
| Weather integration | Complete: Open-Meteo historical and forecast data |
| Local holiday integration | Complete: Jharkhand/Dhanbad holiday file |
| Feature engineering | Complete |
| Model implementation and artifact | Complete |
| Forecast API | Complete |
| Weather and holiday APIs | Complete |
| Frontend visualization | Complete |
| Docker packaging | Complete |

## Important Note

The historical load dataset ends in 2017. The live forecast endpoint therefore uses a replay alignment for time and lag features while still fetching current weather. This is documented in the API warning field when the source data is older than the forecast date.
