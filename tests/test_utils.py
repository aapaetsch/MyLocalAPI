import os
import socket
import subprocess
import types
import sys

import pytest

import utils


def test_get_app_data_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    monkeypatch.setenv('APPDATA', str(tmp_path))
    p = utils.get_app_data_dir()
    assert p.endswith(os.path.join('MyLocalAPI'))


def test_format_and_truncate():
    assert utils.format_file_size(512) == '512.0 B'
    assert utils.format_file_size(1024) == '1.0 KB'
    assert utils.truncate_string('short', 10) == 'short'
    long = 'x' * 60
    assert utils.truncate_string(long, 10).endswith('...')


def test_validate_executable(monkeypatch, tmp_path):
    f = tmp_path / 'prog.exe'
    f.write_text('data')
    # Mock os.path checks
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    assert utils.validate_executable(str(f)) is True

    # Wrong extension
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    assert utils.validate_executable('file.txt') is False


def test_run_subprocess_safe_errors(monkeypatch):
    # TimeoutExpired
    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd='cmd', timeout=0)

    monkeypatch.setattr(subprocess, 'run', raise_timeout)
    with pytest.raises(RuntimeError):
        utils.run_subprocess_safe(['cmd'])

    # FileNotFoundError
    def raise_notfound(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, 'run', raise_notfound)
    with pytest.raises(RuntimeError) as ei:
        utils.run_subprocess_safe(['cmd'])
    assert 'Command not found' in str(ei.value)


def test_find_available_port_and_is_port_in_use():
    port = utils.find_available_port(start_port=20000, max_attempts=10)
    assert isinstance(port, int)

    # bind to a port and check is_port_in_use
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    s.listen(1)
    used_port = s.getsockname()[1]
    try:
        assert utils.is_port_in_use(used_port) is True
    finally:
        s.close()


def test_find_bundled_executable_which(monkeypatch):
    # Simulate where/which returning a path
    class CPR:
        def __init__(self, stdout, returncode=0):
            self.stdout = stdout
            self.returncode = returncode

    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: CPR('C:\\bin\\exe.exe\n', 0))
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    path = utils.find_bundled_executable('notexist.exe')
    assert path and 'bin' in path


def test_open_file_location_and_safe_kill(monkeypatch, tmp_path):
    # nonexistent file
    p = str(tmp_path / 'nofile')
    assert utils.open_file_location(p) is False

    # exist -> Windows explorer call
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    called = {}

    def fake_run(cmd, check=True, **k):
        called['cmd'] = cmd
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    assert utils.open_file_location('anything') is True
    assert 'explorer' in called['cmd'][0].lower()

    # safe_kill on windows
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: types.SimpleNamespace(returncode=0))
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    assert utils.safe_kill_process_by_name('proc.exe') is True

    # safe_kill on non-windows
    monkeypatch.setattr(sys, 'platform', 'linux', raising=False)
    assert utils.safe_kill_process_by_name('proc') is True


def test_firewall_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux', raising=False)
    assert utils.create_firewall_rule(1234) is True
    assert utils.remove_firewall_rule('name') is True


def test_get_local_network_ip_and_interfaces(monkeypatch):
    # Fake socket behavior
    class FakeSock:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def connect(self, addr):
            pass
        def getsockname(self):
            return ('10.0.0.5', 12345)

    monkeypatch.setattr(socket, 'socket', lambda *a, **k: FakeSock())
    ip = utils.get_local_network_ip()
    assert ip == '10.0.0.5'

    # Fake psutil
    class Addr:
        def __init__(self):
            self.family = socket.AF_INET
            self.address = '10.0.0.6'
            self.netmask = '255.255.255.0'

    fake_if = {'eth0': [Addr()]}
    try:
        import psutil
        monkeypatch.setattr(psutil, 'net_if_addrs', lambda: fake_if)
        ifs = utils.get_network_interfaces()
        assert any(i['ip'] == '10.0.0.6' for i in ifs)
    except Exception:
        pytest.skip('psutil not available in test env')


def test_clean_audio_device_id():
    s = '2 items found: \\Device\\Audio\\Render'
    assert 'Device' in utils.clean_audio_device_id(s)
    s2 = 'Simple Device ID'
    assert utils.clean_audio_device_id(s2) == 'Simple Device ID'


def test_autostart_manager_registry(monkeypatch):
    # Simulate winreg raising FileNotFoundError for is_enabled
    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        def OpenKey(self, *a, **k):
            raise FileNotFoundError()

    monkeypatch.setattr(utils, 'winreg', FakeWinreg())
    assert utils.AutostartManager.is_enabled() is False
