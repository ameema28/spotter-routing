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

    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(build_route_plan(**serializer.validated_data))
        except ProviderError as error:
            return _error_response(error)
