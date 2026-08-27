from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

MODEL_PATH = Path(__file__).resolve().parent / "inundation_model.joblib"
MODEL_DIR = Path(__file__).resolve().parent / "models"
CLASSIFIER_MODEL_PATH = MODEL_DIR / "inundation_classifier.json"
REGRESSOR_MODEL_PATH = MODEL_DIR / "water_rise_regressor.json"
FEATURE_COLUMNS = [
    "precipitation_mm_h",
    "upstream_river_discharge_m3s",
    "soil_moisture_percentage",
    "elevation_m",
    "drainage_capacity_index",
]


class FloodRiskPredictor:
    def __init__(self, model_path: str | Path = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.model_bundle = None
        self.classifier = None
        self.regressor = None
        self.feature_columns = FEATURE_COLUMNS

    def _load_model(self) -> None:
        if self.model_bundle is not None:
            return

        if CLASSIFIER_MODEL_PATH.is_file() and REGRESSOR_MODEL_PATH.is_file():
            self.classifier = xgb.XGBClassifier()
            self.classifier.load_model(str(CLASSIFIER_MODEL_PATH))
            self.regressor = xgb.XGBRegressor()
            self.regressor.load_model(str(REGRESSOR_MODEL_PATH))
            self.feature_columns = [
                "rain_rate",
                "upstream_discharge",
                "soil_moisture",
                "elevation",
                "drainage_index",
            ]
            self.model_bundle = {"format": "xgboost_json"}
            return

        if not self.model_path.is_file():
            raise FileNotFoundError(
                "Flood model artifacts are missing. Run 'python -m ml.train_and_save' first."
            )

        self.model_bundle = joblib.load(self.model_path)
        self.classifier = self.model_bundle["classifier"]
        self.regressor = self.model_bundle["regressor"]
        self.feature_columns = self.model_bundle.get("feature_columns", FEATURE_COLUMNS)

    def preload_static_models(self) -> bool:
        if not (CLASSIFIER_MODEL_PATH.is_file() and REGRESSOR_MODEL_PATH.is_file()):
            return False
        self._load_model()
        return True

    def predict_risk(self, lat: float, lng: float, rain_rate: float, discharge: float) -> dict:
        self._load_model()
        # Synthetic geospatial calibration: low elevation and wet conditions increase inundation risk.
        elevation_proxy = max(2.0, 80.0 - abs(lat) * 2.4)
        soil_moisture = min(98.0, max(35.0, 50.0 + rain_rate * 0.9))
        drainage_index = max(0.1, min(1.0, 0.85 - (discharge / 1000.0) * 0.35))

        feature_values = {
            "rain_rate": float(rain_rate),
            "upstream_discharge": float(discharge),
            "soil_moisture": float(soil_moisture),
            "elevation": float(elevation_proxy),
            "drainage_index": float(drainage_index),
            "precipitation_mm_h": float(rain_rate),
            "upstream_river_discharge_m3s": float(discharge),
            "soil_moisture_percentage": float(soil_moisture),
            "elevation_m": float(elevation_proxy),
            "drainage_capacity_index": float(drainage_index),
        }
        input_df = pd.DataFrame([{column: feature_values[column] for column in self.feature_columns}])

        risk_probability = float(self.classifier.predict_proba(input_df[self.feature_columns])[0, 1])
        water_rise = float(self.regressor.predict(input_df[self.feature_columns])[0])

        should_flag = risk_probability >= 0.6 or water_rise >= 1.5
        return {
            "lat": float(lat),
            "lng": float(lng),
            "risk_probability": round(risk_probability, 6),
            "water_rise_meters": round(water_rise, 4),
            "should_flag_flood_polygon": bool(should_flag),
            "status": "HIGH" if should_flag else "MODERATE" if risk_probability >= 0.35 else "LOW",
        }


_predictor = FloodRiskPredictor()


def preload_static_models() -> bool:
    return _predictor.preload_static_models()


def predict_risk(lat: float, lng: float, rain_rate: float, discharge: float) -> dict:
    return _predictor.predict_risk(lat, lng, rain_rate, discharge)
