"""
Met Office DataPoint API adapter for weather forecast fetching.
Handles 3-hourly forecast periods and daily aggregation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class WeatherPeriod:
    """Single 3-hourly weather period from Met Office."""
    timestamp: datetime
    weather_type: str          # e.g., "Partly cloudy", "Heavy rain"
    temperature: Optional[int] = None
    wind_speed: Optional[int] = None
    period_type: str = "unspecified"  # "day" or "night"


@dataclass
class DailySummary:
    """Aggregated daily weather data."""
    date: datetime
    weather_type: str          # Most common weather type for the day
    max_temperature: Optional[int] = None
    min_temperature: Optional[int] = None
    periods: List[WeatherPeriod] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "weather_type": self.weather_type,
            "max_temperature": self.max_temperature,
            "min_temperature": self.min_temperature,
            "period_count": len(self.periods),
        }


class MetOfficeAdapter:
    """
    Adapter for Met Office DataPoint API.

    Fetches 3-hourly forecasts and aggregates to daily summaries.
    """

    # Default endpoint (UK Met Office free tier, point forecast)
    DEFAULT_BASE_URL = "https://www.metoffice.gov.uk/services/data/datapoint"
    DEFAULT_RESOURCE = "forecast_3hourly"  # Available forecasting resource

    def __init__(
        self,
        api_key: str,
        latitude: float,
        longitude: float,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = 10,
    ):
        """
        Initialize Met Office adapter.

        Args:
            api_key: Met Office API key
            latitude: Site latitude
            longitude: Site longitude
            base_url: API base URL
            timeout_seconds: HTTP request timeout
        """
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.last_fetch_at = None
        self.last_forecast = None

    def fetch_forecast(self) -> Optional[List[DailySummary]]:
        """
        Fetch and parse forecast from Met Office.

        Returns:
            List of DailySummary objects, or None on error
        """
        try:
            url = f"{self.base_url}/{self.DEFAULT_RESOURCE}/point/{self.latitude},{self.longitude}"
            params = {
                "key": self.api_key,
                "res": "daily",  # Request daily aggregation if available
            }

            logger.info(f"Fetching forecast from {url}")
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout_seconds
            )
            response.raise_for_status()

            data = response.json()
            self.last_fetch_at = datetime.now()

            summaries = self._parse_forecast(data)
            self.last_forecast = summaries
            logger.info(f"Fetched {len(summaries)} days of forecast")

            return summaries

        except requests.exceptions.RequestException as e:
            logger.error(f"Met Office API error: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse Met Office response: {e}")
            return None

    def _parse_forecast(self, data: Dict[str, Any]) -> List[DailySummary]:
        """
        Parse raw Met Office response into daily summaries.

        Expected structure (3-hourly):
        {
            "SiteRep": {
                "Wx": {
                    "Type": "Day",
                    "Param": [...]
                },
                "DV": {
                    "dataDate": "2024-01-15T...",
                    "type": "3hourly",
                    "Location": {
                        "period": [
                            {
                                "$": "2024-01-15Z",
                                "Rep": "0,1,3,..."
                            },
                            ...
                        ]
                    }
                }
            }
        }

        Args:
            data: Parsed JSON response

        Returns:
            List of DailySummary objects
        """
        try:
            summaries = {}  # date -> DailySummary

            # Navigate to periods
            site_rep = data.get("SiteRep", {})
            dv = site_rep.get("DV", {})
            location = dv.get("Location", {})
            periods = location.get("period", [])

            # Map weather codes to readable types
            wx_type_map = self._get_weather_type_map(site_rep)

            for period_data in periods:
                period_date_str = period_data.get("$", "")
                period_date = self._parse_date(period_date_str)

                if not period_date:
                    continue

                # Get date-only key
                date_key = period_date.date()

                if date_key not in summaries:
                    summaries[date_key] = DailySummary(
                        date=period_date.replace(hour=12, minute=0, second=0),
                        weather_type="Unknown"
                    )

                # Parse reports (each rep is a time period within the day)
                rep_values = period_data.get("Rep", "").split(',')
                period = self._parse_rep_values(
                    rep_values,
                    period_date,
                    wx_type_map
                )

                if period:
                    summaries[date_key].periods.append(period)

            # Aggregate daily summaries
            result = []
            for date_key in sorted(summaries.keys()):
                summary = summaries[date_key]
                summary.weather_type = self._select_weather_type(
                    summary.periods)
                summary.max_temperature = self._get_max_temperature(
                    summary.periods)
                summary.min_temperature = self._get_min_temperature(
                    summary.periods)
                result.append(summary)

            return result

        except Exception as e:
            logger.error(f"Forecast parsing error: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO date string from Met Office."""
        try:
            # Handle formats like "2024-01-15Z" or "2024-01-15T12:00:00Z"
            if date_str.endswith('Z'):
                date_str = date_str[:-1]

            if 'T' in date_str:
                return datetime.fromisoformat(date_str)
            else:
                return datetime.fromisoformat(date_str)
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None

    def _get_weather_type_map(
            self, site_rep: Dict[str, Any]) -> Dict[int, str]:
        """Build map of weather code to readable type."""
        wx_map = {}

        try:
            wx = site_rep.get("Wx", {})
            params = wx.get("Param", [])

            for param in params:
                if param.get("name") == "WeatherType":
                    desc = param.get("desc", "")
                    code = param.get("$", "")
                    try:
                        wx_map[int(code)] = desc
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.debug(f"Weather type map parse error: {e}")

        # Fallback mappings for common codes if parsing fails
        if not wx_map:
            wx_map = {
                0: "Clear",
                1: "Partly cloudy",
                2: "Partly cloudy",
                3: "Mostly cloudy",
                4: "Overcast",
                5: "Overcast",
                6: "Mist",
                7: "Fog",
                8: "Drizzle",
                9: "Light rain",
                10: "Rain",
                11: "Heavy rain",
                12: "Hail",
                13: "Sleet",
                14: "Snow",
                15: "Heavy snow",
                16: "Thunderstorm",
                17: "Thunderstorm with hail",
                18: "Thunderstorm with snow",
                19: "Hail",
            }

        return wx_map

    def _parse_rep_values(
        self,
        rep_values: List[str],
        period_date: datetime,
        wx_type_map: Dict[int, str]
    ) -> Optional[WeatherPeriod]:
        """
        Parse report values (comma-separated parameter values).
        Format: "0,10,2.5,270,5,1008,15,2"
        Indices: [wind_direction°, wind_speed, temp, wind_direction, ?, pressure, ?, weather_type]
        """
        try:
            # Weather type is typically index 7, but varies by API version
            # For now, use index -1 (last value) or assume index varies
            if len(rep_values) >= 1:
                weather_code = int(rep_values[-1].strip())
                weather_type = wx_type_map.get(
                    weather_code, f"WeatherCode({weather_code})")
            else:
                weather_type = "Unknown"

            # Temperature typically at index 2
            temperature = None
            if len(rep_values) >= 3:
                try:
                    temperature = int(float(rep_values[2].strip()))
                except (ValueError, IndexError):
                    pass

            # Determine day/night based on hour
            hour = period_date.hour
            period_type = "day" if 6 <= hour < 22 else "night"

            return WeatherPeriod(
                timestamp=period_date,
                weather_type=weather_type,
                temperature=temperature,
                period_type=period_type
            )

        except Exception as e:
            logger.debug(f"Rep parse error: {e}")
            return None

    def _select_weather_type(self, periods: List[WeatherPeriod]) -> str:
        """
        Select most common weather type for the day.
        Prioritize day periods over night periods.
        """
        if not periods:
            return "Unknown"

        # Count weather types by frequency
        day_types = {}
        night_types = {}

        for period in periods:
            type_map = day_types if period.period_type == "day" else night_types
            type_map[period.weather_type] = type_map.get(
                period.weather_type, 0) + 1

        # Prefer day period weather type
        if day_types:
            most_common = max(day_types.items(), key=lambda x: x[1])
            return most_common[0]
        elif night_types:
            most_common = max(night_types.items(), key=lambda x: x[1])
            return most_common[0]

        return periods[0].weather_type

    def _get_max_temperature(
            self,
            periods: List[WeatherPeriod]) -> Optional[int]:
        """Get maximum temperature from periods."""
        temps = [p.temperature for p in periods if p.temperature is not None]
        return max(temps) if temps else None

    def _get_min_temperature(
            self,
            periods: List[WeatherPeriod]) -> Optional[int]:
        """Get minimum temperature from periods."""
        temps = [p.temperature for p in periods if p.temperature is not None]
        return min(temps) if temps else None

    def get_last_forecast(self) -> Optional[List[DailySummary]]:
        """Get cached forecast from last fetch."""
        return self.last_forecast

    def time_since_last_fetch(self) -> Optional[timedelta]:
        """Get time elapsed since last successful fetch."""
        if self.last_fetch_at:
            return datetime.now() - self.last_fetch_at
        return None
