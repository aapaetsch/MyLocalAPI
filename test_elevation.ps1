# Test elevation functionality for MyLocalAPI
# This script demonstrates the new automatic privilege elevation

Write-Host "=== MyLocalAPI Elevation Test ===" -ForegroundColor Cyan
Write-Host ""

# Check current admin status
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if ($isAdmin) {
    Write-Host "✅ Currently running as Administrator" -ForegroundColor Green
    Write-Host "The elevation feature would skip automatic elevation." -ForegroundColor Yellow
} else {
    Write-Host "❌ Not running as Administrator" -ForegroundColor Red
    Write-Host "MyLocalAPI will automatically prompt for elevation if fan control is enabled." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Testing MyLocalAPI startup..." -ForegroundColor Cyan
Write-Host ""

# Test normal startup (should prompt for elevation if needed)
Write-Host "1. Normal startup (with auto-elevation):" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Gray
Write-Host "   → Will automatically prompt for admin privileges if fan control is configured" -ForegroundColor Yellow

Write-Host ""
Write-Host "2. Skip elevation check:" -ForegroundColor White  
Write-Host "   python main.py --no-elevation" -ForegroundColor Gray
Write-Host "   → Runs without elevation check (fan control disabled)" -ForegroundColor Yellow

Write-Host ""
Write-Host "3. Force admin mode:" -ForegroundColor White
Write-Host "   run_as_admin.bat" -ForegroundColor Gray
Write-Host "   → Manually runs with admin privileges" -ForegroundColor Yellow

Write-Host ""
Write-Host "Run one of the above commands to test the elevation functionality." -ForegroundColor Cyan
Write-Host ""