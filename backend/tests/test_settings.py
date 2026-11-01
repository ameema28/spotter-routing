import runpy
from pathlib import Path

import pytest
from django.conf import settings as django_settings

SETTINGS_FILE = Path(django_settings.BASE_DIR) / 'config' / 'settings.py'


def load_settings():
    # run_path gives a fresh read of the environment without touching the live settings object.
    return runpy.run_path(str(SETTINGS_FILE))


def test_blank_secret_key_uses_the_fallback(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', '')
    assert load_settings()['SECRET_KEY']


def test_set_secret_key_is_used(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'from-the-environment')
    assert load_settings()['SECRET_KEY'] == 'from-the-environment'


def test_cache_is_file_based_so_workers_and_restarts_share_it(monkeypatch):
    monkeypatch.delenv('CACHE_DIR', raising=False)
    cache = load_settings()['CACHES']['default']
    assert cache['BACKEND'].endswith('FileBasedCache')
    assert Path(cache['LOCATION']).is_relative_to(django_settings.BASE_DIR)


def test_cache_holds_more_than_a_large_comparison():
    assert load_settings()['CACHES']['default']['OPTIONS']['MAX_ENTRIES'] >= 400


def test_cache_dir_comes_from_the_environment(monkeypatch):
    # Vercel's filesystem is read-only outside /tmp.
    monkeypatch.setenv('CACHE_DIR', '/tmp/spotter-cache')
    assert load_settings()['CACHES']['default']['LOCATION'] == '/tmp/spotter-cache'


def test_blank_cache_dir_falls_back(monkeypatch):
    monkeypatch.setenv('CACHE_DIR', '')
    assert load_settings()['CACHES']['default']['LOCATION']


@pytest.mark.parametrize('name', ['ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'CORS_ALLOWED_ORIGINS'])
def test_comma_lists_come_from_the_environment(monkeypatch, name):
    monkeypatch.setenv(name, 'https://a.example, https://b.example,')
    assert load_settings()[name] == ['https://a.example', 'https://b.example']


def test_cors_defaults_to_the_local_dev_server(monkeypatch):
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS', '')
    assert load_settings()['CORS_ALLOWED_ORIGINS'] == ['http://localhost:5173']


def test_csrf_origins_default_to_none(monkeypatch):
    monkeypatch.setenv('CSRF_TRUSTED_ORIGINS', '')
    assert load_settings()['CSRF_TRUSTED_ORIGINS'] == []


def test_https_is_trusted_from_the_proxy_only_in_production(monkeypatch):
    monkeypatch.setenv('DEBUG', 'False')
    assert load_settings()['SECURE_PROXY_SSL_HEADER'] == ('HTTP_X_FORWARDED_PROTO', 'https')
    monkeypatch.setenv('DEBUG', 'True')
    assert load_settings()['SECURE_PROXY_SSL_HEADER'] is None


def test_whitenoise_follows_security_middleware():
    middleware = load_settings()['MIDDLEWARE']
    assert middleware.index('whitenoise.middleware.WhiteNoiseMiddleware') == 1


def test_static_root_is_set_for_collectstatic():
    assert load_settings()['STATIC_ROOT']


def test_client_ip_is_taken_from_the_one_proxy_in_front():
    assert load_settings()['REST_FRAMEWORK']['NUM_PROXIES'] == 1


def test_blank_debug_is_off(monkeypatch):
    monkeypatch.setenv('DEBUG', '')
    assert load_settings()['DEBUG'] is False


def test_blank_allowed_hosts_is_empty(monkeypatch):
    monkeypatch.setenv('ALLOWED_HOSTS', '')
    assert load_settings()['ALLOWED_HOSTS'] == []
