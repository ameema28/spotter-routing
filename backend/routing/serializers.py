from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from routing.domain.geometry import GRID_STEPS
from routing.services.route_plan import HEATMAP_MAX_POINTS

MAX_LOAD_LB = 80_000
EARLIEST_DEPARTURE = timedelta(hours=1)
LATEST_DEPARTURE = timedelta(days=7)


class AwareDateTimeField(serializers.DateTimeField):
    """ISO 8601 with a timezone: a time without one could be hours off for the driver."""
    default_error_messages = {'naive': 'Include a timezone, for example 2026-11-02T08:00:00-06:00.'}

    def enforce_timezone(self, value):
        if timezone.is_naive(value):
            self.fail('naive')
        return super().enforce_timezone(value)


class TripSerializer(serializers.Serializer):
    """The fields a search and a heatmap retry share, with the same rules."""
    departure = AwareDateTimeField()
    load_lb = serializers.FloatField(max_value=MAX_LOAD_LB)

    def validate_load_lb(self, value):
        if value <= 0:
            raise serializers.ValidationError('Load must be more than 0 lb.')
        return value

    def validate_departure(self, value):
        now = timezone.now()
        if not now - EARLIEST_DEPARTURE <= value <= now + LATEST_DEPARTURE:
            raise serializers.ValidationError('Departure must be between 1 hour ago and 7 days from now.')
        return value


class RoutePlanRequestSerializer(TripSerializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    step_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)


def _pair():
    return serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2)


def _on_grid(value: float, step: float) -> bool:
    # Grid points are sent rounded to 2 decimals, as route-plan builds them.
    return abs(round(round(value / step) * step, 2) - value) < 1e-9


class HeatmapRequestSerializer(TripSerializer):
    """A grid from a route-plan response, sent back to retry its weather."""
    points = serializers.ListField(child=_pair(), min_length=1, max_length=HEATMAP_MAX_POINTS)
    step_deg = _pair()

    def validate_step_deg(self, value):
        if tuple(value) not in GRID_STEPS:
            raise serializers.ValidationError('Use the step_deg from the route-plan response.')
        return value

    def validate(self, data):
        # Only points on the fixed grid: arbitrary points would spend weather quota no search asked for.
        lat_step, lon_step = data['step_deg']
        for lat, lon in data['points']:
            in_range = -90 <= lat <= 90 and -180 <= lon <= 180
            if not (in_range and _on_grid(lat, lat_step) and _on_grid(lon, lon_step)):
                raise serializers.ValidationError({'points': 'Use the points from the route-plan response.'})
        return data
