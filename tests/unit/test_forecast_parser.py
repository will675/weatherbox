"""
Unit tests for forecast parser module.
Tests aggregation logic, day/night weather type selection, and temperature extraction.
"""

import pytest
from datetime import datetime

from weatherbox.weather.forecast_parser import ForecastParser


class TestForecastParser:
    """Test ForecastParser aggregation logic."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return ForecastParser()

    @pytest.fixture
    def sample_periods(self):
        """Sample 3-hourly weather periods for testing."""
        return [
            {
                'timestamp': datetime(2024, 1, 15, 6, 0),   # 06:00 - day
                'weather_type': 'Clear',
                'temperature': 5,
                'period_type': 'day',
            },
            {
                'timestamp': datetime(2024, 1, 15, 9, 0),   # 09:00 - day
                'weather_type': 'Partly cloudy',
                'temperature': 8,
                'period_type': 'day',
            },
            {
                'timestamp': datetime(2024, 1, 15, 12, 0),  # 12:00 - day
                'weather_type': 'Clear',
                'temperature': 12,
                'period_type': 'day',
            },
            {
                'timestamp': datetime(2024, 1, 15, 15, 0),  # 15:00 - day
                'weather_type': 'Clear',
                'temperature': 10,
                'period_type': 'day',
            },
            {
                'timestamp': datetime(2024, 1, 15, 23, 0),  # 23:00 - night
                'weather_type': 'Overcast',
                'temperature': 3,
                'period_type': 'night',
            },
            {
                'timestamp': datetime(2024, 1, 16, 0, 0),   # 00:00 - night
                'weather_type': 'Overcast',
                'temperature': 2,
                'period_type': 'night',
            },
        ]

    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser.last_parsed_count == 0
        assert parser.DAY_START_HOUR == 6
        assert parser.DAY_END_HOUR == 22

    def test_is_daytime(self, parser):
        """Test daytime classification."""
        assert parser.is_daytime(6) is True    # Start hour
        assert parser.is_daytime(12) is True   # Midday
        assert parser.is_daytime(21) is True   # Before end
        assert parser.is_daytime(22) is False  # End hour (night)
        assert parser.is_daytime(23) is False  # Night
        assert parser.is_daytime(0) is False   # Midnight
        assert parser.is_daytime(5) is False   # Early morning

    def test_aggregate_daily_summary_single_day(self, parser, sample_periods):
        """Test aggregating periods from single day."""
        target_date = datetime(2024, 1, 15)

        summary = parser.aggregate_daily_summary(sample_periods, target_date)

        assert summary['date'].date() == target_date.date()
        assert summary['period_count'] == 5  # 4 day + 1 night on this day
        assert summary['max_temperature'] == 12
        # Night period on Jan 15 at 23:00 has temp 3
        assert summary['min_temperature'] == 3
        assert summary['day_weather_type'] == 'Clear'  # Most common in day
        assert summary['night_weather_type'] == 'Overcast'

    def test_aggregate_daily_summary_prefers_day_weather(
            self, parser, sample_periods):
        """Test that overall weather type prefers day periods."""
        target_date = datetime(2024, 1, 15)
        summary = parser.aggregate_daily_summary(sample_periods, target_date)

        # Overall should be 'Clear' (day) not 'Overcast' (night)
        assert summary['weather_type'] == 'Clear'

    def test_aggregate_daily_summary_no_periods(self, parser):
        """Test aggregation with no periods."""
        summary = parser.aggregate_daily_summary([], datetime(2024, 1, 15))

        assert summary['weather_type'] == 'Unknown'
        assert summary['period_count'] == 0
        assert summary['max_temperature'] is None
        assert summary['min_temperature'] is None

    def test_aggregate_multi_day(self, parser):
        """Test aggregating periods from multiple days."""
        periods = [
            {
                'timestamp': datetime(2024, 1, 15, 12, 0),
                'weather_type': 'Clear',
                'temperature': 10,
            },
            {
                'timestamp': datetime(2024, 1, 16, 12, 0),
                'weather_type': 'Rainy',
                'temperature': 8,
            },
            {
                'timestamp': datetime(2024, 1, 17, 12, 0),
                'weather_type': 'Overcast',
                'temperature': 6,
            },
        ]

        summaries = parser.aggregate_multi_day(periods)

        assert len(summaries) == 3
        assert summaries[0]['date'].date() == datetime(2024, 1, 15).date()
        assert summaries[1]['date'].date() == datetime(2024, 1, 16).date()
        assert summaries[2]['date'].date() == datetime(2024, 1, 17).date()

    def test_weather_type_distribution(self, parser, sample_periods):
        """Test weather type distribution calculation."""
        distribution = parser.get_weather_type_distribution(sample_periods)

        assert 'Clear' in distribution
        assert distribution['Clear'] == (3, 50.0)  # 3 out of 6 = 50%
        assert distribution['Partly cloudy'] == (1, 16.7)
        assert distribution['Overcast'] == (2, 33.3)

    def test_validate_periods_valid(self, parser, sample_periods):
        """Test validation of valid periods."""
        is_valid, errors = parser.validate_periods(sample_periods)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_periods_missing_timestamp(self, parser):
        """Test validation catches missing timestamp."""
        periods = [
            {
                'weather_type': 'Clear',
                'temperature': 10,
            }
        ]

        is_valid, errors = parser.validate_periods(periods)

        assert is_valid is False
        assert any('timestamp' in e for e in errors)

    def test_validate_periods_invalid_weather_type(self, parser):
        """Test validation catches non-string weather type."""
        periods = [
            {
                'timestamp': datetime.now(),
                'weather_type': 123,  # Should be string
            }
        ]

        is_valid, errors = parser.validate_periods(periods)

        assert is_valid is False
        assert any('weather_type' in e for e in errors)

    def test_validate_periods_not_list(self, parser):
        """Test validation catches non-list input."""
        is_valid, errors = parser.validate_periods({'weather_type': 'Clear'})

        assert is_valid is False
        assert any('list' in e.lower() for e in errors)

    def test_select_weather_type_empty(self, parser):
        """Test weather type selection with empty periods."""
        weather_type = parser._select_weather_type([])
        assert weather_type == 'Unknown'

    def test_select_weather_type_highest_frequency(self, parser):
        """Test weather type selection chooses most common."""
        periods = [
            {'weather_type': 'Clear'},
            {'weather_type': 'Clear'},
            {'weather_type': 'Clear'},
            {'weather_type': 'Rainy'},
            {'weather_type': 'Rainy'},
        ]

        weather_type = parser._select_weather_type(periods)
        assert weather_type == 'Clear'  # 3 out of 5

    def test_last_parsed_count(self, parser, sample_periods):
        """Test that parser tracks period count."""
        target_date = datetime(2024, 1, 15)
        parser.aggregate_daily_summary(sample_periods, target_date)

        assert parser.last_parsed_count == 5
