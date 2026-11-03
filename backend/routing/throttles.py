"""Per-client limits on route searches and heatmap retries, which spend Mapbox and Open-Meteo quota."""
from rest_framework.throttling import AnonRateThrottle


class RoutePlanMinuteThrottle(AnonRateThrottle):
    scope = 'route_plan_minute'
    rate = '10/minute'


class RoutePlanDayThrottle(AnonRateThrottle):
    scope = 'route_plan_day'
    rate = '100/day'


# Own scopes, so a heatmap retry doesn't use up one of the client's searches.
class HeatmapMinuteThrottle(AnonRateThrottle):
    scope = 'heatmap_minute'
    rate = '10/minute'


class HeatmapDayThrottle(AnonRateThrottle):
    scope = 'heatmap_day'
    rate = '100/day'
