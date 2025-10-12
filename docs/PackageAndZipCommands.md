## Build Clean exe from spec
python -m PyInstaller --clean --noconfirm mylocalapi.spec

## Zip exe into releases folder
powershell -NoProfile -Command "Compress-Archive -Path .\dist\MyLocalAPI.exe -DestinationPath .\releases\MyLocalAPI-1.0.5-windows-x64.zip -Force; Write-Output 'Release ZIP updated'"
