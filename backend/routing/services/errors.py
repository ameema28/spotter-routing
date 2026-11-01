class ProviderError(Exception):
    """A third-party API failed. The message is safe to show: it never holds a URL or token."""
