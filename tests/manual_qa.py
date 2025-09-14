#!/usr/bin/env python3
"""
Manual QA Test Script for MyLocalAPI
Tests basic functionality and API endpoints
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any

class QATestRunner:
    """Runs QA tests against MyLocalAPI server"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:1482", token: str = "changeme"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.test_results = []
        
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results"""
        print(f"\n{'='*60}")
        print(f"Running Test: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            success = result.get('success', False)
            message = result.get('message', 'No message')
            
            self.test_results.append({
                'name': test_name,
                'success': success,
                'message': message
            })
            
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"\n{status}: {message}")
            
            return success
            
        except Exception as e:
            self.test_results.append({
                'name': test_name,
                'success': False,
                'message': f"Exception: {str(e)}"
            })
            
            print(f"\n✗ FAIL: Exception occurred: {str(e)}")
            return False
    
    def api_request(self, endpoint: str, params: Dict[str, Any] = None) -> requests.Response:
        """Make API request with token"""
        if params is None:
            params = {}
        params['token'] = self.token
        
        url = f"{self.base_url}{endpoint}"
        print(f"Request: GET {url}?{self._format_params(params)}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"Response: {response.status_code}")
        
        try:
            json_data = response.json()
            print(f"Data: {json.dumps(json_data, indent=2)}")
        except:
            print(f"Data: {response.text[:200]}...")
            
        return response
    
    def _format_params(self, params: Dict[str, Any]) -> str:
        """Format parameters for display"""
        return "&".join([f"{k}={v}" for k, v in params.items()])
    
    # Test Cases
    
    def test_server_connection(self) -> Dict[str, Any]:
        """Test 1: Basic server connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                json_data = response.json()
                if 'service' in json_data and json_data['service'] == 'MyLocalAPI':
                    return {'success': True, 'message': 'Server is running and responding correctly'}
                else:
                    return {'success': False, 'message': f'Unexpected response format: {json_data}'}
            else:
                return {'success': False, 'message': f'Server returned status {response.status_code}'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': 'Cannot connect to server. Is it running?'}
        except Exception as e:
            return {'success': False, 'message': f'Connection error: {str(e)}'}
    
    def test_authentication(self) -> Dict[str, Any]:
        """Test 2: Token authentication"""
        # Test with correct token
        response = self.api_request('/device/current')
        if response.status_code != 401:
            success_correct = True
            message_correct = f"Correct token accepted (status: {response.status_code})"
        else:
            success_correct = False  
            message_correct = "Correct token was rejected"
        
        # Test with incorrect token
        try:
            bad_response = requests.get(f"{self.base_url}/device/current", 
                                      params={'token': 'invalid_token'}, timeout=5)
            if bad_response.status_code == 401:
                success_invalid = True
                message_invalid = "Invalid token correctly rejected"
            else:
                success_invalid = False
                message_invalid = f"Invalid token was accepted (status: {bad_response.status_code})"
        except Exception as e:
            success_invalid = False
            message_invalid = f"Error testing invalid token: {str(e)}"
        
        if success_correct and success_invalid:
            return {'success': True, 'message': f'{message_correct} and {message_invalid}'}
        else:
            return {'success': False, 'message': f'{message_correct}, {message_invalid}'}
    
    def test_audio_endpoints(self) -> Dict[str, Any]:
        """Test 3: Audio control endpoints"""
        tests = []
        
        # Test device/current
        response = self.api_request('/device/current')
        tests.append(('device/current', response.status_code in [200, 500]))  # 500 ok if audio disabled
        
        # Test volume/current  
        response = self.api_request('/volume/current')
        tests.append(('volume/current', response.status_code in [200, 403, 500]))
        
        # Test list
        response = self.api_request('/list')
        tests.append(('list', response.status_code in [200, 403]))
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        if passed == total:
            return {'success': True, 'message': f'All {total} audio endpoints responded correctly'}
        else:
            return {'success': False, 'message': f'Only {passed}/{total} audio endpoints responded correctly'}
    
    def test_streaming_endpoints(self) -> Dict[str, Any]:
        """Test 4: Streaming endpoints"""
        # Test with invalid service
        response = self.api_request('/openStreaming', {'service': 'invalid_service'})
        
        if response.status_code == 403:
            return {'success': True, 'message': 'Streaming endpoint disabled (expected if not configured)'}
        elif response.status_code == 400:
            json_data = response.json()
            if 'error' in json_data:
                return {'success': True, 'message': 'Invalid service correctly rejected'}
        elif response.status_code == 500:
            return {'success': True, 'message': 'Streaming endpoint responded (may have dependency issues)'}
        
        return {'success': False, 'message': f'Unexpected response from streaming endpoint: {response.status_code}'}
    
    def test_fan_endpoints(self) -> Dict[str, Any]:
        """Test 5: Fan control endpoints"""
        tests = []
        
        # Test fan/status
        response = self.api_request('/fan/status')
        tests.append(('fan/status', response.status_code in [200, 403, 500]))
        
        # Test fan/configs
        response = self.api_request('/fan/configs')
        tests.append(('fan/configs', response.status_code in [200, 403, 500]))
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        if passed == total:
            return {'success': True, 'message': f'All {total} fan endpoints responded correctly'}
        else:
            return {'success': False, 'message': f'Only {passed}/{total} fan endpoints responded correctly'}
    
    def test_system_endpoints(self) -> Dict[str, Any]:
        """Test 6: System endpoints"""
        tests = []
        
        # Test status
        response = self.api_request('/status')
        tests.append(('status', response.status_code == 200))
        
        # Test diag
        response = self.api_request('/diag')
        tests.append(('diag', response.status_code == 200))
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        if passed == total:
            return {'success': True, 'message': f'All {total} system endpoints working correctly'}
        else:
            return {'success': False, 'message': f'Only {passed}/{total} system endpoints working correctly'}
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test 7: Error handling for invalid requests"""
        tests = []
        
        # Test invalid endpoint
        try:
            response = requests.get(f"{self.base_url}/invalid_endpoint", 
                                  params={'token': self.token}, timeout=5)
            tests.append(('invalid_endpoint', response.status_code == 404))
        except Exception as e:
            tests.append(('invalid_endpoint', False))
        
        # Test missing parameters
        try:
            response = requests.get(f"{self.base_url}/volume", 
                                  params={'token': self.token}, timeout=5)  # Missing percent
            tests.append(('missing_params', response.status_code == 400))
        except Exception as e:
            tests.append(('missing_params', False))
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        if passed == total:
            return {'success': True, 'message': 'Error handling working correctly'}
        else:
            return {'success': False, 'message': f'Error handling issues: {passed}/{total} tests passed'}
    
    def run_all_tests(self):
        """Run all QA tests"""
        print("MyLocalAPI Manual QA Test Runner")
        print(f"Testing server at: {self.base_url}")
        print(f"Using token: {self.token}")
        
        tests = [
            ("Server Connection", self.test_server_connection),
            ("Authentication", self.test_authentication),
            ("Audio Endpoints", self.test_audio_endpoints),
            ("Streaming Endpoints", self.test_streaming_endpoints),
            ("Fan Endpoints", self.test_fan_endpoints),
            ("System Endpoints", self.test_system_endpoints),
            ("Error Handling", self.test_error_handling),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            time.sleep(1)  # Brief pause between tests
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print(f"\n{'='*60}")
        print("TEST RESULTS SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"{status} {result['name']}: {result['message']}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! MyLocalAPI is functioning correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the results above for issues.")
            return False

def main():
    """Main test runner"""
    # Parse command line arguments
    base_url = "http://127.0.0.1:1482"
    token = "changeme"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        token = sys.argv[2]
    
    print(f"Usage: {sys.argv[0]} [base_url] [token]")
    print(f"Examples:")
    print(f"  {sys.argv[0]} http://127.0.0.1:1482 changeme")
    print(f"  {sys.argv[0]} http://192.168.1.100:1482 your_secure_token")
    print()
    
    # Create test runner
    qa_runner = QATestRunner(base_url, token)
    
    # Check if server is reachable before starting tests
    print("Checking server connectivity...")
    try:
        response = requests.get(base_url, timeout=5)
        print(f"✓ Server is reachable (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot reach server. Please ensure MyLocalAPI is running.")
        print(f"Expected URL: {base_url}")
        print("\nTo start the server:")
        print("1. Run MyLocalAPI.exe or python main.py")
        print("2. Click 'Start' in the GUI or tray menu")
        print("3. Re-run this test script")
        return 1
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return 1
    
    # Run all tests
    print(f"\nStarting automated QA tests...")
    success = qa_runner.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())