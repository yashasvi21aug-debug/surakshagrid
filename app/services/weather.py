import httpx
from typing import Dict, Any

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_live_weather(lat: float = 28.6321, lng: float = 77.4446) -> Dict[str, Any]:
    """Fetch real-time weather & precipitation for the river basin coordinates."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": ["precipitation", "rain", "showers", "cloud_cover", "wind_speed_10m"],
        "hourly": "precipitation_probability",
        "timezone": "auto"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "latitude": lat,
                "longitude": lng,
                "precipitation_rate_mm": current.get("precipitation", 0.0),
                "rain_mm": current.get("rain", 0.0),
                "wind_speed_kmh": current.get("wind_speed_10m", 0.0),
                "cloud_cover": current.get("cloud_cover", 0),
                "source": "Open-Meteo Real-Time Telemetry"
            }
        return {"precipitation_rate_mm": 0.0, "source": "Fallback"}