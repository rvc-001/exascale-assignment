# Testing and Verification

## Assignment 1

Run the pipeline from `project/assignment 1`:

```bash
python pipeline.py
```

Expected outputs:

- `data/processed/load_cleaned_30min.csv`
- `models/forecast_model.joblib`
- `models/feature_list.json`
- `models/model_comparison.csv`

Then start the stack:

```bash
docker compose up --build
```

Check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/forecast
curl http://localhost:8000/weather
curl http://localhost:8000/holidays
```

## Assignment 2

From `project/assignment 2/backend`, run:

```bash
pytest
```

Start the app:

```bash
docker compose up --build
```

Verify the analytics endpoints:

```bash
curl "http://localhost:8000/api/analytics/yoy?year=2024"
curl "http://localhost:8000/api/analytics/intensity?metric=Tons%20of%20Steel%20Produced&year=2024"
curl "http://localhost:8000/api/analytics/hotspot?year=2024"
curl "http://localhost:8000/api/analytics/monthly?year=2024"
```

Historical factor check:

```bash
curl -X POST http://localhost:8000/api/emissions/scope1 ^
  -H "Content-Type: application/json" ^
  -d "{\"activity_date\":\"2022-06-15\",\"activity_type\":\"Anthracite Coal\",\"activity_amount\":10}"
```

The returned `factor_used.source` should contain `historical 2020-2022`.

Override and audit check:

```bash
curl -X PATCH http://localhost:8000/api/emissions/1/override ^
  -H "Content-Type: application/json" ^
  -d "{\"new_emissions_value\":12345,\"reason\":\"verification correction\",\"changed_by\":\"tester\"}"

curl http://localhost:8000/api/emissions/audit-log
```
