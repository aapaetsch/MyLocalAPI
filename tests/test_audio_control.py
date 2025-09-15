#!/usr/bin/env python3
"""
Unit tests for audio_control.AudioController

These tests mock out the subprocess calls and bundled executable resolution so
they run quickly and deterministically on CI and developer machines.
"""

import subprocess
import unittest
from unittest.mock import patch, MagicMock

from audio_control import AudioController


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=["svcl.exe"], returncode=returncode, stdout=stdout, stderr=stderr)


class TestAudioController(unittest.TestCase):
    def setUp(self):
        # Ensure find_bundled_executable returns a fake path so constructor succeeds
        patcher = patch('audio_control.find_bundled_executable', return_value='C:\\fake\\svcl.exe')
        self.addCleanup(patcher.stop)
        self.mock_find = patcher.start()

        # Create controller instance
        self.controller = AudioController()

    def test_parse_volume_variants(self):
        self.assertEqual(self.controller._parse_volume('45%'), 45)
        self.assertEqual(self.controller._parse_volume('45.6%'), 46)
        self.assertEqual(self.controller._parse_volume('0%'), 0)
        self.assertEqual(self.controller._parse_volume('100%'), 100)
        self.assertIsNone(self.controller._parse_volume(''))
        self.assertIsNone(self.controller._parse_volume(None))
        self.assertIsNone(self.controller._parse_volume('abc'))

    @patch('audio_control.run_subprocess_safe')
    def test_get_devices_raw_parsing(self, mock_run):
        # Prepare CSV with required headers and two rows
        csv_text = 'Name,Device Name,Direction,Default,Default Multimedia,Default Communications,Volume Percent,Command-Line Friendly ID\n'
        csv_text += 'Speakers,DeviceA,Render,Yes,No,No,50%,ID\\\\One\n'
        csv_text += 'Microphone,DeviceB,Capture,No,No,No,0%,ID\\\\Two\n'

        mock_run.return_value = _cp(stdout=csv_text, returncode=0)

        result = self.controller.get_devices_raw()
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['rows']), 2)
        # Ensure headers list is present and required header included
        self.assertIn('Name', result['headers'])

    @patch('audio_control.run_subprocess_safe')
    def test_get_devices_raw_bom_handling(self, mock_run):
        csv_text = '\ufeffName,Device Name,Direction,Default,Default Multimedia,Default Communications,Volume Percent,Command-Line Friendly ID\n'
        csv_text += 'Speakers,DeviceA,Render,Yes,No,No,25%,ID\\\\One\n'
        mock_run.return_value = _cp(stdout=csv_text, returncode=0)

        result = self.controller.get_devices_raw()
        self.assertTrue(result['ok'])
        self.assertEqual(result['rows'][0]['Name'], 'Speakers')

    def test_get_playback_devices_filters(self):
        # Patch get_devices_raw to return mixed directions
        with patch.object(self.controller, 'get_devices_raw', return_value={
            'ok': True,
            'rows': [
                {'Name': 'A', 'Device Name': 'DevA', 'Direction': 'Render', 'Volume Percent': '10%', 'Command-Line Friendly ID': 'ID\\One', 'Default': '' , 'Default Multimedia':'', 'Default Communications':''},
                {'Name': 'B', 'Device Name': 'DevB', 'Direction': 'Capture', 'Volume Percent': '20%', 'Command-Line Friendly ID': 'ID\\Two', 'Default': '' , 'Default Multimedia':'', 'Default Communications':''}
            ]
        }):
            # Also patch clean_audio_device_id
            with patch('audio_control.clean_audio_device_id', side_effect=lambda x: x):
                play = self.controller.get_playback_devices()
                self.assertTrue(play['ok'])
                self.assertEqual(play['total'], 1)

    @patch('audio_control.run_subprocess_safe')
    @patch('audio_control.clean_audio_device_id')
    def test_get_current_default_device_success(self, mock_clean, mock_run):
        # First call returns the default device id
        mock_run.side_effect = [
            _cp(stdout='ID\\Default\n', returncode=0),  # GetColumnValue
            _cp(stdout='55', returncode=0)  # GetPercent
        ]
        mock_clean.return_value = 'ID\\Default'

        # Patch get_playback_devices to return a matching device
        with patch.object(self.controller, 'get_playback_devices', return_value={
            'ok': True,
            'devices': [
                {'device_id': 'ID\\Default', 'device_name': 'DevDefault', 'name': 'Default', 'volume_percent': 55}
            ]
        }):
            res = self.controller.get_current_default_device()
            self.assertTrue(res['ok'])
            self.assertEqual(res['device_id'], 'ID\\Default')
            self.assertEqual(res['volume'], 55)

    def test_set_default_device_validation(self):
        with self.assertRaises(ValueError):
            self.controller.set_default_device('')

    @patch('audio_control.run_subprocess_safe')
    def test_set_default_device_success_and_fail(self, mock_run):
        mock_run.return_value = _cp(returncode=0)
        self.assertTrue(self.controller.set_default_device('ID\\One'))

        mock_run.return_value = _cp(returncode=1, stderr='error')
        self.assertFalse(self.controller.set_default_device('ID\\One'))

    def test_set_volume_validation(self):
        with self.assertRaises(ValueError):
            self.controller.set_volume(-1)
        with self.assertRaises(ValueError):
            self.controller.set_volume(101)

    @patch('audio_control.run_subprocess_safe')
    def test_set_volume_success_and_fail(self, mock_run):
        mock_run.return_value = _cp(returncode=0)
        self.assertTrue(self.controller.set_volume(30, device_id='ID\\One'))

        mock_run.return_value = _cp(returncode=1, stderr='fail')
        self.assertFalse(self.controller.set_volume(30, device_id='ID\\One'))

    @patch('audio_control.run_subprocess_safe')
    def test_get_current_volume(self, mock_run):
        mock_run.return_value = _cp(stdout='77', returncode=0)
        self.assertEqual(self.controller.get_current_volume('ID\\One'), 77)

        mock_run.return_value = _cp(returncode=1, stderr='err')
        self.assertIsNone(self.controller.get_current_volume('ID\\One'))

    def test_get_audio_snapshot_matched_and_unmatched(self):
        # Matched
        with patch.object(self.controller, 'get_current_default_device', return_value={
            'ok': True, 'device_id': 'ID\\Match', 'device_name': 'Dev', 'name': 'N', 'volume': 12
        }):
            mappings = [{'label': 'match', 'device_id': 'ID\\Match'}]
            snap = self.controller.get_audio_snapshot(mappings)
            self.assertTrue(snap['ok'])
            self.assertTrue(snap['matched'])
            self.assertEqual(snap['active_key'], 'match')

        # Unmatched
        with patch.object(self.controller, 'get_current_default_device', return_value={
            'ok': True, 'device_id': 'ID\\Other', 'device_name': 'Dev', 'name': 'N', 'volume': 12
        }):
            mappings = [{'label': 'match', 'device_id': 'ID\\Match'}]
            snap = self.controller.get_audio_snapshot(mappings)
            self.assertTrue(snap['ok'])
            self.assertFalse(snap['matched'])
            self.assertEqual(snap['active_key'], 'unknown')

    def test_switch_to_device_by_key(self):
        mappings = [{'label': 'one', 'device_id': 'ID\\One'}]

        with patch.object(self.controller, 'set_default_device', return_value=True):
            res = self.controller.switch_to_device_by_key('one', mappings)
            self.assertTrue(res['ok'])

        with patch.object(self.controller, 'set_default_device', return_value=False):
            res = self.controller.switch_to_device_by_key('one', mappings)
            self.assertFalse(res['ok'])

        res = self.controller.switch_to_device_by_key('missing', mappings)
        self.assertFalse(res['ok'])

    def test_streaming_device_helpers(self):
        mappings = [
            {'label': 'a', 'device_id': 'ID1', 'use_for_streaming': False},
            {'label': 'b', 'device_id': 'ID2', 'use_for_streaming': True}
        ]
        self.assertEqual(self.controller.get_streaming_device_id(mappings), 'ID2')

        with patch.object(self.controller, 'set_default_device', return_value=True):
            res = self.controller.switch_to_streaming_device(mappings)
            self.assertTrue(res['ok'])

        # No streaming device configured
        res = self.controller.switch_to_streaming_device([])
        self.assertFalse(res['ok'])

    def test_test_audio_system(self):
        with patch.object(self.controller, 'get_playback_devices', return_value={'ok': True, 'total': 2}):
            with patch.object(self.controller, 'get_current_default_device', return_value={'ok': True}):
                with patch.object(self.controller, 'get_current_volume', return_value=33):
                    res = self.controller.test_audio_system()
                    self.assertTrue(res['ok'])
                    self.assertEqual(res['devices_found'], 2)


if __name__ == '__main__':
    unittest.main()
