from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.ensemble import RandomForestRegressor
import joblib
import json
import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
import math
import os
from functools import lru_cache
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="APU Demand Forecast API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

model = joblib.load(os.path.join(BASE_DIR, "models", "forecast_model.joblib"))
with open(os.path.join(BASE_DIR, "models", "feature_list.json")) as f:
    FEATURES = json.load(f)

print(f"Model loaded. Features ({len(FEATURES)}): {FEATURES}")

@app.get("/forecast")
def get_forecast():
    now_ist = datetime.now(IST)
    now_floor = now_ist.replace(second=0, microsecond=0)
    remainder = now_floor.minute % 30
    now_floor = now_floor.replace(minute=now_floor.minute - remainder)

    forecast_times = [now_floor + timedelta(minutes=30 * i) for i in range(48)]
    weather_hourly = fetch_weather_forecast(now_floor)

    hist = pd.read_csv(os.path.join(BASE_DIR, "data", "processed", "load_cleaned_30min.csv"), parse_dates=True, index_col=0).sort_index()
    hist = hist.tail(1500)
    
    csv_last = hist.index[-1]
    now_naive = now_floor.replace(tzinfo=None)
    weeks_diff = 0
    if csv_last < now_naive - timedelta(days=2):
        weeks_diff = math.ceil((now_naive - csv_last.to_pydatetime()) / timedelta(weeks=1))
        
    replay_warning = None
    if weeks_diff > 0:
        replay_warning = (
            f"CSV ends at {csv_last.date()}; time features and lags shifted by {weeks_diff} weeks "
            "(replay mode). Note: Weather data is still live, causing seasonal inconsistency. Deploy with a live data feed for production."
        )
        logging.warning(replay_warning)

    rows = []
    for i, t in enumerate(forecast_times):
        row = build_feature_row(t, weather_hourly[i], hist, weeks_diff)
        rows.append(row)

    X = pd.DataFrame(rows)[FEATURES]
    predictions = model.predict(X)

    result = {
        "forecast": [
            {"timestamp": t.isoformat(), "predicted_load_kw": round(float(p), 2)}
            for t, p in zip(forecast_times, predictions)
        ]
    }
    if replay_warning:
        result["warning"] = replay_warning
    return result

def build_feature_row(t: datetime, weather: dict, hist: pd.DataFrame, weeks_diff: int = 0) -> dict:
    t_shifted = t - timedelta(weeks=weeks_diff)
    t_ist = t_shifted if t_shifted.tzinfo else t_shifted.replace(tzinfo=IST)
    
    row = {
        'hour':        t_ist.hour,
        'day_of_week': t_ist.weekday(),
        'month':       t_ist.month,
        'quarter':     (t_ist.month - 1) // 3 + 1,
        'is_weekend':  int(t_ist.weekday() >= 5),
        'week_of_year': t_ist.isocalendar()[1],
        'hour_sin':    np.sin(2 * np.pi * t_ist.hour / 24),
        'hour_cos':    np.cos(2 * np.pi * t_ist.hour / 24),
        'dow_sin':     np.sin(2 * np.pi * t_ist.weekday() / 7),
        'dow_cos':     np.cos(2 * np.pi * t_ist.weekday() / 7),
    }

    holiday_timestamps = _get_holiday_set()
    row['is_holiday'] = int(pd.Timestamp(t_ist).strftime('%Y-%m-%d') in holiday_timestamps)

    row['temperature']     = weather.get('temperature', 25.0)
    row['humidity']        = weather.get('humidity', 60.0)
    row['cloud_cover']     = weather.get('cloud_cover', 50.0)
    row['wind_speed']      = weather.get('wind_speed', 10.0)
    row['temp_x_humidity'] = row['temperature'] * row['humidity']
    row['feels_like']      = (row['temperature'] - 0.55 * (1 - row['humidity'] / 100) * (row['temperature'] - 14.5))

    def get_lag(blocks_back: int) -> float:
        target_naive = (t_shifted - timedelta(minutes=30 * blocks_back)).replace(tzinfo=None)
        target_ts = pd.Timestamp(target_naive).floor('30min')
        if target_ts in hist.index:
            val = hist.loc[target_ts]
            return float(val.iloc[0]) if hasattr(val, 'iloc') else float(val)
        logging.warning(f"Lag lookup miss: {target_ts} not in hist")
        return float(hist['load'].mean()) if 'load' in hist.columns else 0.0

    row['lag_48']  = get_lag(48)
    row['lag_96']  = get_lag(96)
    row['lag_336'] = get_lag(336)
    return row

@lru_cache(maxsize=1)
def _get_holiday_set():
    path = os.path.join(BASE_DIR, "data", "raw", "jharkhand_holidays.csv")
    hdf = pd.read_csv(path, parse_dates=['date'])
    return set(hdf['date'].dt.strftime('%Y-%m-%d'))

@app.get("/weather")
def get_weather():
    now_ist = datetime.now(IST)
    now_floor = now_ist.replace(second=0, microsecond=0)
    remainder = now_floor.minute % 30
    now_floor = now_floor.replace(minute=now_floor.minute - remainder)
    weather = fetch_weather_forecast(now_floor)
    return {"weather": weather}

def fetch_weather_forecast(now_floor: datetime):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 23.7957, "longitude": 86.4304,
        "hourly": "temperature_2m,relative_humidity_2m,cloudcover,windspeed_10m",
        "timezone": "Asia/Kolkata", "forecast_days": 2
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logging.error(f"Weather API failed: {e}. Falling back to historical means.")
        data = {
            "hourly": {
                "time": [(now_floor.replace(tzinfo=None) + timedelta(hours=i)).isoformat() for i in range(48)],
                "temperature_2m": [25.0] * 48,
                "relative_humidity_2m": [50.0] * 48,
                "cloudcover": [30.0] * 48,
                "windspeed_10m": [5.0] * 48
            }
        }
    times = pd.to_datetime(data["hourly"]["time"])
    weather_hourly = pd.DataFrame({
        "temperature": data["hourly"]["temperature_2m"],
        "humidity":    data["hourly"]["relative_humidity_2m"],
        "cloud_cover": data["hourly"]["cloudcover"],
        "wind_speed":  data["hourly"]["windspeed_10m"]
    }, index=times)
    weather_30min = weather_hourly.resample('30min').interpolate(method='linear')
    now_floor_naive = now_floor.replace(tzinfo=None)
    forecast_index = [now_floor_naive + timedelta(minutes=30 * i) for i in range(48)]
    result = []
    for ts in forecast_index:
        if ts in weather_30min.index: row = weather_30min.loc[ts]
        else: row = weather_30min.iloc[-1]
        result.append({
            "time":        ts.isoformat(),
            "temperature": round(float(row["temperature"]), 1),
            "humidity":    round(float(row["humidity"]), 1),
            "cloud_cover": round(float(row["cloud_cover"]), 1),
            "wind_speed":  round(float(row["wind_speed"]), 1)
        })
    return result

@app.get("/holidays")
def get_holidays():
    holidays_df = pd.read_csv(os.path.join(BASE_DIR, "data", "raw", "jharkhand_holidays.csv"), parse_dates=["date"])
    now_ist_date = datetime.now(IST).date()
    upcoming = holidays_df[
        (holidays_df["date"].dt.date >= now_ist_date) &
        (holidays_df["date"].dt.date <= now_ist_date + timedelta(days=60))
    ].head(5).copy()
    upcoming["date"] = upcoming["date"].dt.strftime("%Y-%m-%d")
    return {"holidays": upcoming[["date", "holiday_name", "type"]].to_dict(orient="records")}

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}
