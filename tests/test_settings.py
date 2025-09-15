import json
import os
import subprocess
import sys

import pytest

from settings import SettingsManager


def make_manager(monkeypatch, tmp_path):
    # Ensure settings file is in tmp_path
    monkeypatch.setattr('settings.get_app_data_dir', lambda: str(tmp_path))
    return SettingsManager()


def test_load_defaults_and_save_and_get_set(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # defaults should be loaded
    assert mgr.get_setting('port') == 1482

    # change token and save
    ok = mgr.set_setting('token', 'newtoken', save=True)
    assert ok is True
    assert mgr.get_setting('token') == 'newtoken'

    # file was written
    assert os.path.exists(mgr.settings_file)
    with open(mgr.settings_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data.get('token') == 'newtoken'


def test_set_audio_mappings_validation(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)

    # invalid mapping (not dict)
    assert mgr.set_audio_mappings(['notadict'], save=False) is False

    # missing keys
    assert mgr.set_audio_mappings([{'label': 'a'}], save=False) is False

    # valid mappings, ensure only one use_for_streaming kept
    mappings = [
        {'label': 'one', 'device_id': 'dev1', 'use_for_streaming': True},
        {'label': 'two', 'device_id': 'dev2', 'use_for_streaming': True}
    ]
    assert mgr.set_audio_mappings(mappings, save=False) is True
    res = mgr.get_audio_mappings()
    # Only first should keep use_for_streaming True
    assert sum(1 for m in res if m.get('use_for_streaming')) == 1


def test_get_streaming_device_id(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    mappings = [
        {'label': 'one', 'device_id': 'dev1', 'use_for_streaming': False},
        {'label': 'two', 'device_id': 'dev2', 'use_for_streaming': True}
    ]
    mgr.set_audio_mappings(mappings, save=False)
    assert mgr.get_streaming_device_id() == 'dev2'


def test_validate_settings_audio_and_token_and_port(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # invalid port
    mgr.set_setting('port', 80, save=False)
    mgr.set_setting('token', '', save=False)
    mgr.set_setting('audio.enabled', True, save=False)
    mgr.set_setting('audio.mappings', [], save=False)
    errors = mgr.validate_settings()
    assert any('port' in e.lower() for e in errors)
    assert any('token' in e.lower() for e in errors)
    assert any('audio control' in e.lower() for e in errors)


def test_fan_validation_and_parse_configs(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # create fake config dir
    cfg_dir = tmp_path / 'fanconfigs'
    cfg_dir.mkdir()
    (cfg_dir / 'one.json').write_text('{}')
    (cfg_dir / 'two.json').write_text('{}')
    (cfg_dir / 'notes.txt').write_text('ignore')

    mgr.set_setting('fan.enabled', True, save=False)
    mgr.set_setting('fan.fan_exe_path', str(tmp_path / 'fan.exe'), save=False)
    mgr.set_setting('fan.fan_config_path', str(cfg_dir), save=False)
    # monkeypatch os.path.exists so fan exe exists but leave others as default
    monkeypatch.setattr('os.path.exists', lambda p: True)

    configs = mgr.parse_fan_configs()
    assert 'one' in configs and 'two' in configs


def test_set_gaming_mappings_validation(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # both steam and exe filled -> invalid
    bad = [{'label': 'g', 'steam_appid': '1', 'exe_path': 'x'}]
    assert mgr.set_gaming_mappings(bad, save=False) is False

    # none filled -> invalid
    bad2 = [{'label': 'g2', 'steam_appid': '', 'exe_path': ''}]
    assert mgr.set_gaming_mappings(bad2, save=False) is False

    # valid mapping
    good = [{'label': 'g3', 'steam_appid': '123', 'exe_path': ''}]
    assert mgr.set_gaming_mappings(good, save=False) is True


def test_find_apple_tv_moniker(monkeypatch, tmp_path):
    # simulate powershell returning a moniker
    class CPR:
        def __init__(self, stdout, returncode=0):
            self.stdout = stdout
            self.returncode = returncode

    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: CPR('AppleInc.AppleTVWin_abc123\n', 0))
    mgr = make_manager(monkeypatch, tmp_path)
    mon = mgr.find_apple_tv_moniker()
    assert 'AppleInc' in mon


def test_export_import_settings(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # export
    export_file = tmp_path / 'export.json'
    mgr.set_setting('token', 'tok', save=False)
    assert mgr.export_settings(str(export_file)) is True

    # change file content and import
    with open(export_file, 'w', encoding='utf-8') as f:
        json.dump({'port': 5555, 'token': 'fromfile'}, f)

    assert mgr.import_settings(str(export_file)) is True
    assert mgr.get_setting('port') == 5555
    assert mgr.get_setting('token') == 'fromfile'


def test_ensure_firewall_rule_calls_utils(monkeypatch, tmp_path):
    mgr = make_manager(monkeypatch, tmp_path)
    # monkeypatch utils.create_firewall_rule
    called = {}

    def fake_create(port, name, allow_network):
        called['args'] = (port, name, allow_network)
        return True

    import utils as _utils
    monkeypatch.setattr(_utils, 'create_firewall_rule', fake_create)

    # ensure returns True
    assert mgr.ensure_firewall_rule() is True
    assert called
