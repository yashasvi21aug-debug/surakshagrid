from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, roc_auc_score


MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "inundation_model.joblib"


def generate_synthetic_dataset(n_samples: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(42)

    precipitation_mm_h = rng.uniform(0, 120, size=n_samples)
    upstream_river_discharge_m3s = rng.uniform(30, 700, size=n_samples)
    soil_moisture_percentage = rng.uniform(20, 95, size=n_samples)
    elevation_m = rng.uniform(2, 120, size=n_samples)
    drainage_capacity_index = rng.uniform(0.1, 1.0, size=n_samples)

    flood_score = (
        0.45 * (precipitation_mm_h / 120)
        + 0.35 * (upstream_river_discharge_m3s / 700)
        + 0.25 * (soil_moisture_percentage / 100)
        + 0.15 * (1 - elevation_m / 120)
        + 0.20 * (1 - drainage_capacity_index)
    )
    flood_score = np.clip(flood_score, 0, 1)

    flood_inundation_risk = np.clip(flood_score + rng.normal(0, 0.08, size=n_samples), 0, 1)
    water_rise_meters = (
        0.8 * flood_inundation_risk * 5.0
        + 0.2 * (100 - elevation_m) / 100 * 4.0
        + 0.15 * precipitation_mm_h / 50
    )
    water_rise_meters = np.clip(water_rise_meters, 0, 8)

    dataset = pd.DataFrame(
        {
            "precipitation_mm_h": precipitation_mm_h,
            "upstream_river_discharge_m3s": upstream_river_discharge_m3s,
            "soil_moisture_percentage": soil_moisture_percentage,
            "elevation_m": elevation_m,
            "drainage_capacity_index": drainage_capacity_index,
            "flood_inundation_risk": flood_inundation_risk,
            "water_rise_meters": water_rise_meters,
        }
    )
    return dataset


def train_models() -> tuple[xgb.XGBClassifier, xgb.XGBRegressor, dict]:
    df = generate_synthetic_dataset()
    feature_cols = [
        "precipitation_mm_h",
        "upstream_river_discharge_m3s",
        "soil_moisture_percentage",
        "elevation_m",
        "drainage_capacity_index",
    ]

    X = df[feature_cols]
    y_risk = df["flood_inundation_risk"]
    y_depth = df["water_rise_meters"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_risk, test_size=0.2, random_state=42
    )
    X_train_d, X_test_d, y_depth_train, y_depth_test = train_test_split(
        X, y_depth, test_size=0.2, random_state=42
    )

    classifier = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="auc",
        n_estimators=300,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    classifier.fit(X_train, y_train)

    regressor = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    regressor.fit(X_train_d, y_depth_train)

    risk_proba = classifier.predict_proba(X_test)[:, 1]
    risk_auc = roc_auc_score(y_test.round(0), risk_proba)
    depth_rmse = mean_squared_error(y_depth_test, regressor.predict(X_test_d), squared=False)

    metrics = {
        "risk_auc": float(risk_auc),
        "water_rise_rmse_m": float(depth_rmse),
        "feature_columns": feature_cols,
    }
    return classifier, regressor, metrics


def save_models(classifier: xgb.XGBClassifier, regressor: xgb.XGBRegressor) -> None:
    payload = {
        "classifier": classifier,
        "regressor": regressor,
        "feature_columns": [
            "precipitation_mm_h",
            "upstream_river_discharge_m3s",
            "soil_moisture_percentage",
            "elevation_m",
            "drainage_capacity_index",
        ],
    }
    joblib.dump(payload, MODEL_PATH)


def main() -> None:
    classifier, regressor, metrics = train_models()
    save_models(classifier, regressor)
    print(json.dumps({"status": "trained", "model_path": str(MODEL_PATH), **metrics}, indent=2))


if __name__ == "__main__":
    main()
