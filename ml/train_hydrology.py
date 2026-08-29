from __future__ import annotations

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / "models"
INUNDATION_MODEL_PATH = MODEL_DIR / "inundation_xgb.json"
DEPTH_MODEL_PATH = MODEL_DIR / "depth_xgb.json"

FEATURE_COLUMNS = [
    "precipitation_rate_mm_hr",
    "upstream_discharge_m3_s",
    "soil_saturation_pct",
    "elevation_m",
    "distance_to_drainage_m",
]


def generate_synthetic_hydrology_dataset(num_samples: int = 2500, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic hydro-meteorological catchment training data."""
    rng = np.random.default_rng(seed)

    precipitation = rng.uniform(0.0, 150.0, size=num_samples)
    discharge = rng.uniform(10.0, 3500.0, size=num_samples)
    soil_sat = rng.uniform(10.0, 100.0, size=num_samples)
    elevation = rng.uniform(2.0, 250.0, size=num_samples)
    distance = rng.uniform(10.0, 5000.0, size=num_samples)

    # Physical runoff calculation for ground truth target generation
    c_factor = 0.2 + 0.7 * (soil_sat / 100.0)
    q_discharge = (c_factor * precipitation / (5.0 + 0.1 * np.maximum(1.0, elevation))) * np.exp(-distance / 2500.0) + (discharge / 1000.0)
    
    # Inundation risk probability (0 to 1)
    inundation_prob = 1.0 / (1.0 + np.exp(-8.0 * (q_discharge - 0.6)))
    inundation_binary = (inundation_prob >= 0.5).astype(int)

    # Water rise depth in meters
    water_rise_m = np.maximum(0.0, 0.15 + 4.8 * inundation_prob + 0.5 * (precipitation / 150.0) + rng.normal(0, 0.05, size=num_samples))

    df = pd.DataFrame({
        "precipitation_rate_mm_hr": precipitation,
        "upstream_discharge_m3_s": discharge,
        "soil_saturation_pct": soil_sat,
        "elevation_m": elevation,
        "distance_to_drainage_m": distance,
        "inundation_risk": inundation_binary,
        "water_rise_m": water_rise_m,
    })
    return df


def train_and_serialize_models() -> dict[str, str]:
    """Train XGBClassifier and XGBRegressor on hydrological dataset and save JSON model weights."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_hydrology_dataset(num_samples=2500)
    X = df[FEATURE_COLUMNS]
    y_clf = df["inundation_risk"]
    y_reg = df["water_rise_m"]

    # 1. Train Inundation Risk Classifier
    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X, y_clf)
    clf.save_model(str(INUNDATION_MODEL_PATH))
    logger.info("Saved XGBClassifier inundation model to %s", INUNDATION_MODEL_PATH)

    # 2. Train Water Level Rise Regressor
    reg = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        eval_metric="rmse",
        random_state=42,
    )
    reg.fit(X, y_reg)
    reg.save_model(str(DEPTH_MODEL_PATH))
    logger.info("Saved XGBRegressor water rise depth model to %s", DEPTH_MODEL_PATH)

    return {
        "inundation_model": str(INUNDATION_MODEL_PATH),
        "depth_model": str(DEPTH_MODEL_PATH),
    }


if __name__ == "__main__":
    result = train_and_serialize_models()
    print(f"Hydrological XGBoost Models Trained Successfully: {result}")
