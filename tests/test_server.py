import json
from types import SimpleNamespace

import pytest

from server import FlaskServer


class FakeSettings:
    def __init__(self):
        self._settings = {
            'token': 'secret',
            'audio.enabled': True,
            'streaming.launch_streaming_by_endpoint': True,
            'gaming.enabled': True,
            'fan.enabled': True,
            'fan.apply_on_stream_launch': False,
            'fan.apply_on_game_launch': False,
            'host': '127.0.0.1',
            'port': 1482
        }

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def get_audio_mappings(self):
        return [
            {'label': 'game', 'device_id': 'dev-game', 'is_game': True},
            {'label': 'stream', 'device_id': 'dev-stream', 'use_for_streaming': True}
        ]

    def get_gaming_mappings(self):
        return [
            {'label': 'TestGame', 'steam_appid': '12345', 'exe_path': ''}
        ]


class FakeAudio:
    def set_default_device(self, device_id):
        return True

    def switch_to_device_by_key(self, key, mappings):
        return {"ok": True, "device": key}

    def set_volume(self, percent):
        return True

    def get_audio_snapshot(self, mappings):
        return {
            "ok": True,
            "volume": 42,
            "device_id": "dev-stream",
            "active_key": "stream",
            "matched": True,
            "device_name": "DevStream",
            "name": "Stream"
        }

    def get_current_volume(self):
        return 42

    def get_playback_devices(self):
        return {"ok": True, "devices": [], "total": 0}

    def switch_to_streaming_device(self, mappings):
        return {"ok": True}

    def test_audio_system(self):
        return {"ok": True}


class FakeStreaming:
    def launch_service(self, service):
        return {"ok": True, "service": service}

    def test_browsers(self):
        return {"chrome": {"available": False, "paths": []}, "edge": {"available": False, "paths": []}}


class FakeFan:
    def can_switch_configs(self):
        return True

    def set_fan_profile(self, name):
        return {"ok": True, "applied": name}

    def set_fan_percentage(self, percent):
        return {"ok": True, "percent": percent}

    def refresh_sensors(self):
        return True

    def get_config_summary(self):
        return {"percentage_configs": [{"percentage": 20}, {"percentage": 80}]}

    def get_status(self):
        return {"status": "ok"}

    def test_fan_system(self):
        return {"ok": True}


class FakeGaming:
    def launch_game_by_label(self, label, mappings):
        return {"ok": True, "launched": label}

    def launch_game_by_steam_id(self, steamid):
        return {"ok": True, "launched": steamid}

    def launch_game_by_executable(self, path):
        return {"ok": True, "launched": path}

    def test_gaming_system(self):
        return {"ok": True}


@pytest.fixture
def server_app(monkeypatch):
    settings = FakeSettings()
    srv = FlaskServer(settings)

    # Inject fake controllers
    srv.audio_controller = FakeAudio()
    srv.streaming_controller = FakeStreaming()
    srv.fan_controller = FakeFan()
    srv.gaming_controller = FakeGaming()

    return srv.app.test_client()


def test_root_and_health(server_app):
    r = server_app.get('/')
    assert r.status_code == 200
    data = r.get_json()
    assert data['service'] == 'MyLocalAPI'

    r2 = server_app.get('/health')
    assert r2.status_code == 200
    assert r2.get_json()['status'] == 'healthy'


def test_switch_by_id_and_key(server_app):
    token = 'secret'
    # by id
    r = server_app.get(f'/switch?token={token}&id=dev-stream')
    assert r.status_code == 200
    assert r.get_json()['ok'] is True

    # by key
    r2 = server_app.get(f'/switch?token={token}&key=stream')
    assert r2.status_code == 200
    assert r2.get_json()['ok'] is True


def test_set_volume_and_current(server_app):
    token = 'secret'
    r = server_app.get(f'/volume?token={token}&percent=50')
    assert r.status_code == 200
    assert r.get_json()['ok'] is True

    # invalid percent
    r2 = server_app.get(f'/volume?token={token}&percent=150')
    assert r2.status_code == 400

    # current volume
    r3 = server_app.get(f'/volume/current?token={token}')
    assert r3.status_code == 200
    data = r3.get_json()
    assert data['ok'] is True
    assert data['deviceVolume'] == 42


def test_open_streaming_and_launch_game(server_app):
    token = 'secret'
    # open streaming
    r = server_app.get(f'/openStreaming?token={token}&service=youtube')
    assert r.status_code == 200
    assert r.get_json()['ok'] is True

    # launchGame by steamid
    r2 = server_app.get(f'/launchGame?token={token}&steamid=12345')
    assert r2.status_code == 200
    assert r2.get_json()['ok'] is True

    # missing params
    r3 = server_app.get(f'/launchGame?token={token}')
    assert r3.status_code == 400


def test_fan_apply_and_configs_and_status(server_app):
    token = 'secret'
    # apply by name
    r = server_app.get(f'/fan/apply?token={token}&name=profile1')
    assert r.status_code == 200
    assert r.get_json()['ok'] is True

    # apply by percent
    r2 = server_app.get(f'/fan/apply?token={token}&percent=30')
    assert r2.status_code == 200
    assert r2.get_json()['ok'] is True

    # configs with nearestTo
    r3 = server_app.get(f'/fan/configs?token={token}&nearestTo=70')
    assert r3.status_code == 200
    js = r3.get_json()
    assert js['ok'] is True
    assert js['nearest'] is not None

    # status
    r4 = server_app.get(f'/fan/status?token={token}')
    assert r4.status_code == 200
    assert r4.get_json()['ok'] is True


def test_status_and_diag(server_app):
    token = 'secret'
    r = server_app.get(f'/status?token={token}')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True

    r2 = server_app.get(f'/diag?token={token}')
    assert r2.status_code == 200
    diag = r2.get_json()['diagnostics']
    assert 'streaming' in diag
