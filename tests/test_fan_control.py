import os
import subprocess
import types
import time
import json

import pytest

from fan_control import FanController


class DummyProc:
    def __init__(self, pid, name, exe_path=None):
        self.pid = pid
        self.info = {'name': name, 'exe': exe_path}
        self._exe = exe_path

    def exe(self):
        return self._exe

    def create_time(self):
        return 123456.0

    def terminate(self):
        return None

    def wait(self, timeout=None):
        return None

    def kill(self):
        return None


def test_get_fancontrol_processes_and_running_and_exe(monkeypatch):
    p1 = DummyProc(1, 'FanControl.exe', r'C:\Program\FanControl\FanControl.exe')
    p2 = DummyProc(2, 'other.exe', r'C:\other\other.exe')

    def fake_iter(attrs):
        yield p1
        yield p2

    monkeypatch.setattr('psutil.process_iter', lambda attrs: fake_iter(attrs))

    fc = FanController(fan_exe_path=r'C:\Program\FanControl\FanControl.exe', fan_config_path='')
    procs = fc.get_fancontrol_processes()
    assert any('fancontrol' in p.info['name'].lower() for p in procs)
    assert fc.is_running() is True
    assert fc.get_running_exe_path() == r'C:\Program\FanControl\FanControl.exe'


def test_stop_fancontrol_sequence(monkeypatch):
    # Simulate the sequence of get_fancontrol_processes calls used by stop_fancontrol
    p = DummyProc(5, 'FanControl.exe', r'C:\FanControl\FanControl.exe')
    calls = [ [p], [] ]

    def seq():
        return calls.pop(0) if calls else []

    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path='')
    # Replace instance method with our sequence function
    fc.get_fancontrol_processes = seq

    # safe_kill_process_by_name should not raise
    monkeypatch.setattr('fan_control.safe_kill_process_by_name', lambda n: None)

    result = fc.stop_fancontrol(force=False)
    assert result is True


def test_start_and_ensure_running(monkeypatch):
    # Ensure exe exists
    monkeypatch.setattr('os.path.exists', lambda p: True)

    started = {'called': False}

    def fake_popen(args, creationflags=None):
        started['called'] = True
        return types.SimpleNamespace(pid=999)

    monkeypatch.setattr('subprocess.Popen', fake_popen)

    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path='')

    # Make is_running return True after start
    monkeypatch.setattr(fc, 'is_running', lambda: True)

    res = fc.start_fancontrol(minimized=True)
    assert res is True
    assert started['called'] is True

    # ensure_running should return True when already running
    monkeypatch.setattr(fc, 'is_running', lambda: True)
    assert fc.ensure_running() is True


def test_restart_with_config_and_switch_config(monkeypatch, tmp_path):
    config_file = tmp_path / 'myprofile.json'
    config_file.write_text('{}')

    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path=str(tmp_path))

    # stop_fancontrol and start_fancontrol should be called; patch them
    called = {'stop': False, 'start': False}
    monkeypatch.setattr(fc, 'stop_fancontrol', lambda: called.__setitem__('stop', True))
    monkeypatch.setattr(fc, 'start_fancontrol', lambda minimized, config_path=None: called.__setitem__('start', True) or True)

    res = fc.restart_with_config(str(config_file))
    assert res is True
    assert called['stop'] is True
    assert called['start'] is True

    # switch_config should raise when config not exists
    with pytest.raises(RuntimeError):
        fc.switch_config(str(tmp_path / 'nonexistent.json'))

    # If not running, start_fancontrol should be used
    monkeypatch.setattr(fc, 'is_running', lambda: False)
    monkeypatch.setattr(fc, 'start_fancontrol', lambda minimized=True, config_path=None: True)
    assert fc.switch_config(str(config_file)) is True


def test__switch_config_by_replacement_requires_admin(monkeypatch):
    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path='')
    # If not admin, it should log and return False
    monkeypatch.setattr('fan_control.is_admin', lambda: False)
    assert fc._switch_config_by_replacement('somepath') is False


def test_refresh_sensors_success_and_failure(monkeypatch):
    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path='')

    # ensure_running True and get_running_exe_path returns an exe
    monkeypatch.setattr(fc, 'ensure_running', lambda: True)
    monkeypatch.setattr(fc, 'get_running_exe_path', lambda: r'C:\FanControl\FanControl.exe')

    class CPR:
        def __init__(self, returncode=0, stderr=''):
            self.returncode = returncode
            self.stderr = stderr

    monkeypatch.setattr('subprocess.run', lambda *a, **k: CPR(returncode=0))
    assert fc.refresh_sensors() is True

    # Simulate non-zero returncode
    monkeypatch.setattr('subprocess.run', lambda *a, **k: CPR(returncode=1, stderr='err'))
    assert fc.refresh_sensors() is False


def test_get_config_files_and_summary(tmp_path):
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir()
    # Create several json files, some with percentage names
    (cfg_dir / 'profile50.json').write_text('{}')
    (cfg_dir / 'silent.json').write_text('{}')
    (cfg_dir / 'profile75.json').write_text('{}')

    fc = FanController(fan_exe_path='', fan_config_path=str(cfg_dir))
    files = fc.get_config_files()
    assert isinstance(files, list)
    names = [f['name'] for f in files]
    assert 'profile50' in names
    summary = fc.get_config_summary()
    assert summary['total'] == 3
    assert summary['with_percentage'] >= 2


def test_set_fan_percentage_and_profile(tmp_path, monkeypatch):
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir()
    (cfg_dir / '50.json').write_text('{}')
    (cfg_dir / '75.json').write_text('{}')
    (cfg_dir / 'cool.json').write_text('{}')

    fc = FanController(fan_exe_path='', fan_config_path=str(cfg_dir))

    # Mock switch_config to return True and capture calls
    called = {}
    def fake_switch(path):
        called['path'] = path
        return True

    monkeypatch.setattr(fc, 'switch_config', fake_switch)

    res = fc.set_fan_percentage(50)
    assert res['ok'] is True
    assert res['applied'] == 50

    res2 = fc.set_fan_percentage(60)
    assert res2['ok'] is True
    assert res2['applied'] in (50, 75)

    # set profile
    res3 = fc.set_fan_profile('cool')
    assert res3['ok'] is True
    assert res3['profile'].lower() == 'cool'


def test_get_status_and_test_fan_system(monkeypatch, tmp_path):
    # Setup a fake running process and config dir
    p = DummyProc(11, 'FanControl.exe', r'C:\FanControl\FanControl.exe')
    fc = FanController(fan_exe_path=r'C:\FanControl\FanControl.exe', fan_config_path=str(tmp_path))

    monkeypatch.setattr(fc, 'get_fancontrol_processes', lambda: [p])

    # create a config file
    cfg = tmp_path / '10.json'
    cfg.write_text('{}')

    # Ensure file checks work
    monkeypatch.setattr('os.path.exists', lambda p: True)

    status = fc.get_status()
    assert status['configured'] is True or isinstance(status['configured'], bool)
    assert 'processes' in status

    testres = fc.test_fan_system()
    assert 'system_ready' in testres
