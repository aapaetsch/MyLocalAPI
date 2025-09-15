#!/usr/bin/env python3
"""
Network Discovery Tool for MyLocalAPI
Helps find MyLocalAPI servers on the local network

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import socket
import threading
import requests
import json
import time
import sys
from typing import List, Dict, Optional

class MyLocalAPIDiscovery:
    """Discovers MyLocalAPI servers on the local network"""
    
    def __init__(self, port: int = 1482, timeout: int = 2):
        self.port = port
        self.timeout = timeout
        self.found_servers = []
        
    def get_network_range(self) -> Optional[str]:
        """Get the local network range for scanning"""
        try:
            # Get local IP address
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            # Convert to network range (assumes /24 subnet)
            ip_parts = local_ip.split('.')
            network_base = '.'.join(ip_parts[:-1])
            
            return network_base
            
        except Exception as e:
            print(f"Error getting network range: {e}")
            return None
    
    def check_server(self, ip: str) -> Optional[Dict]:
        """Check if MyLocalAPI is running on the given IP"""
        try:
            url = f"http://{ip}:{self.port}/"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('service') == 'MyLocalAPI':
                        return {
                            'ip': ip,
                            'port': self.port,
                            'url': url,
                            'status': data.get('status', 'unknown'),
                            'endpoints': data.get('endpoints', [])
                        }
                except json.JSONDecodeError:
                    pass
                    
        except (requests.RequestException, socket.timeout):
            pass
        
        return None
    
    def scan_ip_range(self, network_base: str, start: int = 1, end: int = 254):
        """Scan IP range for MyLocalAPI servers"""
        print(f"Scanning {network_base}.{start}-{end} on port {self.port}...")
        
        threads = []
        results = []
        
        def scan_ip(ip_suffix: int):
            ip = f"{network_base}.{ip_suffix}"
            result = self.check_server(ip)
            if result:
                results.append(result)
                print(f"✓ Found MyLocalAPI server at {ip}")
        
        # Create threads for parallel scanning
        for i in range(start, end + 1):
            thread = threading.Thread(target=scan_ip, args=(i,))
            threads.append(thread)
            thread.start()
            
            # Limit concurrent threads
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []
        
        # Wait for remaining threads
        for thread in threads:
            thread.join()
        
        return results
    
    def discover_servers(self, custom_ips: List[str] = None) -> List[Dict]:
        """Discover MyLocalAPI servers on the network"""
        print("🔍 Discovering MyLocalAPI servers on the network...")
        print(f"Port: {self.port}, Timeout: {self.timeout}s")
        print("-" * 50)
        
        if custom_ips:
            # Check specific IP addresses
            print(f"Checking custom IPs: {', '.join(custom_ips)}")
            for ip in custom_ips:
                result = self.check_server(ip)
                if result:
                    self.found_servers.append(result)
                    print(f"✓ Found server at {ip}")
                else:
                    print(f"✗ No server at {ip}")
        else:
            # Auto-discover network range
            network_base = self.get_network_range()
            if not network_base:
                print("❌ Could not determine network range")
                return []
            
            print(f"Network range: {network_base}.1-254")
            
            # Scan the network
            servers = self.scan_ip_range(network_base)
            self.found_servers.extend(servers)
        
        return self.found_servers
    
    def print_results(self):
        """Print discovery results in a nice format"""
        print("\n" + "=" * 60)
        print("DISCOVERY RESULTS")
        print("=" * 60)
        
        if not self.found_servers:
            print("❌ No MyLocalAPI servers found on the network")
            print("\nTroubleshooting:")
            print("1. Ensure MyLocalAPI is running with network access (Host: 0.0.0.0)")
            print("2. Check Windows Firewall settings")
            print("3. Verify the server is on the same network")
            print("4. Try custom IP addresses with --ip option")
            return
        
        for i, server in enumerate(self.found_servers, 1):
            print(f"\n🖥️  Server #{i}")
            print(f"   IP Address: {server['ip']}")
            print(f"   Port: {server['port']}")
            print(f"   URL: {server['url']}")
            print(f"   Status: {server['status']}")
            print(f"   Endpoints: {len(server['endpoints'])} available")
            
            # Show sample cURL commands
            print(f"\n   Sample API calls (replace YOUR_TOKEN):")
            print(f"   curl \"{server['url']}device/current?token=YOUR_TOKEN\"")
            print(f"   curl \"{server['url']}volume?percent=50&token=YOUR_TOKEN\"")
            print(f"   curl \"{server['url']}switch?key=headphones&token=YOUR_TOKEN\"")
        
        print(f"\n✅ Found {len(self.found_servers)} MyLocalAPI server(s)")
        print("\n💡 Tips:")
        print("- Replace YOUR_TOKEN with the actual token from the server settings")
        print("- Use these URLs in your iOS Shortcuts or other network clients")
        print("- Test connectivity with the curl commands above")
    
    def test_server_connectivity(self, server_url: str, token: str = "") -> Dict:
        """Test connectivity to a discovered server"""
        print(f"\n🧪 Testing server at {server_url}")
        
        try:
            # Test basic connectivity
            response = requests.get(server_url, timeout=5)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            # Test with token (if provided)
            if token:
                test_url = f"{server_url}device/current"
                auth_response = requests.get(test_url, params={"token": token}, timeout=5)
                
                if auth_response.status_code == 401:
                    return {"success": False, "error": "Invalid token"}
                elif auth_response.status_code == 200:
                    return {"success": True, "message": "Server accessible with provided token"}
                else:
                    return {"success": True, "message": f"Server responding (status: {auth_response.status_code})"}
            else:
                return {"success": True, "message": "Server accessible (no token tested)"}
                
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

def main():
    """Main discovery tool entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover MyLocalAPI servers on the network")
    parser.add_argument("--port", "-p", type=int, default=1482, 
                        help="Port to scan (default: 1482)")
    parser.add_argument("--timeout", "-t", type=int, default=2,
                        help="Request timeout in seconds (default: 2)")
    parser.add_argument("--ip", action="append", 
                        help="Specific IP addresses to check (can be used multiple times)")
    parser.add_argument("--test", metavar="URL",
                        help="Test connectivity to a specific server URL")
    parser.add_argument("--token", metavar="TOKEN",
                        help="Token to use for testing authentication")
    
    args = parser.parse_args()
    
    # Create discovery instance
    discovery = MyLocalAPIDiscovery(port=args.port, timeout=args.timeout)
    
    if args.test:
        # Test specific server
        result = discovery.test_server_connectivity(args.test, args.token or "")
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
        return 0 if result["success"] else 1
    
    # Discover servers
    servers = discovery.discover_servers(custom_ips=args.ip)
    discovery.print_results()
    
    # Optional connectivity test
    if servers and args.token:
        print(f"\n🔐 Testing authentication with provided token...")
        for server in servers:
            result = discovery.test_server_connectivity(server["url"], args.token)
            status = "✅" if result["success"] else "❌"
            print(f"{status} {server['ip']}: {result.get('message', result.get('error'))}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())