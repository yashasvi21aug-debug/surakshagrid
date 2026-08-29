from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.schemas import FloodRiskRequest, FloodRiskResponse

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "models"
MODEL_PATH = MODEL_DIR / "inundation_model.joblib"
LEGACY_PIPELINE_PATH = MODEL_DIR / "flood_model_pipeline.joblib"
INUNDATION_XGB_PATH = MODEL_DIR / "inundation_xgb.json"
DEPTH_XGB_PATH = MODEL_DIR / "depth_xgb.json"

DEFAULT_FEATURE_COLUMNS = [
    "elevation",
    "precipitation_rate",
    "soil_saturation",
    "distance_to_drainage",
    "upstream_discharge",
]


class MLInferenceService:
    """Dynamic Machine Learning & Rational Runoff Hydrodynamic Inference Service."""

    def __init__(
        self,
        model_path: str | Path = MODEL_PATH,
        pipeline_path: str | Path | None = None,
    ) -> None:
        self.model_path = Path(pipeline_path or model_path)
        self.is_custom_path = self.model_path != MODEL_PATH
        self.model_bundle: dict[str, Any] | None = None
        self.xgb_classifier: Any | None = None
        self.xgb_regressor: Any | None = None
        self.is_loaded = False
        self._load_pipeline()

    def _load_pipeline(self) -> None:
        """Attempt to load trained XGBoost JSON or serialized joblib model artifacts."""
        # 1. Attempt native XGBoost JSON models if not testing a custom path
        if not self.is_custom_path and INUNDATION_XGB_PATH.is_file() and DEPTH_XGB_PATH.is_file():
            try:
                import xgboost as xgb

                clf = xgb.XGBClassifier()
                clf.load_model(str(INUNDATION_XGB_PATH))
                reg = xgb.XGBRegressor()
                reg.load_model(str(DEPTH_XGB_PATH))

                self.xgb_classifier = clf
                self.xgb_regressor = reg
                self.is_loaded = True
                logger.info("Successfully loaded native XGBoost JSON models from %s and %s", INUNDATION_XGB_PATH, DEPTH_XGB_PATH)
                return
            except Exception as error:
                logger.warning("Failed to load native XGBoost JSON models: %s", error)

        # 2. Fallback to Joblib serialized pipeline if available
        target_path = self.model_path
        if not target_path.is_file() and self.model_path == MODEL_PATH and LEGACY_PIPELINE_PATH.is_file():
            target_path = LEGACY_PIPELINE_PATH

        if target_path and target_path.is_file():
            try:
                self.model_bundle = joblib.load(target_path)
                self.is_loaded = True
                logger.info("Successfully loaded ML model pipeline from %s", target_path)
                return
            except Exception as error:
                logger.warning("Failed to deserialize model pipeline at %s: %s", target_path, error)

        logger.warning(
            "ML model artifacts missing or unreadable. Utilizing deterministic Rational Runoff physical model."
        )
        self.is_loaded = False

    def predict_subcatchment_risk(self, request: FloodRiskRequest) -> FloodRiskResponse:
        """Execute XGBoost hydrological prediction for 6-12 hour subcatchment flood forecasting."""
        return self.predict_flood_risk(request)

    def predict_flood_risk(self, request: FloodRiskRequest) -> FloodRiskResponse:
        """Execute dynamic model inference or physical Rational Runoff hydrodynamic evaluation."""
        if not self.is_loaded:
            self._load_pipeline()

        dist_val = getattr(request, "distance_to_drainage", request.distance_to_waterway)
        features_dict = {
            "elevation": float(request.elevation),
            "precipitation_rate": float(request.precipitation_rate),
            "soil_saturation": float(request.soil_saturation),
            "distance_to_drainage": float(dist_val),
            "upstream_discharge": float(request.upstream_discharge),
        }

        # 1. Native XGBoost JSON inference
        if self.xgb_classifier is not None and self.xgb_regressor is not None:
            try:
                input_array = np.array(
                    [[
                        request.precipitation_rate,
                        request.upstream_discharge,
                        request.soil_saturation,
                        request.elevation,
                        dist_val,
                    ]],
                    dtype=np.float32,
                )

                if hasattr(self.xgb_classifier, "predict_proba"):
                    inundation_prob = float(self.xgb_classifier.predict_proba(input_array)[0, 1])
                else:
                    inundation_prob = float(self.xgb_classifier.predict(input_array)[0])

                water_rise_m = float(self.xgb_regressor.predict(input_array)[0])
                water_rise_m = max(0.0, float(water_rise_m))

                rise_time_h = float(
                    max(0.5, min(24.0, (request.elevation + dist_val / 200.0) / (0.2 * request.precipitation_rate + 1.0)))
                )
                model_source = "xgboost_hydrology_json"
                confidence = 0.98

                should_flag = inundation_prob >= 0.5 or water_rise_m >= 1.5
                severity = (
                    "CRITICAL"
                    if inundation_prob >= 0.75 or water_rise_m >= 2.5
                    else "HIGH"
                    if should_flag
                    else "MODERATE"
                    if inundation_prob >= 0.35
                    else "LOW"
                )

                return FloodRiskResponse(
                    inundation_probability=round(inundation_prob, 4),
                    estimated_water_rise_meters=round(water_rise_m, 3),
                    estimated_rise_time_hours=round(rise_time_h, 1),
                    severity_classification=severity,
                    status=severity,
                    risk_probability=round(inundation_prob, 4),
                    water_rise_meters=round(water_rise_m, 3),
                    should_flag_flood_polygon=should_flag,
                    model_source=model_source,
                    confidence_score=confidence,
                    features_evaluated=features_dict,
                    lat=request.lat,
                    lng=request.lng,
                )
            except Exception as eval_err:
                logger.error("Error during native XGBoost evaluation: %s. Reverting to fallback.", eval_err)

        # 2. Joblib model bundle inference
        if self.is_loaded and self.model_bundle is not None:
            try:
                feature_cols = (
                    self.model_bundle.get("feature_columns", DEFAULT_FEATURE_COLUMNS)
                    if isinstance(self.model_bundle, dict)
                    else DEFAULT_FEATURE_COLUMNS
                )
                row_data: dict[str, float] = {}
                for col in feature_cols:
                    if col in ("distance_to_drainage", "distance_to_waterway"):
                        row_data[col] = float(dist_val)
                    else:
                        row_data[col] = float(getattr(request, col, features_dict.get(col, 0.0)))

                input_array = np.array([[row_data[col] for col in feature_cols]], dtype=np.float32)
                clf = self.model_bundle["classifier"]
                reg = self.model_bundle["regressor"]

                if hasattr(clf, "predict_proba"):
                    inundation_prob = float(clf.predict_proba(input_array)[0, 1])
                else:
                    inundation_prob = float(clf.predict(input_array)[0])

                water_rise_m = float(reg.predict(input_array)[0])
                water_rise_m = max(0.0, float(water_rise_m))

                rise_time_h = float(
                    max(0.5, min(24.0, (request.elevation + dist_val / 200.0) / (0.2 * request.precipitation_rate + 1.0)))
                )
                model_source = "ml_pipeline_joblib"
                confidence = 0.96

                should_flag = inundation_prob >= 0.6 or water_rise_m >= 1.5
                severity = (
                    "CRITICAL"
                    if inundation_prob >= 0.75 or water_rise_m >= 2.5
                    else "HIGH"
                    if should_flag
                    else "MODERATE"
                    if inundation_prob >= 0.35
                    else "LOW"
                )

                return FloodRiskResponse(
                    inundation_probability=round(inundation_prob, 4),
                    estimated_water_rise_meters=round(water_rise_m, 3),
                    estimated_rise_time_hours=round(rise_time_h, 1),
                    severity_classification=severity,
                    status=severity,
                    risk_probability=round(inundation_prob, 4),
                    water_rise_meters=round(water_rise_m, 3),
                    should_flag_flood_polygon=should_flag,
                    model_source=model_source,
                    confidence_score=confidence,
                    features_evaluated=features_dict,
                    lat=request.lat,
                    lng=request.lng,
                )
            except Exception as eval_err:
                logger.error("Error during ML pipeline evaluation: %s. Reverting to fallback.", eval_err)

        # 3. Rational Runoff deterministic physical model fallback
        return self._rational_runoff_fallback(request, features_dict)

    def _rational_runoff_fallback(
        self, request: FloodRiskRequest, features_dict: dict[str, float]
    ) -> FloodRiskResponse:
        """Deterministic physical Rational Runoff hydrodynamic model (Q = C * I * A)."""
        logger.warning(
            "ML model artifacts missing or unreadable. Utilizing deterministic Rational Runoff physical model."
        )
        dist_val = getattr(request, "distance_to_drainage", request.distance_to_waterway)
        c_factor = 0.2 + 0.7 * (request.soil_saturation / 100.0)
        i_intensity = request.precipitation_rate
        elev_factor = max(1.0, request.elevation)
        dist_factor = math.exp(-dist_val / 2500.0)

        q_discharge = (c_factor * i_intensity / (5.0 + 0.1 * elev_factor)) * dist_factor
        inundation_prob = float(1.0 / (1.0 + math.exp(-8.0 * (q_discharge - 0.5))))
        water_rise_m = float(max(0.0, 0.15 + 4.8 * inundation_prob + 0.5 * (request.precipitation_rate / 150.0)))
        rise_time_h = float(
            max(0.5, min(24.0, (request.elevation + dist_val / 200.0) / (0.2 * request.precipitation_rate + 1.0)))
        )

        should_flag = inundation_prob >= 0.6 or water_rise_m >= 1.5
        severity = (
            "CRITICAL"
            if inundation_prob >= 0.75 or water_rise_m >= 2.5
            else "HIGH"
            if should_flag
            else "MODERATE"
            if inundation_prob >= 0.35
            else "LOW"
        )

        return FloodRiskResponse(
            inundation_probability=round(inundation_prob, 4),
            estimated_water_rise_meters=round(water_rise_m, 3),
            estimated_rise_time_hours=round(rise_time_h, 1),
            severity_classification=severity,
            status=severity,
            risk_probability=round(inundation_prob, 4),
            water_rise_meters=round(water_rise_m, 3),
            should_flag_flood_polygon=should_flag,
            model_source="rational_runoff_hydrodynamic_fallback",
            confidence_score=0.86,
            features_evaluated=features_dict,
            lat=request.lat,
            lng=request.lng,
        )


ml_service = MLInferenceService()
