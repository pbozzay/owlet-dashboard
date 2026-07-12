# Builds the frozen server sidecar and places it where Tauri expects it.
# Run from the repository root: .\desktop\build-sidecar.ps1
$ErrorActionPreference = "Stop"

.venv\Scripts\pyinstaller --onefile --name owlet-server `
  --distpath desktop\dist --workpath desktop\build --specpath desktop `
  --paths . --collect-submodules uvicorn --collect-submodules app `
  --hidden-import aiosqlite --noconfirm desktop\server_entry.py

$target = "desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force $target | Out-Null
# Tauri sidecars are resolved by target triple suffix.
Copy-Item desktop\dist\owlet-server.exe "$target\owlet-server-x86_64-pc-windows-msvc.exe" -Force
Write-Host "Sidecar ready: $target\owlet-server-x86_64-pc-windows-msvc.exe"
