import math

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import RoutePlanRequestSerializer
from routing.services.errors import (
    PlaceNotFound,
    ProviderBusy,
    ProviderError,
    ProviderTimeout,
    RouteNotFound,
)
from routing.services.route_plan import build_route_plan
from routing.throttles import RoutePlanDayThrottle, RoutePlanMinuteThrottle

# Most specific first: every entry is a ProviderError.
ERROR_STATUS = (
    (PlaceNotFound, 422),
    (RouteNotFound, 422),
    (ProviderBusy, 503),
    (ProviderTimeout, 504),
    (ProviderError, 502),
)
THROTTLED_MESSAGE = 'Too many searches — please wait a minute and try again'


def _error_response(error: ProviderError) -> Response:
    status = next(code for kind, code in ERROR_STATUS if isinstance(error, kind))
    response = Response({'error': str(error)}, status=status)
    if getattr(error, 'retry_after', None):
        response['Retry-After'] = error.retry_after
    return response


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})


class RoutePlanView(APIView):
    """Compare routes for a trip. The response is documented on build_route_plan."""
    # A public read-only tool: no accounts, so no session or CSRF handling.
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RoutePlanMinuteThrottle, RoutePlanDayThrottle]

    def handle_exception(self, exc):
        # Same {'error': ...} shape as the other failures, so the frontend handles them one way.
        if isinstance(exc, Throttled):
            response = Response({'error': THROTTLED_MESSAGE}, status=429)
            if exc.wait:
                response['Retry-After'] = str(math.ceil(exc.wait))
            return response
        return super().handle_exception(exc)

    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(build_route_plan(**serializer.validated_data))
        except ProviderError as error:
            return _error_response(error)
