import httpx
from datetime import datetime, timezone


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(latitude: float, longitude: float):
    if not (-90 <= latitude <= 90):
        raise ValueError("Invalid latitude.")

    if not (-180 <= longitude <= 180):
        raise ValueError("Invalid longitude.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "rain,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "timezone": "auto",
        "forecast_days": 1,
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(WEATHER_URL, params=params)
        response.raise_for_status()
        data = response.json()

    current = data.get("current", {})

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Severe thunderstorm with hail",
    }

    code = current.get("weather_code")

    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "rain_mm": current.get("rain", 0),
        "precipitation_mm": current.get("precipitation", 0),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "condition": weather_codes.get(code, "Conditions unavailable"),
        "weather_code": code,
        "observed_at": current.get("time"),
        "timezone": data.get("timezone", "auto"),
        "source": "Open-Meteo",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }