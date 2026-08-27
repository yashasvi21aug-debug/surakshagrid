from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split


ML_DIR = Path(__file__).resolve().parent
MODEL_DIR = ML_DIR / "models"
CLASSIFIER_PATH = MODEL_DIR / "inundation_classifier.json"
REGRESSOR_PATH = MODEL_DIR / "water_rise_regressor.json"
RANDOM_SEED = 42
FEATURE_COLUMNS = [
    "rain_rate",
    "upstream_discharge",
    "soil_moisture",
    "elevation",
    "drainage_index",
]


def generate_synthetic_dataset(n_samples: int = 4000) -> pd.DataFrame:
    """Generate deterministic rainfall events representative of the Yamuna-Hindon basin."""
    if n_samples < 100:
        raise ValueError("n_samples must be at least 100")

    rng = np.random.default_rng(RANDOM_SEED)
    rain_rate = rng.gamma(shape=2.2, scale=18.0, size=n_samples).clip(0, 180)
    upstream_discharge = rng.lognormal(mean=np.log(260), sigma=0.55, size=n_samples).clip(30, 1600)
    soil_moisture = rng.uniform(22, 98, size=n_samples)
    elevation = rng.uniform(2, 180, size=n_samples)
    drainage_index = rng.uniform(0.08, 1.0, size=n_samples)

    normalized_rain = rain_rate / 180
    normalized_discharge = upstream_discharge / 1600
    normalized_soil = soil_moisture / 100
    normalized_elevation = 1 - elevation / 180
    normalized_drainage = 1 - drainage_index
    hazard_score = (
        0.38 * normalized_rain
        + 0.30 * normalized_discharge
        + 0.18 * normalized_soil
        + 0.08 * normalized_elevation
        + 0.06 * normalized_drainage
    )
    risk_probability = 1 / (1 + np.exp(-12 * (hazard_score - 0.42)))
    inundated = (risk_probability + rng.normal(0, 0.06, n_samples) >= 0.5).astype(np.int32)
    water_rise = np.clip(
        0.15
        + 5.4 * risk_probability
        + 0.7 * normalized_rain
        + 0.45 * normalized_discharge
        + rng.normal(0, 0.12, n_samples),
        0,
        8,
    )

    return pd.DataFrame(
        {
            "rain_rate": rain_rate,
            "upstream_discharge": upstream_discharge,
            "soil_moisture": soil_moisture,
            "elevation": elevation,
            "drainage_index": drainage_index,
            "inundated": inundated,
            "water_rise": water_rise,
        }
    )


def train_models(
    dataset: pd.DataFrame | None = None,
) -> tuple[xgb.XGBClassifier, xgb.XGBRegressor, dict[str, float]]:
    df = dataset if dataset is not None else generate_synthetic_dataset()
    features = df[FEATURE_COLUMNS]
    classifier_target = df["inundated"]
    regressor_target = df["water_rise"]
    x_train, x_test, y_class_train, y_class_test = train_test_split(
        features, classifier_target, test_size=0.2, random_state=RANDOM_SEED, stratify=classifier_target
    )
    x_train_reg, x_test_reg, y_reg_train, y_reg_test = train_test_split(
        features, regressor_target, test_size=0.2, random_state=RANDOM_SEED
    )

    classifier = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=180,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    classifier.fit(x_train, y_class_train)

    regressor = xgb.XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        n_estimators=180,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    regressor.fit(x_train_reg, y_reg_train)

    metrics = {
        "classifier_auc": float(roc_auc_score(y_class_test, classifier.predict_proba(x_test)[:, 1])),
        "regressor_rmse": float(mean_squared_error(y_reg_test, regressor.predict(x_test_reg)) ** 0.5),
    }
    return classifier, regressor, metrics


def save_models(classifier: xgb.XGBClassifier, regressor: xgb.XGBRegressor) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    classifier.save_model(str(CLASSIFIER_PATH))
    regressor.save_model(str(REGRESSOR_PATH))


def compile_models() -> dict[str, object]:
    classifier, regressor, metrics = train_models()
    save_models(classifier, regressor)
    return {
        "status": "compiled",
        "classifier": str(CLASSIFIER_PATH),
        "regressor": str(REGRESSOR_PATH),
        **metrics,
    }


def main() -> None:
    print(json.dumps(compile_models(), indent=2))


if __name__ == "__main__":
    main()
