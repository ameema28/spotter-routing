import math

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import HeatmapRequestSerializer, RoutePlanRequestSerializer
from routing.services.errors import (
    PlaceNotFound,
    ProviderBusy,
    ProviderError,
    ProviderTimeout,
    RouteNotFound,
)
from routing.services.route_plan import build_heatmap_levels, build_route_plan
from routing.throttles import (
    HeatmapDayThrottle,
    HeatmapMinuteThrottle,
    RoutePlanDayThrottle,
    RoutePlanMinuteThrottle,
)

# Most specific first: every entry is a ProviderError.
ERROR_STATUS = (
    (PlaceNotFound, 422),
    (RouteNotFound, 422),
    (ProviderBusy, 503),
    (ProviderTimeout, 504),
    (ProviderError, 502),
)


def _error_response(error: ProviderError) -> Response:
    status = next(code for kind, code in ERROR_STATUS if isinstance(error, kind))
    body = {'error': str(error)}
    # Lets the form show "not found" under the right input.
    if getattr(error, 'field', None):
        body['field'] = error.field
    response = Response(body, status=status)
    if getattr(error, 'retry_after', None):
        response['Retry-After'] = error.retry_after
    return response


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})


class ProviderView(APIView):
    """A public tool that spends provider quota: no accounts, so no session or CSRF handling."""
    authentication_classes = []
    permission_classes = []
    throttled_message = ''

    def handle_exception(self, exc):
        # Same {'error': ...} shape as the other failures, so the frontend handles them one way.
        if isinstance(exc, Throttled):
            response = Response({'error': self.throttled_message}, status=429)
            if exc.wait:
                response['Retry-After'] = str(math.ceil(exc.wait))
            return response
        return super().handle_exception(exc)

    def run(self, serializer_class, build):
        serializer = serializer_class(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(build(serializer.validated_data))
        except ProviderError as error:
            return _error_response(error)


class RoutePlanView(ProviderView):
    """Compare routes for a trip. The response is documented on build_route_plan."""
    throttle_classes = [RoutePlanMinuteThrottle, RoutePlanDayThrottle]
    throttled_message = 'Too many searches — please wait a minute and try again'

    def post(self, request):
        return self.run(RoutePlanRequestSerializer, lambda data: build_route_plan(**data))


class HeatmapView(ProviderView):
    """Retry the weather for a route plan's heatmap grid. Documented on build_heatmap_levels."""
    throttle_classes = [HeatmapMinuteThrottle, HeatmapDayThrottle]
    throttled_message = 'Too many heatmap retries — please wait a minute and try again'

    def post(self, request):
        # step_deg is only checked: the points already say where each cell is.
        return self.run(HeatmapRequestSerializer, lambda data: build_heatmap_levels(
            data['points'], data['departure'], data['load_lb']))
