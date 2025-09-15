# MyLocalAPI Network Access Setup Guide

## Overview
This guide helps you configure network access to your MyLocalAPI server so other devices on your network can use the gaming, audio, and fan control endpoints.

## Step 1: Find Your Computer's IP Address

### Option A: Using Command Prompt
1. Press `Win + R`, type `cmd`, press Enter
2. Run: `ipconfig`
3. Look for your active network adapter (usually "Wireless LAN adapter Wi-Fi" or "Ethernet adapter")
4. Note the **IPv4 Address** (e.g., `192.168.1.100`)

### Option B: Using PowerShell
1. Press `Win + X`, select "Windows PowerShell"
2. Run: `Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*" -or $_.IPAddress -like "172.*"}`
3. Look for the IP address that's not `127.0.0.1`

## Step 2: Configure Windows Firewall

### Option A: Automatic Rule Creation (Recommended)
When you first run MyLocalAPI, Windows will likely prompt you to allow network access. Click "Allow access" for both private and public networks.

### Option B: Manual Firewall Configuration
1. Press `Win + R`, type `wf.msc`, press Enter
2. Click "Inbound Rules" in the left panel
3. Click "New Rule..." in the right panel
4. Select "Port" → Next
5. Select "TCP" → "Specific local ports" → Enter `5000` → Next
6. Select "Allow the connection" → Next
7. Check all profiles (Domain, Private, Public) → Next
8. Name: "MyLocalAPI Server" → Finish

## Step 3: Test Network Access

### From Another Device
1. Make sure both devices are on the same network (Wi-Fi/Ethernet)
2. Open a web browser on the other device
3. Navigate to: `http://YOUR_IP_ADDRESS:5000/health`
   - Example: `http://192.168.1.100:5000/health`
4. You should see: `{"status": "healthy"}`

### Common Issues and Solutions

#### "This site can't be reached" or Connection Refused
- **Check Firewall**: Make sure Windows Firewall allows port 5000
- **Check MyLocalAPI**: Ensure the server is running and shows "Running on all interfaces (0.0.0.0:5000)"
- **Check Network**: Both devices must be on the same local network

#### "Connection timed out"
- **Router Settings**: Some routers block device-to-device communication
- **Network Profile**: Make sure your network is set to "Private" not "Public"
  - Go to Settings → Network & Internet → Wi-Fi → Your Network → Change to "Private"

#### Fan Control Not Working from Network
- **Admin Rights**: MyLocalAPI must be running as administrator for fan control
- **Service Dependency**: FanControl.exe must be available and configured

## Step 4: Advanced Configuration

### Different Port
If port 5000 is already in use, you can change it:
1. Edit `settings.json`
2. Change `"server": {"port": 5000}` to your preferred port
3. Update firewall rules accordingly
4. Restart MyLocalAPI

### Security Considerations

#### For Home Network Use (Recommended)
- Keep default settings
- Use only on private/trusted networks
- Consider MAC address filtering on your router

#### For Public/Guest Network Use (Advanced)
- Add authentication to endpoints
- Use HTTPS instead of HTTP
- Implement rate limiting
- Consider VPN access instead

## API Endpoints Reference

Once network access is working, other devices can use:

### Gaming Control
- `GET http://YOUR_IP:5000/gaming/games` - List configured games
- `POST http://YOUR_IP:5000/gaming/launch` - Launch a game
  ```json
  {"game_id": "steam_game_1"}
  ```

### Audio Control
- `GET http://YOUR_IP:5000/audio/devices` - List audio devices
- `POST http://YOUR_IP:5000/audio/set_default` - Set default device
  ```json
  {"device_name": "Speakers"}
  ```

### Fan Control (Requires Admin)
- `GET http://YOUR_IP:5000/fan/profiles` - List fan profiles
- `POST http://YOUR_IP:5000/fan/apply` - Apply fan profile
  ```json
  {"profile": "gaming"}
  ```

### Health Check
- `GET http://YOUR_IP:5000/health` - Server status

## Mobile App Integration

Popular apps for making HTTP requests to your MyLocalAPI:

### Android
- **HTTP Request Shortcuts** - Create home screen shortcuts for common actions
- **Tasker** - Automate requests based on conditions
- **IFTTT/Webhooks** - Integrate with smart home systems

### iOS
- **Shortcuts App** - Create Siri shortcuts for voice control
- **Workflow Apps** - Various apps for HTTP automation

### Example Mobile Shortcut
Create a shortcut that sends a POST request to launch your favorite game:
- URL: `http://192.168.1.100:5000/gaming/launch`
- Method: POST
- Body: `{"game_id": "steam_game_1"}`
- Headers: `Content-Type: application/json`

## Troubleshooting Checklist

- [ ] MyLocalAPI server is running
- [ ] Windows Firewall allows port 5000
- [ ] Both devices on same network
- [ ] Correct IP address used
- [ ] Network profile set to "Private"
- [ ] For fan control: Running as administrator
- [ ] Router allows device-to-device communication

## Support

If you continue having issues:
1. Check the MyLocalAPI console for error messages
2. Test with `curl` or Postman to isolate client vs server issues
3. Verify network connectivity with `ping YOUR_IP_ADDRESS`
4. Check Windows Event Viewer for firewall/security blocks