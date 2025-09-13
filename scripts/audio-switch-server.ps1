<#! 
 Audio Switch & Utility Server (PowerShell 5.1 compatible)
 ---------------------------------------------------------
 - Switch Windows default playback device (by key, name, or Command-Line Friendly ID)
 - Set device/system volume to a percent, query current volume
 - Launch streaming services with the right app/browser and focus the window
 - Fan Control integration: switch fixed/curve profiles or refresh sensors
 - Lightweight HTTP server, works great with iOS Shortcuts/Siri

 Endpoints (GET):
   /switch?key=headphones|speakers|screen&token=...
   /volume?percent=35&token=...
   /volume/current?token=...
   /device/current?token=...
   /openStreaming?service=youtube|crunchyroll|netflix|disney|prime|appletv&token=...
   /fan?percent=0..100&token=...
   /fan/profile?name=<config-basename>&token=...
   /fan/refresh?token=...
   /fan/configs?nearestTo=55&token=...
   /list?token=...&ids=1

 Requires NirSoft SoundVolumeCommandLine (svcl.exe) or SoundVolumeView in the path specified by -SvvPath.
 Fan speed requires FanControl.exe and pre-saved configuration files in -FanConfigDir.
 Tested on Windows PowerShell 5.1.
#>

param(
  [int]$Port = 8008,
  [string]$Token ="SOMEPASSWORDHERRE",
  [string]$SvvPath = $null,

  # --- Fan Control paths ---
  [string]$FanControlExe = "C:\Users\aapae\Desktop\FanControl\FanControl.exe",
  [string]$FanConfigDir  = "C:\Users\aapae\Desktop\FanControl\Configurations",

  [ValidateSet('Console','Multimedia','Communications')]
  [string]$DefaultRole = 'Console',
  [switch]$AllRoles
)

$scriptDir = if ($PSScriptRoot -and ($PSScriptRoot -ne '')) {
  $PSScriptRoot
} else {
  try { Split-Path -Parent $MyInvocation.MyCommand.Path } catch { $null }
}

# Allow override via env var or pre-set $SvvPath, otherwise auto-detect common candidates
if (-not $SvvPath) { $SvvPath = $env:SVVPATH }

if (-not $SvvPath) {
  $candidates = @()
  if ($scriptDir) {
    $candidates += (Join-Path $scriptDir 'svcl-x64\svcl.exe')
    $candidates += (Join-Path $scriptDir 'svcl.exe')
    $candidates += (Join-Path $scriptDir 'SoundVolumeView64.exe')
    $candidates += (Join-Path $scriptDir 'SoundVolumeView.exe')
  }
  # also check PATH if nothing found in script folder
  $candidates += 'svcl.exe','SoundVolumeView64.exe','SoundVolumeView.exe'

  $SvvPath = $candidates | Where-Object { 
    try { Test-Path $_ } catch { $false } 
  } | Select-Object -First 1
}

if ($SvvPath) {
  # normalize to full path if possible
  try { $SvvPath = (Resolve-Path $SvvPath -ErrorAction Stop).Path } catch {}
} else {
  throw "svcl.exe not found. Expected it in svcl-x64\svcl.exe, next to the script, or on PATH. You can also set the SVVPATH env var or pass -SvvPath explicitly."
}

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SvvPath)) { throw "Audio tool not found at: $SvvPath" }

try {
  $is64Proc = [Environment]::Is64BitProcess
  $is64OS   = [Environment]::Is64BitOperatingSystem
  if ($is64OS -and -not $is64Proc) {
    Write-Warning "You are running 32-bit PowerShell on a 64-bit OS. Launch 64-bit PowerShell for reliable results."
  }
} catch {}

$DeviceMap = @{
  "headphones" = "HyperX Cloud II Wireless\Device\Speakers\Render"
  "speakers"   = "Bose Revolve+ SoundLink\Device\Speakers\Render"
  "screen"     = "NVIDIA High Definition Audio\Device\M32UC\Render"
}

$RoleToNum = @{ "Console"=0; "Multimedia"=1; "Communications"=2 }

function Start-AppSafe {
  param(
    [Parameter(Mandatory)][string]$File,
    [string[]]$Args,
    [string]$WorkingDirectory = $null,
    [ValidateSet('Normal','Minimized','Maximized','Hidden')]
    [string]$WindowStyle = 'Normal'
  )
  if (-not (Test-Path $File)) { throw "File not found: $File" }
  $wd = if ($WorkingDirectory) { $WorkingDirectory } else { Split-Path $File -Parent }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName         = $File
  $psi.Arguments        = ($Args -join ' ')
  $psi.WorkingDirectory = $wd
  $psi.UseShellExecute  = $true
  switch ($WindowStyle) {
    'Minimized' { $psi.WindowStyle = [Diagnostics.ProcessWindowStyle]::Minimized }
    'Maximized' { $psi.WindowStyle = [Diagnostics.ProcessWindowStyle]::Maximized }
    'Hidden'    { $psi.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden }
    default     { $psi.WindowStyle = [Diagnostics.ProcessWindowStyle]::Normal }
  }
  [System.Diagnostics.Process]::Start($psi)
}


function Send-Json {
  param($ctx, [int]$status, $obj)
  try {
    $json  = ($obj | ConvertTo-Json -Compress -Depth 10)
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)

    $ctx.Response.StatusCode        = $status
    $ctx.Response.ContentType       = "application/json; charset=utf-8"
    $ctx.Response.SendChunked       = $false
    $ctx.Response.KeepAlive         = $false
    $ctx.Response.ContentLength64   = $bytes.Length
    $ctx.Response.Headers["Cache-Control"] = "no-store"

    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } catch {
    try {
      $msg = '{"error":"internal"}'
      $buf = [Text.Encoding]::UTF8.GetBytes($msg)
      $ctx.Response.StatusCode      = 500
      $ctx.Response.ContentType     = "application/json; charset=utf-8"
      $ctx.Response.SendChunked     = $false
      $ctx.Response.KeepAlive       = $false
      $ctx.Response.ContentLength64 = $buf.Length
      $ctx.Response.OutputStream.Write($buf, 0, $buf.Length)
    } catch {}
  } finally {
    try { $ctx.Response.OutputStream.Flush() } catch {}
    try { $ctx.Response.Close() } catch {}
  }
}

# --- Case-insensitive column get ---
function Get-Col {
  param($row, [string]$name)
  if (-not $row) { return $null }
  foreach ($p in $row.PSObject.Properties.Name) {
    if ([string]::Compare($p, $name, $true) -eq 0) { return $row.$p }
  }
  return $null
}

# --- Default flag detector (Render/Yes/1) ---
function Is-DefaultFlag {
  param([object]$v)
  if ($null -eq $v) { return $false }
  $s = ([string]$v).Trim().ToLower()
  if (-not $s) { return $false }
  return ($s -eq 'render' -or $s -eq 'yes' -or $s -eq '1' -or $s -like '*render*' -or $s -like '*yes*')
}

function Get-DevicesRaw {
  $exe = $SvvPath
  if (-not $exe -or -not (Test-Path $exe)) {
    $cand = @(
      (Join-Path $PSScriptRoot 'svcl.exe'),
      (Join-Path $PSScriptRoot 'SoundVolumeView64.exe'),
      (Join-Path $PSScriptRoot 'SoundVolumeView.exe')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cand) { $exe = $cand }
  }
  if (-not (Test-Path $exe)) {
    Write-Host "[DEBUG] Tool not found."
    return @{ ok=$false; rows=@(); exitCode=-1; stderr="Tool not found"; headers=@() }
  }

  $leaf   = (Split-Path -Leaf $exe)
  $isSvcl = ([string]::Equals($leaf, 'svcl.exe', 'InvariantCultureIgnoreCase'))
  Write-Host "[DEBUG] Using tool: '$exe' (svcl:$isSvcl)"

  # Helpers
  function _Parse-TSV([string[]]$lines) {
    try {
      if (-not $lines -or $lines.Count -lt 1) { return @() }
      # Sanitize header: trim, fill blanks, dedupe
      $rawHeader = $lines[0] -split "`t"
      $header = @()
      $seen = @{}
      for ($i=0; $i -lt $rawHeader.Count; $i++) {
        $h = ([string]$rawHeader[$i]).Trim()
        if ([string]::IsNullOrWhiteSpace($h)) { $h = "Col$($i+1)" }
        if ($seen.ContainsKey($h)) {
          $n = 2
          while ($seen.ContainsKey("$h$n")) { $n++ }
          $h = "$h$n"
        }
        $seen[$h] = $true
        $header += $h
      }
      $dataLines = $lines | Select-Object -Skip 1
      $data = foreach ($line in $dataLines) {
        $vals = $line -split "`t", $header.Count
        $obj = [ordered]@{}
        for ($i=0; $i -lt $header.Count; $i++) {
          $obj[$header[$i]] = (if ($i -lt $vals.Count) { $vals[$i] } else { $null })
        }
        [pscustomobject]$obj
      }
      ,$data
    } catch { @() }
  }

  function _RunStdout([string]$file, [string]$args) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $file
    $psi.Arguments = $args
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding  = [System.Text.Encoding]::UTF8
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    return @{ out=$out; err=$err; exit=$p.ExitCode }
  }

  if ($isSvcl) {
    $cols = 'Name,Device Name,Direction,Default,Default Multimedia,Default Communications,Volume Percent,Command-Line Friendly ID'

    # TSV -> stdout (empty filename)
    $r1 = _RunStdout $exe "/stab """" /Columns ""$cols"""
    if ($r1.out) {
      $lines = @($r1.out -split "(`r`n|`n)")
      $rows  = _Parse-TSV $lines
      if ($rows.Count -gt 0) {
        $hdrs = $rows[0].PSObject.Properties.Name
        Write-Host "[DEBUG] svcl /stab (stdout) rows:$($rows.Count) headers: $($hdrs -join ', ')"
        return @{ ok=$true; rows=$rows; exitCode=$r1.exit; stderr=$r1.err; headers=$hdrs }
      }
    }

    # CSV -> stdout (empty filename) with forced headers
    $r2 = _RunStdout $exe "/scomma """" /Columns ""$cols"""
    if ($r2.out) {
      $colsArr = @()
      foreach ($c in ($cols -split ',')) { $n = $c.Trim(); if ($n) { $colsArr += $n } }
      $csvLines = @($r2.out -split "(`r`n|`n)")
      $csvBody  = ($csvLines | Select-Object -Skip 1) -join "`n"  # drop original header
      try { $rows = $csvBody | ConvertFrom-Csv -Header $colsArr } catch { $rows = @() }
      if ($rows.Count -gt 0) {
        $hdrs = $rows[0].PSObject.Properties.Name
        Write-Host "[DEBUG] svcl /scomma (stdout) rows:$($rows.Count) headers: $($hdrs -join ', ')"
        return @{ ok=$true; rows=$rows; exitCode=$r2.exit; stderr=$r2.err; headers=$hdrs }
      }
    }

    Write-Host "[DEBUG] svcl produced no stdout (tsv/csv)."
    return @{ ok=$false; rows=@(); exitCode=($r1.exit,$r2.exit | Select-Object -First 1); stderr=($r1.err + $r2.err); headers=@() }
  }

  return @{ ok=$false; rows=@(); exitCode=-1; stderr="Unsupported tool for stdout mode"; headers=@() }
}

# -------------------- Fan Control helpers --------------------
function Get-FCProcess {
  Get-Process -Name FanControl -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Test-IsCurrentProcessElevated {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p  = New-Object Security.Principal.WindowsPrincipal($id)
  $p.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Start-Unelevated {
  param(
    [Parameter(Mandatory)][string]$File,
    [string[]]$Args,
    [string]$WorkingDirectory = $null
  )
  if (-not (Test-Path $File)) { throw "File not found: $File" }
  $wd = if ($WorkingDirectory) { $WorkingDirectory } else { Split-Path $File -Parent }
  $argStr = ($Args -join ' ')
  $shell = New-Object -ComObject Shell.Application
  $shell.ShellExecute($File, $argStr, $wd, 'open', 0) | Out-Null
}

# Kill any running FanControl and start fresh with target config
function Restart-FCWithConfig {
  param([Parameter(Mandatory)][string]$ConfigPath)
  if (-not (Test-Path $FanControlExe)) { throw "FanControl.exe not found: $FanControlExe" }
  if (-not (Test-Path $ConfigPath))    { throw "Config not found: $ConfigPath" }

  # Stop all running instances
  $procs = @(Get-Process -Name FanControl -ErrorAction SilentlyContinue)
  foreach ($p in $procs) {
    try { $null=$p.CloseMainWindow(); Start-Sleep -Milliseconds 200 } catch {}
    try { if (-not $p.HasExited) { $p.Kill() } } catch {}
    try { $null=$p.WaitForExit(2000) } catch {}
  }
  if (Get-Process -Name FanControl -ErrorAction SilentlyContinue) {
    & "$env:SystemRoot\System32\taskkill.exe" /F /IM FanControl.exe /T | Out-Null
    Start-Sleep -Milliseconds 200
  }

  # Start minimized with target config; if server is elevated, launch UNELEVATED for desktop context
  $args = @('-m','-c', $ConfigPath)
  $wd   = Split-Path $FanControlExe -Parent
  if (Test-IsCurrentProcessElevated) {
    Start-Unelevated -File $FanControlExe -Args $args -WorkingDirectory $wd
  } else {
    Start-AppSafe   -File $FanControlExe -Args $args -WorkingDirectory $wd -WindowStyle Minimized
  }

  Start-Sleep -Milliseconds 500
}


function Get-FCRunPath {
  $p = Get-FCProcess
  if ($p) {
    try { return $p.MainModule.FileName } catch { } # might fail under 32→64 boundary; ignore
  }
  return $FanControlExe
}

function Ensure-FanControlRunning {
  if (-not (Test-Path $FanControlExe)) { throw "FanControl.exe not found: $FanControlExe" }
  $proc = Get-FCProcess
  if ($proc) { return $proc }  # already running; do NOT minimize/steal focus
  # not running → start minimized once
  Start-AppSafe -File $FanControlExe -Args @('-m') -WindowStyle Minimized | Out-Null
  Start-Sleep -Milliseconds 500
  return (Get-FCProcess)
}

function Invoke-FC {
  param([string[]]$Args)
  # If it’s running, use the running binary path so single-instance handler picks up args.
  $exeToUse = Get-FCRunPath
  if (-not (Get-FCProcess)) { Ensure-FanControlRunning | Out-Null }  # start only if needed
  Start-AppSafe -File $exeToUse -Args $Args -WindowStyle Hidden | Out-Null
}

function Switch-FCConfig {
  param([Parameter(Mandatory)][string]$ConfigPath)
  if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
  Invoke-FC -Args @('-c', $ConfigPath)
}

function Get-FCConfigs {
  if (-not (Test-Path $FanConfigDir)) { throw "Config directory not found: $FanConfigDir" }
  Get-ChildItem -Path $FanConfigDir -Filter *.json -File
}

function Get-FCConfigSummary {
  # Requires Get-FCConfigs and $FanConfigDir to be defined
  try {
    $files = Get-FCConfigs
  } catch {
    throw "Get-FCConfigs failed: $($_.Exception.Message)"
  }

  $list = @()
  foreach ($f in $files) {
    $bn = $f.BaseName
    $pct = $null
    $hasPct = $false
    if ($bn -match '(\d{1,3})') {
      $n = [int]$Matches[1]
      if ($n -ge 0 -and $n -le 100) { $pct = $n; $hasPct = $true }
    }
    $list += [pscustomobject]@{
      basename      = $bn
      filename      = $f.Name
      fullPath      = $f.FullName
      percent       = $pct
      hasPercent    = $hasPct
      length        = $f.Length
      lastWriteTime = $f.LastWriteTime
    }
  }

  $withPct = $list | Where-Object { $_.hasPercent } | Sort-Object percent
  [pscustomobject]@{
    total       = $list.Count
    withPercent = @($withPct)
    all         = @($list)
  }
}


function Set-FCPercent {
  param([Parameter(Mandatory)][ValidateRange(0,100)][int]$Percent)
  $configs = Get-FCConfigs
  if (-not $configs) { throw "No .json configs found in $FanConfigDir" }

  $exact = $configs | Where-Object { $_.BaseName -match '(\d{1,3})' -and [int]$Matches[1] -eq $Percent } | Select-Object -First 1
  if ($exact) { Switch-FCConfig -ConfigPath $exact.FullName; return [pscustomobject]@{ requested=$Percent; applied=$Percent; config=$exact.FullName } }

  $withPct = foreach ($c in $configs) {
    if ($c.BaseName -match '(\d{1,3})') { [pscustomobject]@{ File=$c; Pct=[int]$Matches[1] } }
  }
  if (-not $withPct) { throw "Could not parse percentages from config filenames in $FanConfigDir" }

  $nearest = $withPct | Sort-Object { [math]::Abs($_.Pct - $Percent) } | Select-Object -First 1
  Switch-FCConfig -ConfigPath $nearest.File.FullName
  [pscustomobject]@{ requested=$Percent; applied=$nearest.Pct; config=$nearest.File.FullName }
}

function Set-FCProfile {
  param([Parameter(Mandatory)][string]$Name)
  $cfg = Get-FCConfigs | Where-Object { $_.BaseName -ieq $Name } | Select-Object -First 1
  if (-not $cfg) { throw "Profile not found (basename must match): $Name" }
  Switch-FCConfig -ConfigPath $cfg.FullName
  [pscustomobject]@{ profile=$Name; config=$cfg.FullName }
}

function Refresh-FC {
  Invoke-FC -Args @('-r')
  "refreshed"
}

# -------------------- Direct default device/volume (svcl) --------------------
function _ResolveTool() {
  $exe = $SvvPath
  if (-not $exe -or -not (Test-Path $exe)) {
    $cand = @(
      (Join-Path $PSScriptRoot 'svcl.exe'),
      (Join-Path $PSScriptRoot 'SoundVolumeView64.exe'),
      (Join-Path $PSScriptRoot 'SoundVolumeView.exe')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cand) { $exe = $cand }
  }
  $leaf = if ($exe) { Split-Path -Leaf $exe } else { "" }
  $isSvcl = ([string]::Equals($leaf, 'svcl.exe', 'InvariantCultureIgnoreCase'))
  return @{ exe=$exe; isSvcl=$isSvcl }
}

function Get-DefaultRenderId-Direct {
  $r = _ResolveTool
  if (-not $r.isSvcl -or -not (Test-Path $r.exe)) { return $null }

  $raw = (& $r.exe /Stdout /GetColumnValue "DefaultRenderDevice" "Command-Line Friendly ID" 2>$null)
  if (-not $raw) { $raw = (& $r.exe /GetColumnValue "DefaultRenderDevice" "Command-Line Friendly ID" 2>$null) }

  $id = Clean-CLFI ([string]$raw)
  if ($id) { Write-Host "[DEBUG] Direct default ID (clean): $id"; return $id }
  $null
}

function Get-DefaultRenderVolume-Direct {
  $r = _ResolveTool
  if (-not $r.isSvcl -or -not (Test-Path $r.exe)) { return $null }
  $out = (& $r.exe /Stdout /GetPercent "DefaultRenderDevice" 2>$null)
  if (-not $out) { $out = (& $r.exe /GetPercent "DefaultRenderDevice" 2>$null) }
  $s = ([string]$out).Trim()
  if (-not $s) { return $null }
  $s = ($s -replace '[^0-9\.\-]', '')
  if (-not $s) { return $null }
  [double]$d = 0
  if (-not [double]::TryParse($s, [ref]$d)) { return $null }
  if ($d -gt 100) { $d = $d / 10.0 }  # normalize if tool returns x10 format
  $d = [math]::Max(0, [math]::Min(100, $d))
  return [int][math]::Round($d)
}

function Get-DefaultRenderRowFromRaw {
  param($raw)
  if (-not $raw -or -not $raw.ok) { return $null }

  function _gc($row, [string]$n) {
    foreach ($p in $row.PSObject.Properties.Name) { if ([string]::Compare($p,$n,$true)-eq 0) { return $row.$p } }
    return $null
  }
  function _flag($v) {
    if ($null -eq $v) { return $false }
    $s = ([string]$v).Trim().ToLower()
    if (-not $s) { return $false }
    return ($s -eq 'render' -or $s -eq 'yes' -or $s -eq '1' -or $s -like '*render*' -or $s -like '*yes*')
  }

  $rows1 = $raw.rows | Where-Object {
    ([string](_gc $_ 'Direction')) -eq 'Render' -and
    ($null -ne (_gc $_ 'Command-Line Friendly ID')) -and
    (([string](_gc $_ 'Command-Line Friendly ID')) -match '\\Device\\')
  }
  $rows = if ($rows1 -and $rows1.Count) { $rows1 } else { $raw.rows | Where-Object { ([string](_gc $_ 'Direction')) -eq 'Render' } }
  if (-not $rows -or -not $rows.Count) { return $null }

  $roleCol = "Default $DefaultRole"
  if ($rows[0].PSObject.Properties.Name -contains $roleCol) {
    $byRole = $rows | Where-Object { _flag (_gc $_ $roleCol) } | Select-Object -First 1
    if ($byRole) { return $byRole }
  }
  if ($rows[0].PSObject.Properties.Name -contains 'Default') {
    $byDef = $rows | Where-Object { _flag (_gc $_ 'Default') } | Select-Object -First 1
    if ($byDef) { return $byDef }
  }
  $anyCols = @('Default','Default Console','Default Multimedia','Default Communications') | Where-Object { $rows[0].PSObject.Properties.Name -contains $_ }
  if ($anyCols.Count) {
    $flagged = $rows | Where-Object { foreach ($c in $anyCols) { if (_flag (_gc $_ $c)) { return $true } } $false } | Select-Object -First 1
    if ($flagged) { return $flagged }
  }
  $rows | Select-Object -First 1
}

function Build-IdFromRow {
  param($row)
  if (-not $row) { return $null }
  $clfi = $row.'Command-Line Friendly ID'
  if ($clfi) { return $clfi }
  $dev  = $row.'Device Name'
  $name = $row.'Name'
  $dir  = if ($row.Direction) { $row.Direction } else { 'Render' }
  if ($dev -and $name) { return "$dev\Device\$name\$dir" }
  $null
}

function Get-VolumeFromRow {
  param($row)
  if (-not $row) { return $null }
  $v = $null
  if ($row.PSObject.Properties.Name -contains 'Volume Percent') { $v = $row.'Volume Percent' }
  elseif ($row.PSObject.Properties.Name -contains 'Volume') { $v = $row.'Volume' }
  if ($null -eq $v) { return $null }
  $s = ([string]$v) -replace '[^0-9\.,]', '' ; if (-not $s) { return $null }
  $s = $s.Replace(',', '.')
  $d = 0.0 ; if (-not [double]::TryParse($s, [ref]$d)) { return $null }
  [int][math]::Round([math]::Max(0, [math]::Min(100, $d)))
}

function Resolve-ActiveKeyFromMap {
  param($id, $row, $deviceMap)
  if (-not $id) { return @{ key='unknown'; matched=$false; deviceName = $null; name = $null } }
  $idn = $id.Trim().ToLower()
  foreach ($k in $deviceMap.Keys) {
    $map = ([string]$deviceMap[$k]).Trim().ToLower()
    if ($map -eq $idn) {
      return @{ key=$k; matched=$true; deviceName=($row.'Device Name'); name=$row.Name }
    }
  }
  if ($row -and $row.'Device Name' -and $row.Name) {
    $syn = "$($row.'Device Name')\Device\$($row.Name)\$(if($row.Direction){$row.Direction}else{'Render'})"
    $synN = $syn.Trim().ToLower()
    $k = ($deviceMap.Keys | Where-Object { ([string]$deviceMap[$_]).Trim().ToLower() -eq $synN } | Select-Object -First 1)
    if ($k) { return @{ key=$k; matched=$true; deviceName=$row.'Device Name'; name=$row.Name } }
  }
  @{ key='unknown'; matched=$false; deviceName=($row.'Device Name'); name=$row.Name }
}

function Get-AudioSnapshot {
  $raw = Get-DevicesRaw
  if (-not $raw.ok -or -not $raw.rows -or $raw.rows.Count -eq 0) {
    return @{ ok=$false; reason='no_rows'; raw=$raw }
  }

  $row = $null
  try { $row = Get-DefaultRenderRowFromRaw $raw } catch {}

  # Direct (clean) ID + volume via svcl
  $idDirect  = Get-DefaultRenderId-Direct
  $volDirect = Get-DefaultRenderVolume-Direct

  # Prefer direct ID; fallback to row
  $id = if ($idDirect) { $idDirect } elseif ($row) { Build-IdFromRow $row } else { $null }

  # If we got an ID but no row, try to match the row by CLFI
  if ($id -and -not $row) {
    $idn = $id.Trim().ToLower()
    $row = $raw.rows | Where-Object {
      ($_.PSObject.Properties.Name -contains 'Command-Line Friendly ID') -and
      ([string]$_.('Command-Line Friendly ID')).Trim().ToLower() -eq $idn
    } | Select-Object -First 1
  }

  # Volume: prefer table, else direct
  $vol = $null
  if ($row) { $vol = Get-VolumeFromRow $row }
  if ($null -eq $vol) { $vol = $volDirect }

  if (-not $id) { return @{ ok=$false; reason='no_default_device'; raw=$raw } }

  # If still no row, synthesize friendly names from CLFI pieces
  $deviceName = $null; $name = $null
  if (-not $row) {
    $parts = $id -split '\\'
    if ($parts.Length -ge 4) {
      $deviceName = $parts[0]   # provider
      $name       = $parts[2]   # device name
    }
  } else {
    $deviceName = $row.'Device Name'
    $name       = $row.'Name'
  }

  # Map to your DeviceMap using the CLEAN ID
  $key = 'unknown'; $matched = $false
  foreach ($k in $DeviceMap.Keys) {
    if ($DeviceMap[$k].Trim().ToLower() -eq $id.Trim().ToLower()) {
      $key = $k; $matched = $true; break
    }
  }

  return @{
    ok         = $true
    raw        = @{ exitCode = $raw.exitCode; headers = $raw.headers; rowCount = @($raw.rows).Count }
    row        = $row
    id         = $id
    volume     = $vol
    activeKey  = $key
    matched    = $matched
    deviceName = $deviceName
    name       = $name
  }
}

function Get-Diagnostics {
  $raw = Get-DevicesRaw
  $env = @{
    psVersion = $PSVersionTable.PSVersion.ToString()
    is64Proc  = [Environment]::Is64BitProcess
    is64OS    = [Environment]::Is64BitOperatingSystem
    svvPath   = $SvvPath
  }
  $hdrs = if ($raw -and $raw.headers) { $raw.headers } else { @() }
  return @{
    svv = @{
      exitCode = $raw.exitCode
      stderr   = ""
      headers  = $hdrs
      rowCount = @($raw.rows).Count
    }
    env = $env
  }
}

function Clean-CLFI {
  param([string]$text)
  if (-not $text) { return $null }
  $t = $text.Trim()
  $t = ($t -replace '^(?i)\s*\d+\s+items?\s+found:\s*', '')
  $m = [regex]::Match($t, '(?im)([^\\\r\n]+)\\Device\\([^\\\r\n]+)\\Render')
  if ($m.Success) {
    return "$($m.Groups[1].Value)\Device\$($m.Groups[2].Value)\Render"
  }
  if ($t -match '\\Device\\' -and $t -match '\\Render') {
    foreach ($tok in ($t -split '\s{2,}|\s+')) {
      if ($tok -match '\\Device\\' -and $tok -match '\\Render') { return $tok.Trim() }
    }
  }
  return $t
}

# --- Legacy helpers (used by /switch, /volume set, etc.) ---
function Get-DefaultRenderRow { Get-DefaultRenderRowFromRaw (Get-DevicesRaw) }

function Get-DefaultRenderId {
  $row = Get-DefaultRenderRow
  if ($row) {
    $clfi = Get-Col $row 'Command-Line Friendly ID'
    if ($clfi) { return $clfi }
    $devName = Get-Col $row 'Device Name'
    $name    = Get-Col $row 'Name'
    $dir     = (Get-Col $row 'Direction'); if (-not $dir) { $dir = 'Render' }
    if ($devName -and $name) { return "$devName\Device\$name\$dir" }
  }
  # Fallback to direct
  return Get-DefaultRenderId-Direct
}

function Get-DefaultRenderVolume {
  $row = Get-DefaultRenderRow
  if ($row) {
    $v = $null
    if ($row.PSObject.Properties.Name -contains 'Volume Percent') { $v = $row.'Volume Percent' }
    if ($null -eq $v -and $row.PSObject.Properties.Name -contains 'Volume') { $v = $row.'Volume' }
    if ($null -ne $v) {
      $s = [string]$v
      $s = $s -replace '[^0-9\.,]', ''
      if (-not [string]::IsNullOrWhiteSpace($s)) {
        $s = $s.Replace(',', '.')
        $d = 0.0
        if ([double]::TryParse($s, [ref]$d)) {
          return [int][math]::Round([math]::Max(0, [math]::Min(100, $d)))
        }
      }
    }
  }
  # Fallback to direct
  return Get-DefaultRenderVolume-Direct
}

function Set-DefaultDevice {
  param([string]$DeviceIdentifier,[string]$Role=$DefaultRole)
  $roles = if ($AllRoles) {0..2} else {@($RoleToNum[$Role])}
  foreach ($r in $roles) { & $SvvPath /SetDefault "$DeviceIdentifier" $r | Out-Null }
}

function Set-DeviceVolumePercent {
  param([int]$Percent,[string]$Target)
  if (-not $Target) { $Target = Get-DefaultRenderId }
  & $SvvPath /SetVolume "$Target" $Percent | Out-Null
}

function List-PlaybackDevices {
  $raw = Get-DevicesRaw
  if (-not $raw.ok) {
    return @{ ok=$false; rows=@(); total=0; exitCode=$raw.exitCode; stderr=($raw.stderr) }
  }

  $pick = @()

  foreach ($r in $raw.rows) {
    # direction: prefer 'Direction' but accept alternate names like 'Type'
    $dir = Get-Col $r 'Direction'
    if (-not $dir) { $dir = Get-Col $r 'Type' }
    if (-not $dir) { $dir = '' }

    # only interested in render (playback) devices
    if ($dir -ne 'Render') { continue }

    $clfi = $null
    foreach ($p in $r.PSObject.Properties.Name) {
      if ($p -match '(?i)command.*friendly|command[-\s]*line.*friendly') {
        $clfi = Get-Col $r $p
        break
      }
    }
    if (-not $clfi) {
      foreach ($p in $r.PSObject.Properties.Name) {
        $val = Get-Col $r $p
        if ($val -and ($val -match '\\Device\\')) { $clfi = $val; break }
      }
    }

    # Volume: try 'Volume Percent' then fall back to 'Volume'
    $vol = Get-Col $r 'Volume Percent'
    if (-not $vol) { $vol = Get-Col $r 'Volume' }

    $obj = [pscustomobject]@{
      Name                       = (Get-Col $r 'Name')
      'Device Name'              = (Get-Col $r 'Device Name')
      Direction                  = $dir
      Default                    = (Get-Col $r 'Default')
      'Default Multimedia'       = (Get-Col $r 'Default Multimedia')
      'Default Communications'   = (Get-Col $r 'Default Communications')
      'Volume Percent'           = $vol
      'Command-Line Friendly ID' = $clfi
    }

    $pick += $obj
  }

  # Fallback: if no items found, try looser detection and include raw row for inspection
  if ($pick.Count -eq 0) {
    $fallback = @()
    foreach ($r in $raw.rows) {
      $dir = Get-Col $r 'Direction'; if (-not $dir) { $dir = Get-Col $r 'Type' }
      if ($dir -ne 'Render') { continue }
      $anyClfi = $null
      foreach ($p in $r.PSObject.Properties.Name) {
        $val = Get-Col $r $p
        if ($val -and ($val -match '\\Device\\')) { $anyClfi = $val; break }
      }
      $fallback += [pscustomobject]@{
        Name = Get-Col $r 'Name'
        'Device Name' = Get-Col $r 'Device Name'
        Direction = $dir
        'Command-Line Friendly ID' = $anyClfi
        Raw = $r
      }
    }
    if ($fallback.Count -gt 0) { $pick = $fallback }
  }

  return @{ ok = $true; rows = $pick; total = $pick.Count; exitCode = $raw.exitCode }
}

function Get-ActiveKeyFromMap {
  $id = Get-DefaultRenderId-Direct
  if (-not $id) { $id = Get-DefaultRenderId }  # fallback
  if (-not $id) {
    Write-Host "[DEBUG] Get-ActiveKeyFromMap: No default render ID found"
    return @{ ok=$false; id=$null; key='unknown'; matched=$false; deviceName=$null; name=$null }
  }
  $idNorm = ([string]$id).Trim().ToLower()
  foreach ($k in $DeviceMap.Keys) {
    $mapNorm = ([string]$DeviceMap[$k]).Trim().ToLower()
    if ($mapNorm -eq $idNorm) {
      $row = Get-DefaultRenderRow
      return @{
        ok=$true; id=$id; key=$k; matched=$true
        deviceName = if ($row) { $row.'Device Name' } else { $null }
        name       = if ($row) { $row.Name } else { $null }
      }
    }
  }
  $row2 = Get-DefaultRenderRow
  if ($row2) {
    $dir   = if ($row2.Direction) { $row2.Direction } else { 'Render' }
    if ($row2.'Device Name' -and $row2.Name) {
      $synth = "$($row2.'Device Name')\Device\$($row2.Name)\$dir".ToLower()
      foreach ($k in $DeviceMap.Keys) {
        if (([string]$DeviceMap[$k]).Trim().ToLower() -eq $synth) {
          return @{ ok=$true; id=$id; key=$k; matched=$true; deviceName=$row2.'Device Name'; name=$row2.Name }
        }
      }
    }
  }
  @{ ok=$true; id=$id; key='unknown'; matched=$false; deviceName=if($row2){$row2.'Device Name'}else{$null}; name=if($row2){$row2.Name}else{$null} }
}

function Get-CurrentVolumes {
  $vol = Get-DefaultRenderVolume
  if ($null -eq $vol) { return @{ ok=$false; deviceVolume=$null; systemVolume=$null } }
  $iv = [int]$vol
  @{ ok=$true; deviceVolume=$iv; systemVolume=$iv }
}

# ---- Window focusing helpers ----
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class WinAPI {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@

function Focus-ProcessWindow {
  param([System.Diagnostics.Process]$Process,[int]$TimeoutMs=3000)
  $SW_RESTORE = 9
  $sw = [Diagnostics.Stopwatch]::StartNew()
  do {
    try { $Process.Refresh() } catch {}
    $h = $Process.MainWindowHandle
    if ($h -and $h -ne [IntPtr]::Zero) {
      [void][WinAPI]::ShowWindowAsync($h, $SW_RESTORE)
      [void][WinAPI]::SetForegroundWindow($h)
      return $true
    }
    Start-Sleep -Milliseconds 100
  } while ($sw.ElapsedMilliseconds -lt $TimeoutMs)
  return $false
}

function Open-UrlInChrome {
  param([string]$Url)
  $chromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
  )
  $chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $chrome) { throw "Chrome not found." }
  $p = Start-Process -FilePath $chrome -ArgumentList "`"$Url`"" -PassThru
  [void](Focus-ProcessWindow -Process $p)
}

function Open-UrlInEdge {
  param([string]$Url)
  $edgePaths = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
  )
  $edge = $edgePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $edge) { throw "Edge not found." }
  $p = Start-Process -FilePath $edge -ArgumentList "`"$Url`"" -PassThru
  [void](Focus-ProcessWindow -Process $p)
}

function Open-AppleTVApp {
  param([string]$FallbackUrl = 'https://tv.apple.com/')
  try {
    $appMoniker = 'shell:AppsFolder\AppleInc.AppleTV_8wekyb3d8bbwe!App'
    Start-Process explorer.exe $appMoniker -ErrorAction Stop | Out-Null
    Start-Sleep -Milliseconds 500
    $p = Get-Process -Name "AppleTV" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($p) { [void](Focus-ProcessWindow -Process $p) }
  } catch {
    try { Open-UrlInEdge -Url $FallbackUrl } catch { Start-Process $FallbackUrl | Out-Null }
  }
}

function Open-StreamingService {
  param([string]$Service)
  $service = $Service.ToLower()
  switch ($service) {
    "youtube"     { Open-UrlInChrome -Url "https://www.youtube.com" }
    "crunchyroll" { Open-UrlInChrome -Url "https://www.crunchyroll.com" }
    "netflix"     { Open-UrlInEdge   -Url "https://www.netflix.com" }
    "disney"      { Open-UrlInEdge   -Url "https://www.disneyplus.com" }
    "prime"       { Open-UrlInEdge   -Url "https://www.primevideo.com" }
    "appletv"     { Open-AppleTVApp }
    default       { throw "Unknown service $service" }
  }
}

# --- HTTP listener ----------------------------------------------------------
Add-Type -AssemblyName System.Net
Add-Type -AssemblyName System.Web

$listener = New-Object System.Net.HttpListener
$prefix = "http://+:$Port/"
$listener.Prefixes.Add($prefix)
$listener.Start()
Write-Host "Audio Switch server listening on $prefix"

try { New-NetFirewallRule -DisplayName "AudioSwitch-$Port" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -ErrorAction SilentlyContinue | Out-Null } catch {}

while ($listener.IsListening) {
  $ctx = $null
  try {
    $ctx = $listener.GetContext()
    $req = $ctx.Request

    if ($req.HttpMethod -ne 'GET') { Send-Json $ctx 405 @{ error="Method not allowed" }; continue }

    $qs = [System.Web.HttpUtility]::ParseQueryString($req.Url.Query)
    $token = $qs["token"]
    if ($token -ne $Token) { Send-Json $ctx 401 @{ error="Unauthorized" }; continue }

    # Normalize + log
    $path = $req.Url.AbsolutePath.TrimEnd('/').ToLower()
    Write-Host ">> $($req.RemoteEndPoint) $($req.HttpMethod) $path"

    if ($path -eq "/switch") {
      $key = $qs["key"]; $id = $qs["id"]
      $target = if ($id) { $id } elseif ($DeviceMap.ContainsKey($key)) { $DeviceMap[$key] } else { $null }
      if (-not $target) { Send-Json $ctx 404 @{ error="Device not found" }; continue }
      Set-DefaultDevice -DeviceIdentifier $target
      Send-Json $ctx 200 @{ ok=$true; device=$target }
      continue
    }

    if ($path -eq "/volume") {
      $percentStr = $qs["percent"]
      if (-not $percentStr) { Send-Json $ctx 400 @{ error="Missing percent" }; continue }
      $pOk = [int]::TryParse($percentStr, [ref]([int]$p=0))
      if (-not $pOk -or $p -lt 0 -or $p -gt 100) { Send-Json $ctx 400 @{ error="Percent must be 0..100" }; continue }
      Set-DeviceVolumePercent -Percent $p
      Send-Json $ctx 200 @{ ok=$true; percent=$p }
      continue
    }

    if ($path -eq "/volume/current") {
      try {
        $snap = Get-AudioSnapshot
        if ($snap.ok -and $snap.volume -ne $null) {
          Send-Json $ctx 200 @{
            ok = $true
            deviceVolume = $snap.volume
            systemVolume = $snap.volume
            active = @{
              deviceId   = $snap.id
              activeKey  = $snap.activeKey
              matched    = $snap.matched
              deviceName = $snap.deviceName
              name       = $snap.name
            }
          }
        } else {
          Send-Json $ctx 500 @{
            error = "Could not get volume"
            diagnostics = @{
              reason = if ($snap.ok) { "no_volume_in_row" } else { $snap.reason }
              svv    = if ($snap.raw) { @{ exitCode = $snap.raw.exitCode; rowCount = $snap.raw.rowCount; headers = $snap.raw.headers } } else { $null }
            }
          }
        }
      } catch {
        Send-Json $ctx 500 @{ error = $_.Exception.Message }
      }
      continue
    }

    if ($path -eq "/device/current") {
      try {
        $snap = Get-AudioSnapshot
        if ($snap.ok) {
          Send-Json $ctx 200 @{
            ok        = $true
            deviceId  = $snap.id
            activeKey = $snap.activeKey
            matched   = $snap.matched
            deviceName= $snap.deviceName
            name      = $snap.name
            volumes   = @{
              deviceVolume = $snap.volume
              systemVolume = $snap.volume
            }
          }
        } else {
          Send-Json $ctx 500 @{
            error = "Could not resolve default device"
            diagnostics = @{
              reason = $snap.reason
              svv    = if ($snap.raw) { @{ exitCode = $snap.raw.exitCode; rowCount = $snap.raw.rowCount; headers = $snap.raw.headers } } else { $null }
            }
          }
        }
      } catch {
        Send-Json $ctx 500 @{ error = $_.Exception.Message }
      }
      continue
    }

    if ($path -eq "/openstreaming") {
      $service = $qs["service"]
      if (-not $service) { Send-Json $ctx 400 @{ error="Missing 'service'" }; continue }
      try { Open-StreamingService -Service $service; Send-Json $ctx 200 @{ ok=$true; service=$service } } catch { Send-Json $ctx 500 @{ error=$_.Exception.Message } }
      continue
    }

   # ---------------- Fan Control endpoints ----------------
    if ($path -eq "/fan/apply") {
      $name   = ([string]$qs["name"]).Trim()
      $pctStr = ([string]$qs["percent"]).Trim()

      try {
        if ($name) {
          if (Get-Command Set-FCProfileSmart -ErrorAction SilentlyContinue) {
            $r = Set-FCProfileSmart -Name $name
            Restart-FCWithConfig -ConfigPath $r.config
            Send-Json $ctx 200 @{ ok=$true; mode="name"; profile=$r.profile; config=$r.config; match=$r.match; restarted=$true }
          } else {
            $r = Set-FCProfile -Name $name
            Restart-FCWithConfig -ConfigPath $r.config
            Send-Json $ctx 200 @{ ok=$true; mode="name"; profile=$r.profile; config=$r.config; restarted=$true }
          }
          continue
        }

        if ($pctStr) {
          $pct = 0
          if (-not [int]::TryParse($pctStr, [ref]$pct)) { Send-Json $ctx 400 @{ error="percent must be 0..100" }; continue }
          if ($pct -lt 0 -or $pct -gt 100)            { Send-Json $ctx 400 @{ error="percent must be 0..100" }; continue }
          $r = Set-FCPercent -Percent $pct
          Restart-FCWithConfig -ConfigPath $r.config
          Send-Json $ctx 200 @{ ok=$true; mode="percent"; requested=$r.requested; applied=$r.applied; config=$r.config; restarted=$true }
          continue
        }

        Send-Json $ctx 400 @{ error="Provide name=profileBasename or percent=0..100" }
      } catch {
        Send-Json $ctx 500 @{ error="$($_.Exception.Message)" }
      }
      continue
    }


    if ($path -eq "/fan/refresh") {
      try {
        $status = Refresh-FC
        Send-Json $ctx 200 @{ ok=$true; status=$status }
      } catch {
        Send-Json $ctx 500 @{ error = "$($_.Exception.Message)" }
      }
      continue
    }

    if ($path -eq "/fan/configs") {
      try {
        $summary = Get-FCConfigSummary

        $nearest = $null
        $nearestToStr = ([string]$qs["nearestTo"]).Trim()
        if ($nearestToStr) {
          $want = 0
          if ([int]::TryParse($nearestToStr, [ref]$want)) {
            $cands = $summary.withPercent
            if ($cands -and $cands.Count -gt 0) {
              $nearest = ($cands | Sort-Object { [math]::Abs($_.percent - $want) } | Select-Object -First 1)
            }
          }
        }

        Send-Json $ctx 200 @{ ok=$true; summary=$summary; nearest=$nearest }
      } catch {
        Send-Json $ctx 500 @{ error = "$($_.Exception.Message)" }
      }
      continue
    }


    if ($path -eq "/fan/status") {
      try {
        $p = Get-FCProcess
        $exeInUse = Get-FCRunPath
        $configs  = @()
        try { $configs = (Get-FCConfigs | Select-Object -ExpandProperty BaseName) } catch { $configs = @() }
        Send-Json $ctx 200 @{
          ok       = $true
          running  = [bool]$p
          pid      = if ($p) { $p.Id } else { $null }
          exe      = $exeInUse
          started  = if ($p) { $p.StartTime } else { $null }
          configDir= $FanConfigDir
          profiles = $configs
        }
      } catch {
        Send-Json $ctx 500 @{ error = "$($_.Exception.Message)" }
      }
      continue
    }


    # -------------------------------------------------------

    if ($path -eq "/list") {
      $result = List-PlaybackDevices
      if ($result.ok) {
        Send-Json $ctx 200 @{ ok=$true; devices=$result.rows; total=$result.total }
      } else {
        Send-Json $ctx 200 @{ ok=$false; message="No devices"; exitCode=$result.exitCode; stderr=$result.stderr; total=0 }
      }
      continue
    }

    if ($path -eq "/status") {
      # use the snapshot so we only hit svcl.exe once
      $snap = Get-AudioSnapshot
      $list = List-PlaybackDevices
      Send-Json $ctx 200 @{
        ok = $true
        active = @{
          deviceId  = if ($snap.ok) { $snap.id } else { $null }
          activeKey = if ($snap.ok) { $snap.activeKey } else { 'unknown' }
          matched   = if ($snap.ok) { $snap.matched } else { $false }
          deviceName= if ($snap.ok) { $snap.deviceName } else { $null }
          name      = if ($snap.ok) { $snap.name } else { $null }
        }
        volumes = if ($snap.ok) { @{ ok=$true; deviceVolume=$snap.volume; systemVolume=$snap.volume } } else { @{ ok=$false; deviceVolume=$null; systemVolume=$null } }
        devices = if ($list.ok) { $list.rows } else { @() }
      }
      continue
    }

    if ($path -eq "/diag") {
      $diag = Get-Diagnostics
      Send-Json $ctx 200 @{ ok=$true; diagnostics=$diag }
      continue
    }

    Send-Json $ctx 404 @{ 
      error="Not found"; 
      endpoints=@(
        "/switch","/volume","/volume/current","/device/current","/openStreaming",
        "/fan","/fan/profile","/fan/apply","/fan/refresh","/fan/configs","/fan/status",
        "/list","/status","/diag"
      ) 
    }

  } catch {
    if ($ctx) {
      try {
        $inv = $_.InvocationInfo
        $where = @{
          command = $inv.MyCommand.Name
          line    = $inv.ScriptLineNumber
          pos     = $inv.PositionMessage
          lineText= $inv.Line
        }
        $diag = Get-Diagnostics
        Send-Json $ctx 500 @{ error=$_.Exception.Message; where=$where; diagnostics=$diag }
      } catch {}
    }
  }
}

$listener.Stop()
$listener.Close()