from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "inundation_model.joblib"
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
        self.model_bundle = joblib.load(self.model_path)
        self.classifier = self.model_bundle["classifier"]
        self.regressor = self.model_bundle["regressor"]
        self.feature_columns = self.model_bundle.get("feature_columns", FEATURE_COLUMNS)

    def predict_risk(self, lat: float, lng: float, rain_rate: float, discharge: float) -> dict:
        # Synthetic geospatial calibration: low elevation and wet conditions increase inundation risk.
        elevation_proxy = max(2.0, 80.0 - abs(lat) * 2.4)
        soil_moisture = min(98.0, max(35.0, 50.0 + rain_rate * 0.9))
        drainage_index = max(0.1, min(1.0, 0.85 - (discharge / 1000.0) * 0.35))

        input_df = pd.DataFrame(
            [
                {
                    "precipitation_mm_h": float(rain_rate),
                    "upstream_river_discharge_m3s": float(discharge),
                    "soil_moisture_percentage": float(soil_moisture),
                    "elevation_m": float(elevation_proxy),
                    "drainage_capacity_index": float(drainage_index),
                }
            ]
        )

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


def predict_risk(lat: float, lng: float, rain_rate: float, discharge: float) -> dict:
    return _predictor.predict_risk(lat, lng, rain_rate, discharge)
