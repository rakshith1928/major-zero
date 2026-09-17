"""T09 paper artifact: RandomForest demand model on the seeded history.

Run:  ../.venv/Scripts/python research/analytics_notebook.py
Reads the dev SQLite DB (backend/zerobus.db — seed it first), trains a
RandomForestRegressor on (weekday, departure hour, bus-type, route) ->
occupancy, and writes research/results/demand_{model.pkl, metrics.json}.
"""

import json
import pickle
import sqlite3
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
DB = HERE.parent / "backend" / "zerobus.db"

BUS_TYPE_CODE = {"AC_SLEEPER": 0, "AC_SEMI_SLEEPER": 1, "NON_AC_SEATER": 2}


def load_frame():
    import pandas as pd

    conn = sqlite3.connect(DB)
    bookings = pd.read_sql_query(
        "SELECT bus_id, travel_date, COUNT(*) AS taken FROM bookings "
        "WHERE is_synthetic=1 GROUP BY bus_id, travel_date",
        conn,
    )
    buses = pd.read_sql_query("SELECT * FROM buses", conn)
    conn.close()
    frame = bookings.merge(buses, left_on="bus_id", right_on="id")
    frame["travel_date"] = pd.to_datetime(frame["travel_date"]).dt.date
    frame["weekday"] = pd.to_datetime(frame["travel_date"]).dt.weekday
    frame["dep_hour"] = frame["departure_time"].str.slice(0, 2).astype(int)
    frame["bus_code"] = frame["bus_type"].map(BUS_TYPE_CODE)
    frame["route_code"] = (
        frame["origin"] + ">" + frame["destination"]
    ).astype("category").cat.codes
    frame["occupancy"] = frame["taken"] / frame["total_seats"]
    return frame


def main() -> None:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import train_test_split

    frame = load_frame()
    features = ["weekday", "dep_hour", "bus_code", "route_code"]
    X_train, X_test, y_train, y_test = train_test_split(
        frame[features], frame["occupancy"], test_size=0.2, random_state=42
    )
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, pred))
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "demand_model.pkl").open("wb") as fh:
        pickle.dump(model, fh)
    (RESULTS / "demand_metrics.json").write_text(
        json.dumps(
            {
                "model": "RandomForestRegressor(n=100)",
                "mae": mae,
                "n_rows": len(frame),
                "feature_importance": dict(
                    zip(features, [round(float(v), 3) for v in model.feature_importances_])
                ),
            },
            indent=2,
        )
    )
    print(f"rows={len(frame)} MAE={mae:.4f}")


if __name__ == "__main__":
    main()
