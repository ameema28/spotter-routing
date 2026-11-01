"""Per-client limits on route searches, which spend Mapbox and Open-Meteo quota."""
from rest_framework.throttling import AnonRateThrottle


class RoutePlanMinuteThrottle(AnonRateThrottle):
    scope = 'route_plan_minute'
    rate = '10/minute'


class RoutePlanDayThrottle(AnonRateThrottle):
    scope = 'route_plan_day'
    rate = '100/day'
