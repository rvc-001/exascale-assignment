import os
import json
import requests
import pandas as pd
import numpy as np
import math
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.dummy import DummyRegressor
import joblib
from pathlib import Path
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DATA = PROJECT_DIR / "data" / "raw" / "Utility_consumption.csv"

def mape_percent(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

def main():
    # Setup directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    
    # 1. Load Data
    logging.info("Loading load data...")
    if not SOURCE_DATA.exists():
        raise FileNotFoundError(
            f"Utility_consumption.csv not found at {SOURCE_DATA}. "
            "Place it in data/raw before running the pipeline."
        )
    df = pd.read_csv(SOURCE_DATA)
    df['Datetime'] = pd.to_datetime(df['Datetime'], format='mixed')
    df = df.set_index('Datetime')
    df = df.sort_index()
    
    FEEDER_COLS = [c for c in df.columns if 'PowerConsumption' in c]
    logging.info(f"Feeder cols: {FEEDER_COLS}")
    
    # 2. Collect Weather Data
    logging.info("Fetching Open-Meteo weather data...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 23.7957,
        "longitude": 86.4304,
        "start_date": "2017-01-01",
        "end_date": "2017-12-30",
        "hourly": "temperature_2m,relative_humidity_2m,cloudcover,windspeed_10m",
        "timezone": "Asia/Kolkata"
    }
    response = requests.get(url, params=params)
    weather_data = response.json()
    
    weather_df = pd.DataFrame({
        'timestamp': weather_data['hourly']['time'],
        'temperature': weather_data['hourly']['temperature_2m'],
        'humidity': weather_data['hourly']['relative_humidity_2m'],
        'cloud_cover': weather_data['hourly']['cloudcover'],
        'wind_speed': weather_data['hourly']['windspeed_10m']
    })
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    weather_df.to_csv('data/raw/weather_data.csv', index=False)
    weather_30min = weather_df.set_index('timestamp').resample('30min').interpolate(method='linear')
    
    # 3. Clean and aggregate Load Data
    logging.info("Cleaning load data...")
    df_clean = df.copy()
    df_clean['load'] = df_clean[FEEDER_COLS].sum(axis=1, min_count=len(FEEDER_COLS))
    df_clean = df_clean[['load']]
    
    df_clean['load'] = df_clean['load'].interpolate(method='time', limit=3)
    
    # Outlier clipping
    def grouped_clip(series):
        month = series.index.month
        hour = series.index.hour
        is_weekend = series.index.dayofweek >= 5
        result = series.copy()
        for m in range(1, 13):
            for h in range(24):
                for w in [True, False]:
                    mask = (month == m) & (hour == h) & (is_weekend == w)
                    if mask.sum() < 4:
                        continue
                    s = series[mask]
                    Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
                    IQR = Q3 - Q1
                    result[mask] = s.clip(lower=Q1 - 1.5 * IQR, upper=Q3 + 1.5 * IQR)
        return result

    df_clean['load'] = grouped_clip(df_clean['load'])
    
    # Resample to 30 min and handle long gaps
    df_30min = df_clean.resample('30min').mean()
    df_30min['load'] = df_30min['load'].fillna(df_30min['load'].shift(336))
    df_30min['load'] = df_30min['load'].ffill()
    df_30min['load'] = df_30min['load'].bfill()
    assert df_30min['load'].isnull().sum() == 0, "Still has nulls!"
    df_30min.to_csv('data/processed/load_cleaned_30min.csv')
    
    # 4. Feature Engineering
    logging.info("Engineering features...")
    df_feat = df_30min.copy()
    df_feat['hour'] = df_feat.index.hour
    df_feat['day_of_week'] = df_feat.index.dayofweek
    df_feat['month'] = df_feat.index.month
    df_feat['quarter'] = df_feat.index.quarter
    df_feat['is_weekend'] = (df_feat.index.dayofweek >= 5).astype(int)
    df_feat['week_of_year'] = df_feat.index.isocalendar().week.astype(int)
    
    df_feat['hour_sin'] = np.sin(2 * np.pi * df_feat['hour'] / 24)
    df_feat['hour_cos'] = np.cos(2 * np.pi * df_feat['hour'] / 24)
    df_feat['dow_sin'] = np.sin(2 * np.pi * df_feat['day_of_week'] / 7)
    df_feat['dow_cos'] = np.cos(2 * np.pi * df_feat['day_of_week'] / 7)
    
    # Holidays
    holiday_dates = pd.to_datetime(pd.read_csv('data/raw/jharkhand_holidays.csv')['date']).dt.normalize()
    df_feat['is_holiday'] = df_feat.index.normalize().isin(holiday_dates).astype(int)
    
    # Lags
    df_feat['lag_48'] = df_feat['load'].shift(48)
    df_feat['lag_96'] = df_feat['load'].shift(96)
    df_feat['lag_336'] = df_feat['load'].shift(336)
    
    # Weather
    df_feat = df_feat.join(weather_30min[['temperature', 'humidity', 'cloud_cover', 'wind_speed']], how='left')
    df_feat['temperature'] = df_feat['temperature'].ffill().bfill()
    df_feat['humidity'] = df_feat['humidity'].ffill().bfill()
    df_feat['cloud_cover'] = df_feat['cloud_cover'].ffill().bfill()
    df_feat['wind_speed'] = df_feat['wind_speed'].ffill().bfill()
    
    df_feat['temp_x_humidity'] = df_feat['temperature'] * df_feat['humidity']
    df_feat['feels_like'] = df_feat['temperature'] - 0.55 * (1 - df_feat['humidity']/100) * (df_feat['temperature'] - 14.5)
    
    df_feat = df_feat.dropna()
    
    FEATURES = [
        'hour', 'day_of_week', 'is_weekend',
        'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos',
        'is_holiday',
        'temperature', 'humidity', 'cloud_cover', 'wind_speed',
        'temp_x_humidity', 'feels_like',
        'lag_48', 'lag_96', 'lag_336'
    ]
    TARGET = 'load'
    
    # 5. Train-Test Split & Training
    logging.info("Training and comparing candidate models...")
    n = len(df_feat)
    train_df = df_feat.iloc[:int(n * 0.70)]
    val_df   = df_feat.iloc[int(n * 0.70):int(n * 0.85)]
    test_df  = df_feat.iloc[int(n * 0.85):]
    
    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_val,   y_val   = val_df[FEATURES],   val_df[TARGET]
    X_test,  y_test  = test_df[FEATURES],  test_df[TARGET]
    
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    candidates = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        ),
    }

    comparison = []
    fitted_models = {}
    for name, candidate in candidates.items():
        candidate.fit(X_train, y_train)
        preds = candidate.predict(X_test)
        comparison.append({
            "model": name,
            "mae": round(mean_absolute_error(y_test, preds), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds))), 3),
            "mape_percent": round(mape_percent(y_test, preds), 3),
            "r2": round(r2_score(y_test, preds), 5),
        })
        fitted_models[name] = candidate

    comparison_df = pd.DataFrame(comparison).sort_values("mae")
    comparison_df.to_csv("models/model_comparison.csv", index=False)
    logging.info("Model comparison:\n%s", comparison_df.to_string(index=False))

    model = fitted_models["random_forest"]
    rf_metrics = comparison_df[comparison_df["model"] == "random_forest"].iloc[0]
    logging.info(
        "Selected Random Forest - MAE: %.2f | RMSE: %.2f | MAPE: %.2f%% | R2: %.3f",
        rf_metrics["mae"], rf_metrics["rmse"], rf_metrics["mape_percent"], rf_metrics["r2"]
    )
    
    # 6. Save Artifacts
    joblib.dump(model, 'models/forecast_model.joblib')
    with open('models/feature_list.json', 'w') as f:
        json.dump(FEATURES, f)
    logging.info("Implementation successful. Models and data saved.")

if __name__ == "__main__":
    main()
