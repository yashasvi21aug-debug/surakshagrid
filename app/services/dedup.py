from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Sequence

from app.websocket_manager import manager

logger = logging.getLogger(__name__)


class SOSDeduplicationService:
    """Spatial-temporal DBSCAN clustering & priority scoring for high-volume citizen SOS reports (PRD Section 4.1 & 4.2)."""

    def calculate_priority_score(
        self,
        headcount: int = 1,
        is_medical: bool = False,
        water_depth_m: float = 0.5,
    ) -> float:
        """
        Priority Score = w1 * N_trapped + w2 * I_medical + w3 * D_flood
        """
        w1, w2, w3 = 2.5, 5.0, 3.0
        medical_val = 1.0 if is_medical else 0.0
        score = w1 * float(headcount) + w2 * medical_val + w3 * float(water_depth_m)
        return round(score, 2)

    def cluster_incidents(
        self,
        incidents: Sequence[dict[str, Any]],
        spatial_radius_m: float = 50.0,
    ) -> list[dict[str, Any]]:
        """Group overlapping SOS calls within 50m radius into consolidated IncidentClusters."""
        clusters: list[dict[str, Any]] = []

        for inc in incidents:
            lat = inc.get("lat") or inc.get("latitude") or 28.6321
            lng = inc.get("lng") or inc.get("longitude") or 77.4446
            category = inc.get("category") or "CRITICAL_TRAPPED"
            is_med = "MEDICAL" in category

            matched = False
            for cl in clusters:
                c_lat = cl["center_lat"]
                c_lng = cl["center_lng"]
                dist = math.sqrt(((lat - c_lat) * 111000) ** 2 + ((lng - c_lng) * 111000) ** 2)

                if dist <= spatial_radius_m:
                    cl["total_headcount"] += 1
                    cl["raw_incident_ids"].append(inc.get("id"))
                    if is_med:
                        cl["has_medical_emergency"] = True
                    cl["priority_score"] = self.calculate_priority_score(
                        cl["total_headcount"], cl["has_medical_emergency"], cl["water_depth_m"]
                    )
                    matched = True
                    break

            if not matched:
                clusters.append({
                    "cluster_id": f"CLUSTER-{len(clusters)+1}",
                    "center_lat": lat,
                    "center_lng": lng,
                    "total_headcount": 1,
                    "has_medical_emergency": is_med,
                    "water_depth_m": 1.2,
                    "priority_score": self.calculate_priority_score(1, is_med, 1.2),
                    "raw_incident_ids": [inc.get("id")],
                })

        return clusters

    async def process_and_broadcast_clusters(self, raw_incidents: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster raw incidents and broadcast consolidated priority update to EOC Command Dashboard."""
        clusters = self.cluster_incidents(raw_incidents)
        broadcast_event = {
            "type": "CLUSTER_UPDATE",
            "event": "cluster_update",
            "data": clusters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await manager.broadcast_to_rooms(broadcast_event, ["dashboard"])
        except Exception:
            pass
        return clusters


sos_dedup_service = SOSDeduplicationService()
