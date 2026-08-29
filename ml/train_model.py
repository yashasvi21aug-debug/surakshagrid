from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ML_DIR = Path(__file__).resolve().parent
MODEL_DIR = ML_DIR / "models"
MODEL_PATH = MODEL_DIR / "inundation_model.joblib"
CLASSIFIER_JSON = MODEL_DIR / "inundation_classifier.json"
REGRESSOR_JSON = MODEL_DIR / "water_rise_regressor.json"

RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "elevation",
    "precipitation_rate",
    "soil_saturation",
    "distance_to_drainage",
    "upstream_discharge",
]


def generate_synthetic_hydrological_data(n_samples: int = 4000) -> pd.DataFrame:
    """Generate realistic hydro-meteorological observations for the Yamuna-Hindon basin."""
    rng = np.random.default_rng(RANDOM_SEED)

    precipitation_rate = rng.gamma(shape=2.2, scale=18.0, size=n_samples).clip(0, 180)
    upstream_discharge = rng.lognormal(mean=np.log(260), sigma=0.55, size=n_samples).clip(30, 1600)
    soil_saturation = rng.uniform(20, 100, size=n_samples)
    elevation = rng.uniform(2, 180, size=n_samples)
    distance_to_drainage = rng.uniform(10, 5000, size=n_samples)

    norm_rain = precipitation_rate / 180.0
    norm_dis = upstream_discharge / 1600.0
    norm_soil = soil_saturation / 100.0
    norm_elev = 1.0 - elevation / 180.0
    norm_dist = 1.0 - distance_to_drainage / 5000.0

    hazard_score = (
        0.38 * norm_rain
        + 0.28 * norm_dis
        + 0.18 * norm_soil
        + 0.10 * norm_elev
        + 0.06 * norm_dist
    )

    risk_prob = 1.0 / (1.0 + np.exp(-12.0 * (hazard_score - 0.42)))
    inundated = (risk_prob + rng.normal(0, 0.06, n_samples) >= 0.5).astype(np.int32)
    water_rise = np.clip(
        0.15
        + 5.4 * risk_prob
        + 0.7 * norm_rain
        + 0.45 * norm_dis
        + rng.normal(0, 0.12, n_samples),
        0.0,
        8.0,
    )

    return pd.DataFrame(
        {
            "elevation": elevation,
            "precipitation_rate": precipitation_rate,
            "soil_saturation": soil_saturation,
            "distance_to_drainage": distance_to_drainage,
            "upstream_discharge": upstream_discharge,
            # Backward compatibility aliases
            "rain_rate": precipitation_rate,
            "distance_to_waterway": distance_to_drainage,
            "inundated": inundated,
            "water_rise": water_rise,
        }
    )


def train_inundation_models(
    df: pd.DataFrame | None = None,
) -> tuple[Pipeline, Pipeline, dict[str, float]]:
    dataset = df if df is not None else generate_synthetic_hydrological_data()
    X = dataset[FEATURE_COLUMNS]
    y_clf = dataset["inundated"]
    y_reg = dataset["water_rise"]

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X, y_clf, test_size=0.2, random_state=RANDOM_SEED, stratify=y_clf
    )
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X, y_reg, test_size=0.2, random_state=RANDOM_SEED
    )

    clf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=RANDOM_SEED)),
    ])
    clf_pipeline.fit(X_train_c, y_train_c)

    reg_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=RANDOM_SEED)),
    ])
    reg_pipeline.fit(X_train_r, y_train_r)

    metrics = {
        "classifier_auc": float(roc_auc_score(y_test_c, clf_pipeline.predict_proba(X_test_c)[:, 1])),
        "regressor_rmse": float(mean_squared_error(y_test_r, reg_pipeline.predict(X_test_r)) ** 0.5),
    }

    return clf_pipeline, reg_pipeline, metrics


def save_serialized_model(clf_pipeline: Pipeline, reg_pipeline: Pipeline) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "classifier": clf_pipeline,
        "regressor": reg_pipeline,
        "feature_columns": FEATURE_COLUMNS,
    }
    joblib.dump(bundle, MODEL_PATH)

    # Clean up legacy static JSON files if present
    for json_file in (CLASSIFIER_JSON, REGRESSOR_JSON):
        if json_file.is_file():
            try:
                json_file.unlink()
            except Exception:
                pass


def compile_models() -> dict[str, object]:
    clf_pipeline, reg_pipeline, metrics = train_inundation_models()
    save_serialized_model(clf_pipeline, reg_pipeline)
    return {
        "status": "compiled",
        "model_path": str(MODEL_PATH),
        **metrics,
    }


def main() -> None:
    print(json.dumps(compile_models(), indent=2))


if __name__ == "__main__":
    main()
