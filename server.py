#!/usr/bin/env python3
"""
Flask HTTP server for MyLocalAPI
Provides REST endpoints for audio control, streaming, and fan management
"""

import threading
import time
import logging
from typing import Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.serving import make_server

from settings import SettingsManager
from audio_control import AudioController
from streaming import StreamingController
from fan_control import FanController

logger = logging.getLogger(__name__)

class FlaskServer:
    """Flask server wrapper with threading support"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for browser access
        
        self.server = None
        self.server_thread = None
        self.running = False
        
        # Initialize controllers
        self.audio_controller = None
        self.streaming_controller = None
        self.fan_controller = None
        
        self._setup_routes()
        self._init_controllers()
    
    def _init_controllers(self):
        """Initialize controllers based on current settings"""
        try:
            # Audio controller
            if self.settings_manager.get_setting('audio.enabled', True):
                svv_path = self.settings_manager.get_setting('audio.svv_path', '')
                self.audio_controller = AudioController(svv_path if svv_path else None)
            
            # Streaming controller
            apple_tv_moniker = self.settings_manager.get_setting('streaming.appleTVMoniker', '')
            self.streaming_controller = StreamingController(apple_tv_moniker)
            
            # Fan controller
            if self.settings_manager.get_setting('fan.enabled', False):
                fan_exe = self.settings_manager.get_setting('fan.fan_exe_path', '')
                fan_config = self.settings_manager.get_setting('fan.fan_config_path', '')
                if fan_exe and fan_config:
                    self.fan_controller = FanController(fan_exe, fan_config)
                    
        except Exception as e:
            logger.error(f"Error initializing controllers: {e}")
    
    def _check_token(self, token: str) -> bool:
        """Verify API token"""
        expected_token = self.settings_manager.get_setting('token', '')
        return token and token == expected_token
    
    def _require_auth(self, f):
        """Decorator to require token authentication"""
        def decorated_function(*args, **kwargs):
            token = request.args.get('token')
            if not self._check_token(token):
                return jsonify({"error": "Unauthorized"}), 401
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/', methods=['GET'])
        def root():
            """Root endpoint"""
            return jsonify({
                "service": "MyLocalAPI",
                "status": "running",
                "endpoints": [
                    "/switch", "/volume", "/volume/current", "/device/current",
                    "/openStreaming", "/fan/apply", "/fan/refresh", "/fan/configs",
                    "/fan/status", "/list", "/status", "/diag"
                ]
            })
        
        @self.app.route('/switch', methods=['GET'])
        @self._require_auth
        def switch_device():
            """Switch audio device"""
            if not self.settings_manager.get_setting('audio.enabled', True):
                return jsonify({"error": "Audio control is disabled"}), 403
            
            if not self.audio_controller:
                return jsonify({"error": "Audio controller not available"}), 500
            
            key = request.args.get('key')
            device_id = request.args.get('id')
            
            try:
                mappings = self.settings_manager.get_audio_mappings()
                
                if device_id:
                    # Direct device ID provided
                    success = self.audio_controller.set_default_device(device_id)
                    if success:
                        return jsonify({"ok": True, "device": device_id})
                    else:
                        return jsonify({"error": f"Failed to set device: {device_id}"}), 500
                
                elif key:
                    # Use device mapping
                    result = self.audio_controller.switch_to_device_by_key(key, mappings)
                    if result["ok"]:
                        return jsonify(result)
                    else:
                        return jsonify({"error": result["error"]}), 404
                
                else:
                    return jsonify({"error": "Missing 'key' or 'id' parameter"}), 400
                    
            except Exception as e:
                logger.error(f"Error in /switch: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/volume', methods=['GET'])
        @self._require_auth
        def set_volume():
            """Set device volume"""
            if not self.settings_manager.get_setting('audio.enabled', True):
                return jsonify({"error": "Audio control is disabled"}), 403
            
            if not self.audio_controller:
                return jsonify({"error": "Audio controller not available"}), 500
            
            percent_str = request.args.get('percent')
            if not percent_str:
                return jsonify({"error": "Missing 'percent' parameter"}), 400
            
            try:
                percent = int(percent_str)
                if not 0 <= percent <= 100:
                    return jsonify({"error": "Percent must be 0-100"}), 400
                
                success = self.audio_controller.set_volume(percent)
                if success:
                    return jsonify({"ok": True, "percent": percent})
                else:
                    return jsonify({"error": "Failed to set volume"}), 500
                    
            except ValueError:
                return jsonify({"error": "Invalid percent value"}), 400
            except Exception as e:
                logger.error(f"Error in /volume: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/volume/current', methods=['GET'])
        @self._require_auth
        def get_current_volume():
            """Get current volume"""
            if not self.settings_manager.get_setting('audio.enabled', True):
                return jsonify({"error": "Audio control is disabled"}), 403
            
            if not self.audio_controller:
                return jsonify({"error": "Audio controller not available"}), 500
            
            try:
                mappings = self.settings_manager.get_audio_mappings()
                snapshot = self.audio_controller.get_audio_snapshot(mappings)
                
                if snapshot["ok"]:
                    return jsonify({
                        "ok": True,
                        "deviceVolume": snapshot["volume"],
                        "systemVolume": snapshot["volume"],
                        "active": {
                            "deviceId": snapshot["device_id"],
                            "activeKey": snapshot["active_key"],
                            "matched": snapshot["matched"],
                            "deviceName": snapshot["device_name"],
                            "name": snapshot["name"]
                        }
                    })
                else:
                    return jsonify({
                        "error": "Could not get volume",
                        "reason": snapshot.get("reason", "unknown")
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error in /volume/current: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/device/current', methods=['GET'])
        @self._require_auth
        def get_current_device():
            """Get current default device"""
            if not self.settings_manager.get_setting('audio.enabled', True):
                return jsonify({"error": "Audio control is disabled"}), 403
            
            if not self.audio_controller:
                return jsonify({"error": "Audio controller not available"}), 500
            
            try:
                mappings = self.settings_manager.get_audio_mappings()
                snapshot = self.audio_controller.get_audio_snapshot(mappings)
                
                if snapshot["ok"]:
                    return jsonify({
                        "ok": True,
                        "deviceId": snapshot["device_id"],
                        "activeKey": snapshot["active_key"],
                        "matched": snapshot["matched"],
                        "deviceName": snapshot["device_name"],
                        "name": snapshot["name"],
                        "volumes": {
                            "deviceVolume": snapshot["volume"],
                            "systemVolume": snapshot["volume"]
                        }
                    })
                else:
                    return jsonify({
                        "error": "Could not resolve default device",
                        "reason": snapshot.get("reason", "unknown")
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error in /device/current: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/openStreaming', methods=['GET'])
        @self._require_auth
        def open_streaming():
            """Open streaming service"""
            if not self.settings_manager.get_setting('streaming.launch_streaming_by_endpoint', True):
                return jsonify({
                    "error": "Streaming service endpoint is disabled",
                    "details": "Enable 'Launch Streaming service by endpoint' in settings"
                }), 403
            
            service = request.args.get('service')
            if not service:
                return jsonify({"error": "Missing 'service' parameter"}), 400
            
            try:
                # Switch to streaming device if configured
                if self.audio_controller and self.settings_manager.get_setting('audio.enabled', True):
                    mappings = self.settings_manager.get_audio_mappings()
                    streaming_result = self.audio_controller.switch_to_streaming_device(mappings)
                    if streaming_result["ok"]:
                        logger.info("Switched to streaming device")
                
                # Apply fan config if enabled
                if (self.fan_controller and 
                    self.settings_manager.get_setting('fan.enabled', False) and
                    self.settings_manager.get_setting('fan.apply_on_stream_launch', False)):
                    
                    selected_config = self.settings_manager.get_setting('fan.selected_config', '')
                    if selected_config:
                        try:
                            fan_result = self.fan_controller.set_fan_profile(selected_config)
                            if fan_result["ok"]:
                                logger.info(f"Applied fan config: {selected_config}")
                        except Exception as e:
                            logger.warning(f"Failed to apply fan config: {e}")
                
                # Launch streaming service
                if self.streaming_controller:
                    result = self.streaming_controller.launch_service(service)
                    if result["ok"]:
                        return jsonify(result)
                    else:
                        return jsonify({"error": result["error"]}), 500
                else:
                    return jsonify({"error": "Streaming controller not available"}), 500
                    
            except Exception as e:
                logger.error(f"Error in /openStreaming: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/fan/apply', methods=['GET'])
        @self._require_auth
        def apply_fan_config():
            """Apply fan configuration"""
            if not self.settings_manager.get_setting('fan.enabled', False):
                return jsonify({"error": "Fan control is disabled"}), 403
            
            if not self.fan_controller:
                return jsonify({"error": "Fan controller not available"}), 500
            
            name = request.args.get('name')
            percent_str = request.args.get('percent')
            
            try:
                if name:
                    result = self.fan_controller.set_fan_profile(name)
                    if result["ok"]:
                        # Restart with config for immediate effect
                        config_path = result["config"]
                        restart_success = self.fan_controller.restart_with_config(config_path)
                        result["restarted"] = restart_success
                    return jsonify(result)
                
                elif percent_str:
                    percent = int(percent_str)
                    if not 0 <= percent <= 100:
                        return jsonify({"error": "Percent must be 0-100"}), 400
                    
                    result = self.fan_controller.set_fan_percentage(percent)
                    if result["ok"]:
                        # Restart with config for immediate effect
                        config_path = result["config"]
                        restart_success = self.fan_controller.restart_with_config(config_path)
                        result["restarted"] = restart_success
                    return jsonify(result)
                
                else:
                    return jsonify({"error": "Provide 'name' or 'percent' parameter"}), 400
                    
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Error in /fan/apply: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/fan/refresh', methods=['GET'])
        @self._require_auth
        def refresh_fan():
            """Refresh fan sensors"""
            if not self.settings_manager.get_setting('fan.enabled', False):
                return jsonify({"error": "Fan control is disabled"}), 403
            
            if not self.fan_controller:
                return jsonify({"error": "Fan controller not available"}), 500
            
            try:
                success = self.fan_controller.refresh_sensors()
                if success:
                    return jsonify({"ok": True, "status": "refreshed"})
                else:
                    return jsonify({"error": "Failed to refresh sensors"}), 500
                    
            except Exception as e:
                logger.error(f"Error in /fan/refresh: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/fan/configs', methods=['GET'])
        @self._require_auth
        def get_fan_configs():
            """Get fan configuration list"""
            if not self.settings_manager.get_setting('fan.enabled', False):
                return jsonify({"error": "Fan control is disabled"}), 403
            
            if not self.fan_controller:
                return jsonify({"error": "Fan controller not available"}), 500
            
            try:
                summary = self.fan_controller.get_config_summary()
                
                # Handle nearestTo parameter
                nearest = None
                nearest_to_str = request.args.get('nearestTo')
                if nearest_to_str:
                    try:
                        target_percent = int(nearest_to_str)
                        percentage_configs = summary["percentage_configs"]
                        if percentage_configs:
                            nearest = min(percentage_configs, 
                                        key=lambda x: abs(x["percentage"] - target_percent))
                    except ValueError:
                        pass
                
                return jsonify({
                    "ok": True,
                    "summary": summary,
                    "nearest": nearest
                })
                
            except Exception as e:
                logger.error(f"Error in /fan/configs: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/fan/status', methods=['GET'])
        @self._require_auth
        def get_fan_status():
            """Get fan control status"""
            if not self.settings_manager.get_setting('fan.enabled', False):
                return jsonify({"error": "Fan control is disabled"}), 403
            
            if not self.fan_controller:
                return jsonify({"error": "Fan controller not available"}), 500
            
            try:
                status = self.fan_controller.get_status()
                return jsonify({"ok": True, **status})
                
            except Exception as e:
                logger.error(f"Error in /fan/status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/list', methods=['GET'])
        @self._require_auth
        def list_devices():
            """List audio devices"""
            if not self.settings_manager.get_setting('audio.enabled', True):
                return jsonify({"error": "Audio control is disabled"}), 403
            
            if not self.audio_controller:
                return jsonify({"error": "Audio controller not available"}), 500
            
            try:
                result = self.audio_controller.get_playback_devices()
                if result["ok"]:
                    return jsonify({
                        "ok": True,
                        "devices": result["devices"],
                        "total": result["total"]
                    })
                else:
                    return jsonify({
                        "ok": False,
                        "message": "Failed to get devices",
                        "error": result.get("error", "Unknown error"),
                        "total": 0
                    })
                    
            except Exception as e:
                logger.error(f"Error in /list: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/status', methods=['GET'])
        @self._require_auth
        def get_status():
            """Get overall system status"""
            try:
                # Audio status
                audio_status = {"ok": False}
                if self.audio_controller and self.settings_manager.get_setting('audio.enabled', True):
                    mappings = self.settings_manager.get_audio_mappings()
                    audio_snapshot = self.audio_controller.get_audio_snapshot(mappings)
                    if audio_snapshot["ok"]:
                        audio_status = {
                            "ok": True,
                            "deviceId": audio_snapshot["device_id"],
                            "activeKey": audio_snapshot["active_key"],
                            "matched": audio_snapshot["matched"],
                            "deviceName": audio_snapshot["device_name"],
                            "name": audio_snapshot["name"]
                        }
                
                # Volume status
                volume_status = {"ok": False}
                if self.audio_controller and self.settings_manager.get_setting('audio.enabled', True):
                    volume = self.audio_controller.get_current_volume()
                    if volume is not None:
                        volume_status = {
                            "ok": True,
                            "deviceVolume": volume,
                            "systemVolume": volume
                        }
                
                # Device list
                devices = []
                if self.audio_controller and self.settings_manager.get_setting('audio.enabled', True):
                    device_result = self.audio_controller.get_playback_devices()
                    if device_result["ok"]:
                        devices = device_result["devices"]
                
                return jsonify({
                    "ok": True,
                    "active": audio_status,
                    "volumes": volume_status,
                    "devices": devices
                })
                
            except Exception as e:
                logger.error(f"Error in /status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/diag', methods=['GET'])
        @self._require_auth
        def get_diagnostics():
            """Get diagnostic information"""
            try:
                diag = {
                    "ok": True,
                    "audio": {"enabled": False, "status": "disabled"},
                    "fan": {"enabled": False, "status": "disabled"},
                    "streaming": {"enabled": True}
                }
                
                # Audio diagnostics
                if self.settings_manager.get_setting('audio.enabled', True):
                    diag["audio"]["enabled"] = True
                    if self.audio_controller:
                        audio_test = self.audio_controller.test_audio_system()
                        diag["audio"]["status"] = audio_test
                    else:
                        diag["audio"]["status"] = {"error": "Controller not initialized"}
                
                # Fan diagnostics  
                if self.settings_manager.get_setting('fan.enabled', False):
                    diag["fan"]["enabled"] = True
                    if self.fan_controller:
                        fan_test = self.fan_controller.test_fan_system()
                        diag["fan"]["status"] = fan_test
                    else:
                        diag["fan"]["status"] = {"error": "Controller not initialized"}
                
                # Streaming diagnostics
                if self.streaming_controller:
                    browser_test = self.streaming_controller.test_browsers()
                    diag["streaming"]["status"] = browser_test
                
                return jsonify({"ok": True, "diagnostics": diag})
                
            except Exception as e:
                logger.error(f"Error in /diag: {e}")
                return jsonify({"error": str(e)}), 500
    
    def start(self) -> bool:
        """Start the Flask server"""
        if self.running:
            return False
        
        try:
            port = self.settings_manager.get_setting('port', 1482)
            
            # Create server
            self.server = make_server('127.0.0.1', port, self.app, threaded=True)
            
            # Start server in thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.running = True
            logger.info(f"Flask server started on port {port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Flask server: {e}")
            return False
    
    def stop(self):
        """Stop the Flask server"""
        if not self.running:
            return
        
        self.running = False
        
        if self.server:
            self.server.shutdown()
            self.server = None
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
            self.server_thread = None
        
        logger.info("Flask server stopped")
    
    def is_running(self) -> bool:
        """Check if server is running"""
        return self.running and self.server is not None
    
    def get_url(self) -> str:
        """Get server URL"""
        host = self.settings_manager.get_setting('host', '127.0.0.1')
        port = self.settings_manager.get_setting('port', 1482)
        
        # For network access, show the actual network IP or indicate network access
        if host == '0.0.0.0':
            display_host = self._get_local_ip() or 'localhost'
        elif host == 'localhost':
            display_host = '127.0.0.1'
        else:
            display_host = host
            
        return f"http://{display_host}:{port}/"
    
    def _get_local_ip(self) -> str:
        """Get local network IP address"""
        try:
            import socket
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"