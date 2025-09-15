import os
import subprocess
import types

import pytest

from gaming_control import GamingController


def test_launch_game_by_steam_id_empty():
    gc = GamingController()
    res = gc.launch_game_by_steam_id('')
    assert res['ok'] is False
    assert 'Steam App ID is required' in res['error']


def test_launch_game_by_steam_id_windows(monkeypatch):
    gc = GamingController()
    called = {}

    # Ensure os reports windows
    monkeypatch.setattr(os, 'name', 'nt', raising=False)

    def fake_startfile(url):
        called['url'] = url

    monkeypatch.setattr(os, 'startfile', fake_startfile)

    res = gc.launch_game_by_steam_id('12345')
    assert res['ok'] is True
    assert called.get('url') == 'steam://run/12345'


def test_launch_game_by_steam_id_posix(monkeypatch):
    gc = GamingController()
    called = {}

    monkeypatch.setattr(os, 'name', 'posix', raising=False)

    def fake_run(args, check=False):
        called['args'] = args

    monkeypatch.setattr(subprocess, 'run', fake_run)

    res = gc.launch_game_by_steam_id('98765')
    assert res['ok'] is True
    assert called.get('args') == ['xdg-open', 'steam://run/98765']


def test_launch_game_by_executable_errors_and_success(monkeypatch, tmp_path):
    gc = GamingController()

    # Empty path
    res = gc.launch_game_by_executable('')
    assert res['ok'] is False

    exe = tmp_path / 'game.exe'
    # not exists
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    res = gc.launch_game_by_executable(str(exe))
    assert res['ok'] is False and 'Executable not found' in res['error']

    # exists but not file
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    monkeypatch.setattr(os.path, 'isfile', lambda p: False)
    res = gc.launch_game_by_executable(str(exe))
    assert res['ok'] is False and 'Path is not a file' in res['error']

    # success path on windows (creationflags used)
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    monkeypatch.setattr(os, 'name', 'nt', raising=False)

    started = {}
    def fake_popen(args, creationflags=None):
        started['args'] = args
        started['flags'] = creationflags
        return types.SimpleNamespace(pid=42)

    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    res = gc.launch_game_by_executable(str(exe))
    assert res['ok'] is True
    assert started['args'] == [str(exe)]


def test_launch_game_by_label(monkeypatch):
    gc = GamingController()

    mappings = [
        {'label': 'SteamGame', 'steam_appid': '111', 'exe_path': ''},
        {'label': 'ExeGame', 'steam_appid': '', 'exe_path': 'C:\\games\\game.exe'}
    ]

    # Patch launch_game_by_steam_id
    def fake_steam(sid):
        return {'ok': True, 'steam_appid': sid}

    monkeypatch.setattr(gc, 'launch_game_by_steam_id', fake_steam)
    res = gc.launch_game_by_label('SteamGame', mappings)
    assert res['ok'] is True
    assert res.get('label') == 'SteamGame'

    # Patch launch_game_by_executable
    def fake_exe(path):
        return {'ok': True, 'exe_path': path}

    monkeypatch.setattr(gc, 'launch_game_by_executable', fake_exe)
    res2 = gc.launch_game_by_label('ExeGame', mappings)
    assert res2['ok'] is True
    assert res2.get('label') == 'ExeGame'

    # missing mapping
    res3 = gc.launch_game_by_label('Nope', mappings)
    assert res3['ok'] is False


def test_get_audio_device_for_game():
    gc = GamingController()
    mappings = [
        {'label': 'Game A', 'use_for_audio': True},
        {'label': 'Game B', 'use_for_audio': False}
    ]

    res = gc.get_audio_device_for_game('Game A', mappings)
    assert res == 'Game A'
    res2 = gc.get_audio_device_for_game('Game B', mappings)
    assert res2 is None


def test_test_gaming_system_detects_steam(monkeypatch):
    gc = GamingController()

    # If any steam path exists it should set steam_available True
    def fake_exists(path):
        if 'Steam.lnk' in path or 'steam.exe' in path:
            return True
        return False

    monkeypatch.setattr(os.path, 'exists', fake_exists)
    res = gc.test_gaming_system()
    assert res['ok'] is True
    assert res['steam_available'] is True


def test_test_gaming_system_no_steam(monkeypatch):
    gc = GamingController()
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    res = gc.test_gaming_system()
    assert res['ok'] is True
    assert res['steam_available'] is False
    assert 'Steam installation not detected' in res['issues'][0]
