$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'Web Interface/dist/index.html')) {
    Push-Location -LiteralPath 'Web Interface'
    try {
        if (-not (Test-Path -LiteralPath 'node_modules/vite/bin/vite.js')) {
            npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Write-Host 'Open http://localhost:5000 on this laptop. Press Ctrl+C to stop.'
python 'sahayak_cloud/server.py'
