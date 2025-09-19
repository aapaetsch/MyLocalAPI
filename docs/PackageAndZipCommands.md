## Build Clean exe from spec
c:/Users/aapae/Documents/Projects/MyLocalAPI/venv/Scripts/python.exe -m PyInstaller --clean --noconfirm mylocalapi.spec

## Zip exe into releases folder
powershell -NoProfile -Command "Compress-Archive -Path .\dist\MyLocalAPI.exe -DestinationPath .\releases\MyLocalAPI-1.0.5-windows-x64.zip -Force; Write-Output 'Release ZIP updated'"