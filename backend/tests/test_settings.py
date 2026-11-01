import runpy
from pathlib import Path

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


def test_cache_is_file_based_so_workers_and_restarts_share_it():
    cache = load_settings()['CACHES']['default']
    assert cache['BACKEND'].endswith('FileBasedCache')
    assert Path(cache['LOCATION']).is_relative_to(django_settings.BASE_DIR)


def test_blank_debug_is_off(monkeypatch):
    monkeypatch.setenv('DEBUG', '')
    assert load_settings()['DEBUG'] is False


def test_blank_allowed_hosts_is_empty(monkeypatch):
    monkeypatch.setenv('ALLOWED_HOSTS', '')
    assert load_settings()['ALLOWED_HOSTS'] == []
