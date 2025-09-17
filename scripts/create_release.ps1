<#
.SYNOPSIS
Create a timestamped release ZIP for MyLocalAPI.

.DESCRIPTION
This script collects the built `dist` folder plus optional extras and packages them into a single ZIP file
named `MyLocalAPI-<version-or-timestamp>.zip` at the repository root (or a specified output directory).

.PARAMETER Version
Optional version string to use in the ZIP filename (e.g. 0.1.0). If omitted a timestamp will be used.

.PARAMETER SourceDir
The project root directory. Default = current directory.

.PARAMETER OutDir
Directory where a temporary release staging folder will be created. Default = <SourceDir>\release

.PARAMETER Extras
Array of extra files to include in the release ZIP. Default includes settings.json, README.md, LICENSE, PYINSTALLER_GUIDE.md

.PARAMETER IncludeSVCL
If set, the script will copy `scripts\svcl-x64` into the release if present.

.PARAMETER Overwrite
If set, overwrite existing ZIP with the same name.

.EXAMPLE
# Use a timestamped name (default)
.
\scripts\create_release.ps1

# Provide a specific version string and include svcl bundle
.
\scripts\create_release.ps1 -Version "0.1.0" -IncludeSVCL
#>
param(
    [string]$Version,
    [string]$SourceDir = (Get-Location).Path,
    [string]$OutDir = "",
    [string[]]$Extras = @('settings.json','README.md','LICENSE','PYINSTALLER_GUIDE.md'),
    [switch]$IncludeSVCL,
    [switch]$Overwrite
)

try {
    if (-not $OutDir -or $OutDir -eq '') { $OutDir = Join-Path $SourceDir 'release' }

    Write-Output "Source Dir: $SourceDir"
    Write-Output "Release staging dir: $OutDir"

    # Ensure source paths are full
    $SourceDir = (Resolve-Path $SourceDir).Path
    # Resolve OutDir in a way compatible with PowerShell 5.1 (avoid null-conditional operator)
    $resolvedOut = Resolve-Path -LiteralPath $OutDir -ErrorAction SilentlyContinue
    if ($resolvedOut) {
        $OutDir = $resolvedOut.Path
    } else {
        New-Item -ItemType Directory -Path (Join-Path $SourceDir 'release') -Force | Out-Null
        $OutDir = (Resolve-Path (Join-Path $SourceDir 'release')).Path
    }

    # Prepare staging folder
    $staging = Join-Path $OutDir 'staging'
    if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
    New-Item -ItemType Directory -Path $staging | Out-Null

    # Copy dist
    $distPath = Join-Path $SourceDir 'dist'
    if (-not (Test-Path $distPath)) {
        Write-Error "dist directory not found at $distPath. Please run your build (PyInstaller) first."; exit 2
    }
    Write-Output "Copying dist -> staging..."
    Copy-Item -Path (Join-Path $distPath '*') -Destination (Join-Path $staging 'dist') -Recurse -Force

    # Optionally copy svcl-x64 bundle
    if ($IncludeSVCL) {
        $svcl_src = Join-Path $SourceDir 'scripts\svcl-x64'
        if (Test-Path $svcl_src) {
            Write-Output "Including svcl-x64 bundle"
            New-Item -ItemType Directory -Path (Join-Path $staging 'svcl-x64') -Force | Out-Null
            Copy-Item -Path (Join-Path $svcl_src '*') -Destination (Join-Path $staging 'svcl-x64') -Recurse -Force
        } else {
            Write-Warning "svcl-x64 not found in scripts. Skipping."
        }
    } else {
        # If not explicitly requested but present, copy it into a subfolder so installers can bundle it if desired
        $svcl_src = Join-Path $SourceDir 'scripts\svcl-x64'
        if (Test-Path $svcl_src) {
            Write-Output "svcl-x64 detected in scripts. Use -IncludeSVCL to include it in the ZIP."
        }
    }

    # Copy extras
    foreach ($f in $Extras) {
        $src = Join-Path $SourceDir $f
        if (Test-Path $src) {
            Write-Output "Copying extra: $f"
            Copy-Item -Path $src -Destination $staging -Force
        } else {
            Write-Warning "Extra not found: $f"
        }
    }

    # Determine output filename
    if ($Version) {
        $tag = $Version
    } else {
        $tag = Get-Date -Format "yyyyMMdd-HHmm"
    }

    $zipName = "MyLocalAPI-$tag.zip"
    # Place release zips under the OutDir in a 'zips' subfolder to keep repository root clean
    $zipsDir = Join-Path $OutDir 'zips'
    if (-not (Test-Path $zipsDir)) { New-Item -ItemType Directory -Path $zipsDir | Out-Null }
    $zipPath = Join-Path $zipsDir $zipName

    if ((Test-Path $zipPath) -and -not $Overwrite) {
        Write-Error "Target zip already exists: $zipPath. Use -Overwrite to replace it."; exit 3
    }

    # Create zip
    Write-Output "Creating ZIP: $zipPath"
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -Force

    # Clean staging
    Remove-Item -Recurse -Force $staging

    Write-Output "Created: $zipPath"
    Write-Output "Size: $((Get-Item $zipPath).Length) bytes"
    exit 0
}
catch {
    Write-Error "Error creating release: $_"
    exit 1
}
