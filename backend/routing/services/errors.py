class ProviderError(Exception):
    """A third-party API failed. The message is safe to show: it never holds a URL or token."""


class ProviderTimeout(ProviderError):
    """A third-party API took too long."""


class PlaceNotFound(ProviderError):
    """Geocoding found no match for what the user typed. field says which input: origin or destination."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class RouteNotFound(ProviderError):
    """No drivable route exists between the two places."""


class ProviderBusy(ProviderError):
    """The weather provider's rate limit was reached."""

    def __init__(self, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.retry_after = retry_after
