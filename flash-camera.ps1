param([Parameter(Mandatory=$true)][string]$Port)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$cliCommand = Get-Command arduino-cli -ErrorAction SilentlyContinue
$cliPath = if ($cliCommand) { $cliCommand.Source } else { Join-Path $env:LOCALAPPDATA 'Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe' }
if (-not (Test-Path -LiteralPath $cliPath)) { throw 'Install Arduino IDE or add arduino-cli to PATH.' }
if (-not (Test-Path -LiteralPath 'firmware/SahayakCamera/config.h')) { throw 'Copy firmware/config.example.h to firmware/SahayakCamera/config.h and configure Wi-Fi, server address and device token.' }
& $cliPath compile --fqbn esp32:esp32:esp32cam --output-dir '.codex_artifacts/firmware-build' 'firmware/SahayakCamera'
if ($LASTEXITCODE -ne 0) { throw 'Camera compilation failed.' }
& $cliPath upload --fqbn esp32:esp32:esp32cam --port $Port --input-dir '.codex_artifacts/firmware-build' --upload-property 'upload.speed=115200'
if ($LASTEXITCODE -ne 0) { throw 'Upload failed. Check the USB cable, serial port and programming mode.' }
Write-Host 'Camera firmware uploaded. Start SAHAYAK and check that Wi-Fi frames arrive.'
