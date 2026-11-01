import pytest


@pytest.fixture(autouse=True)
def isolated_cache(settings, tmp_path):
    """Run on the real backend, but never touch the developer's cached weather."""
    settings.CACHES = {'default': {**settings.CACHES['default'], 'LOCATION': str(tmp_path / 'cache')}}
