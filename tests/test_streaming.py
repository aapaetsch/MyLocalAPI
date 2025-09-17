import types
import subprocess
import webbrowser
import sys

import pytest

import streaming as streaming


class DummyPopen:
    def __init__(self, pid=1234):
        self.pid = pid


def test_test_browsers_no_browsers(monkeypatch):
    # No browser paths found
    monkeypatch.setattr('os.path.exists', lambda p: False)
    sc = streaming.StreamingController()
    tb = sc.test_browsers()
    assert tb['chrome']['available'] is False
    assert tb['edge']['available'] is False


def test_launch_in_chrome_not_found(monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda p: False)
    sc = streaming.StreamingController()
    res = sc.launch_in_chrome('https://example.com')
    assert res['ok'] is False
    assert 'not found' in res['error'].lower()


def test_launch_in_chrome_success_focus(monkeypatch):
    # Simulate a chrome path exists
    def exists(p):
        return 'chrome.exe' in p.lower()

    monkeypatch.setattr('os.path.exists', exists)

    sc = streaming.StreamingController()

    # Replace Popen and focus helpers
    monkeypatch.setattr(subprocess, 'Popen', lambda args: DummyPopen(9999))
    monkeypatch.setattr(sc, '_focus_window_by_process', lambda proc, timeout=3: True)
    res = sc.launch_in_chrome('https://example.com')
    assert res['ok'] is True
    assert res['browser'] == 'chrome'
    assert res['focused'] is True


def test_launch_service_fallback_to_edge(monkeypatch):
    # Simulate chrome present but chrome launch fails and edge present
    monkeypatch.setattr('os.path.exists', lambda p: 'chrome' in p.lower() or 'edge' in p.lower())
    sc = streaming.StreamingController()

    # Force launch_in_chrome to fail, and launch_in_edge to succeed
    monkeypatch.setattr(sc, 'launch_in_chrome', lambda url: {"ok": False})
    monkeypatch.setattr(sc, 'launch_in_edge', lambda url: {"ok": True, "browser": "edge", "url": url})

    res = sc.launch_service('youtube')
    assert res['ok'] is True
    assert res['service'] == 'youtube'
    assert res['browser'] in ('edge', 'chrome', 'default')


def test_launch_apple_tv_app_found(monkeypatch):
    # Ensure apple_tv_moniker is set
    sc = streaming.StreamingController(apple_tv_moniker='AppleInc.AppleTVWin_test')

    # Mock subprocess.Popen
    monkeypatch.setattr(subprocess, 'Popen', lambda args: DummyPopen(2222))

    # Mock psutil.process_iter to yield a process with info containing name
    class FakeProc:
        def __init__(self, name):
            self.info = {'pid': 1, 'name': name}

    class FakePsutil:
        @staticmethod
        def process_iter(attrs):
            yield FakeProc('AppleTV.exe')

    monkeypatch.setitem(sys.modules, 'psutil', FakePsutil())

    # focus by title should be called and succeed
    monkeypatch.setattr(sc, '_focus_window_by_title', lambda title, timeout=1: True)

    res = sc.launch_apple_tv_app(timeout=1)
    assert res['ok'] is True
    assert res['service'] == 'appletv'
    assert res['method'] == 'app'
    assert res['focused'] is True


def test_fallback_apple_tv_browser(monkeypatch):
    # No edge paths -> fallback to webbrowser
    monkeypatch.setattr('os.path.exists', lambda p: False)
    sc = streaming.StreamingController(apple_tv_moniker='')
    called = {}
    monkeypatch.setattr(webbrowser, 'open', lambda url: called.setdefault('url', url))

    res = sc._fallback_apple_tv()
    assert res['ok'] is True
    assert res['method'] == 'browser_fallback'
    assert 'tv.apple.com' in res['url']


def test_get_available_services_requirements(monkeypatch):
    # No browsers installed
    monkeypatch.setattr('os.path.exists', lambda p: False)
    sc = streaming.StreamingController()
    services = sc.get_available_services()
    # For youtube (chrome) and netflix (edge) there should be requirements
    assert 'youtube' in services
    assert any('not found' in r.lower() or r for r in services['youtube']['requirements'])
