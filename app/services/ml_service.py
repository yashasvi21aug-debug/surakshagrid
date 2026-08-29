import json
import os
import xgboost as xgb
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models")
XGB_INUNDATION_PATH = os.path.join(MODEL_DIR, "inundation_xgb.json")
XGB_DEPTH_PATH = os.path.join(MODEL_DIR, "depth_xgb.json")

class HydrologicalPredictor:
    def __init__(self):
        self.inundation_model = None
        self.depth_model = None
        self._load_models()

    def _load_models(self):
        if os.path.exists(XGB_INUNDATION_PATH):
            self.inundation_model = xgb.Booster()
            self.inundation_model.load_model(XGB_INUNDATION_PATH)
        if os.path.exists(XGB_DEPTH_PATH):
            self.depth_model = xgb.Booster()
            self.depth_model.load_model(XGB_DEPTH_PATH)

    def predict_basin_risk(self, precipitation_mm: float, river_discharge_m3s: float, soil_saturation_pct: float):
        """
        PRD FR-3.1 & FR-3.2: 6-12 hr inundation probability and depth estimation.
        """
        features = np.array([[precipitation_mm, river_discharge_m3s, soil_saturation_pct]], dtype=np.float32)
        dmatrix = xgb.DMatrix(features)

        # Inundation risk probability
        prob = float(self.inundation_model.predict(dmatrix)[0]) if self.inundation_model else (precipitation_mm * 0.08)
        prob = min(max(prob, 0.0), 1.0)

        # Depth rise estimate (meters)
        depth = float(self.depth_model.predict(dmatrix)[0]) if self.depth_model else (precipitation_mm * 0.02)

        return {
            "inundation_probability": round(prob, 4),
            "estimated_water_rise_m": round(depth, 2),
            "passable_for_vehicles": depth < 0.30,  # Impassable if water depth > 30cm
            "alert_level": "RED" if prob > 0.70 else ("AMBER" if prob > 0.40 else "GREEN")
        }

hydrology_engine = HydrologicalPredictor()