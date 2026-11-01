import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def memory_cache(settings):
    """Fast, and never touches the developer's cached weather. Cleared so throttle counts don't leak."""
    settings.CACHES = {'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'tests',
        'OPTIONS': settings.CACHES['default']['OPTIONS'],
    }}
    cache.clear()


@pytest.fixture
def file_cache(settings, tmp_path):
    """The production backend, for the tests that depend on it."""
    settings.CACHES = {'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(tmp_path / 'cache'),
        'OPTIONS': settings.CACHES['default']['OPTIONS'],
    }}
