from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

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


class RoutePlanRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    departure = AwareDateTimeField()
    load_lb = serializers.FloatField(max_value=MAX_LOAD_LB)
    step_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_load_lb(self, value):
        if value <= 0:
            raise serializers.ValidationError('Load must be more than 0 lb.')
        return value

    def validate_departure(self, value):
        now = timezone.now()
        if not now - EARLIEST_DEPARTURE <= value <= now + LATEST_DEPARTURE:
            raise serializers.ValidationError('Departure must be between 1 hour ago and 7 days from now.')
        return value
