"""
Forecast aggregator for computing daily summaries from 3-hourly weather periods.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WeatherType:
    """Represents a weather type with occurrence count."""
    name: str
    count: int


class ForecastParser:
    """
    Parse and aggregate 3-hourly weather periods into daily summaries.
    """

    # Time windows for day vs night classification
    DAY_START_HOUR = 6      # 06:00
    DAY_END_HOUR = 22       # 22:00 (night starts)

    def __init__(self):
        """Initialize forecast parser."""
        self.last_parsed_count = 0

    @staticmethod
    def is_daytime(hour: int) -> bool:
        """Check if hour is within daytime window."""
        return ForecastParser.DAY_START_HOUR <= hour < ForecastParser.DAY_END_HOUR

    def aggregate_daily_summary(
        self,
        periods: List[Dict],
        date: datetime
    ) -> Dict:
        """
        Aggregate 3-hourly periods for a specific date into daily summary.

        Args:
            periods: List of period dicts with keys:
                - timestamp: datetime
                - weather_type: str
                - temperature: Optional[int]
                - period_type: str ("day" or "night")
            date: Target date for filtering periods

        Returns:
            Dictionary with keys:
                - date: datetime (normalized to noon)
                - weather_type: str (most common type)
                - day_weather_type: str (most common during day)
                - night_weather_type: str (most common during night)
                - max_temperature: Optional[int]
                - min_temperature: Optional[int]
                - period_count: int (how many 3-hourly periods)
        """
        # Filter periods for this date
        date_only = date.date()
        day_periods = [
            p for p in periods
            if p.get('timestamp') and p['timestamp'].date() == date_only
        ]

        if not day_periods:
            logger.debug(f"No periods found for {date_only}")
            return {
                'date': date.replace(hour=12, minute=0, second=0),
                'weather_type': 'Unknown',
                'day_weather_type': 'Unknown',
                'night_weather_type': 'Unknown',
                'max_temperature': None,
                'min_temperature': None,
                'period_count': 0,
            }

        # Separate day and night periods
        day_periods_list = [
            p for p in day_periods
            if self.is_daytime(p.get('timestamp').hour)
        ]
        night_periods_list = [
            p for p in day_periods
            if not self.is_daytime(p.get('timestamp').hour)
        ]

        # Extract weather types
        day_weather_type = self._select_weather_type(day_periods_list)
        night_weather_type = self._select_weather_type(night_periods_list)

        # Overall weather type: prefer day if available
        overall_weather_type = (
            day_weather_type if day_weather_type != 'Unknown'
            else night_weather_type
        )

        # Extract temperatures
        all_temps = [
            p.get('temperature')
            for p in day_periods
            if p.get('temperature') is not None
        ]

        max_temp = max(all_temps) if all_temps else None
        min_temp = min(all_temps) if all_temps else None

        self.last_parsed_count = len(day_periods)

        return {
            'date': date.replace(hour=12, minute=0, second=0),
            'weather_type': overall_weather_type,
            'day_weather_type': day_weather_type,
            'night_weather_type': night_weather_type,
            'max_temperature': max_temp,
            'min_temperature': min_temp,
            'period_count': len(day_periods),
        }

    def aggregate_multi_day(self, periods: List[Dict]) -> List[Dict]:
        """
        Aggregate periods into daily summaries for multiple days.

        Args:
            periods: List of all 3-hourly periods with full details

        Returns:
            List of daily summary dicts, one per day
        """
        if not periods:
            return []

        # Group periods by date
        dates_seen = set()
        for period in periods:
            ts = period.get('timestamp')
            if ts:
                dates_seen.add(ts.date())

        # Generate summaries for each date
        summaries = []
        for date_only in sorted(dates_seen):
            # Create datetime for that date
            dt = datetime.combine(date_only, datetime.min.time())
            summary = self.aggregate_daily_summary(periods, dt)
            summaries.append(summary)

        logger.info(
            f"Aggregated {
                len(periods)} periods into {
                len(summaries)} daily summaries")
        return summaries

    def _select_weather_type(self, periods: List[Dict]) -> str:
        """
        Select most common weather type from periods.

        Args:
            periods: List of period dicts

        Returns:
            Most common weather type string, or 'Unknown' if no periods
        """
        if not periods:
            return 'Unknown'

        # Count weather types
        type_counts = {}
        for period in periods:
            wtype = period.get('weather_type', 'Unknown')
            type_counts[wtype] = type_counts.get(wtype, 0) + 1

        # Return most common
        if type_counts:
            most_common = max(type_counts.items(), key=lambda x: x[1])
            return most_common[0]

        return 'Unknown'

    def get_weather_type_distribution(
        self,
        periods: List[Dict]
    ) -> Dict[str, Tuple[int, float]]:
        """
        Get distribution of weather types with counts and percentages.

        Args:
            periods: List of period dicts

        Returns:
            Dictionary mapping weather type to (count, percentage)
        """
        type_counts = {}
        for period in periods:
            wtype = period.get('weather_type', 'Unknown')
            type_counts[wtype] = type_counts.get(wtype, 0) + 1

        total = len(periods)
        distribution = {
            wtype: (count, round(100 * count / total, 1))
            for wtype, count in type_counts.items()
        } if total > 0 else {}

        logger.debug(f"Weather distribution: {distribution}")
        return distribution

    def validate_periods(self, periods: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate period list structure.

        Args:
            periods: List of period dicts

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not isinstance(periods, list):
            errors.append("Periods must be a list")
            return False, errors

        required_keys = {'timestamp', 'weather_type'}

        for i, period in enumerate(periods):
            if not isinstance(period, dict):
                errors.append(f"Period {i} is not a dict")
                continue

            missing = required_keys - set(period.keys())
            if missing:
                errors.append(f"Period {i} missing keys: {missing}")

            if not isinstance(period.get('timestamp'), datetime):
                errors.append(
                    f"Period {i} timestamp is not datetime: "
                    f"{type(period.get('timestamp'))}"
                )

            if not isinstance(period.get('weather_type'), str):
                errors.append(
                    f"Period {i} weather_type is not string: "
                    f"{type(period.get('weather_type'))}"
                )

        return len(errors) == 0, errors
