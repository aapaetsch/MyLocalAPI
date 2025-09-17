import os
import tempfile
import sys
import types

import pytest

from src import utils


def test_get_desktop_path_returns_path():
    path = utils._get_desktop_path()
    assert isinstance(path, str)
    assert os.path.isabs(path)


def test_create_desktop_shortcut_url_fallback(tmp_path, monkeypatch):
    # Force win32com not available
    monkeypatch.setitem(sys.modules, 'win32com', None)

    desktop = tmp_path
    monkeypatch.setattr(utils, '_get_desktop_path', lambda: str(desktop))

    target = r"C:\Program Files\MyLocalAPI\MyLocalAPI.exe"
    name = 'MyLocalAPI Test'
    icon = ''

    # Call the function; should create a .url file
    utils.create_desktop_shortcut(name, target, args='', icon=icon, description='desc')

    # Check .url file exists
    files = list(desktop.iterdir())
    assert any(f.name.endswith('.url') for f in files), f"No .url created in {desktop}"


def test_prompt_create_desktop_shortcut_marker(tmp_path, monkeypatch):
    # Ensure marker file is written and prompt returns without showing GUI when marker exists
    appname = 'MyLocalAPI Test'
    appdata = tmp_path
    marker = os.path.join(str(appdata), 'first_run_shortcut_done')

    monkeypatch.setattr(utils, 'get_app_data_dir', lambda: str(appdata))

    # Ensure marker does not exist, then run prompt which should create marker after calling create_desktop_shortcut
    created = []

    def fake_create(name, target='', args='', icon='', description=''):
        created.append(True)

    monkeypatch.setattr(utils, 'create_desktop_shortcut', fake_create)

    # Provide a fake tkinter with messagebox.askyesno returning True
    fake_tk = types.ModuleType('tkinter')

    class FakeRoot:
        def withdraw(self):
            pass
        def destroy(self):
            pass

    def FakeTk():
        return FakeRoot()

    fake_tk.Tk = FakeTk
    fake_msg = types.SimpleNamespace(askyesno=lambda title, msg: True)

    monkeypatch.setitem(sys.modules, 'tkinter', fake_tk)
    monkeypatch.setitem(sys.modules, 'tkinter.messagebox', fake_msg)

    # Run prompt (should call fake_create and write the marker)
    utils.prompt_create_desktop_shortcut(app_name=appname, target='exe')

    assert os.path.exists(marker), f"Marker file {marker} was not created"
    assert created, 'create_desktop_shortcut was not called'
