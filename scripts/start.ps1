param(
    [ValidateRange(1024, 65535)][int]$Port = 8000,
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $probe = New-Object System.Net.Sockets.TcpClient
    try { $probe.Connect('127.0.0.1', $Port); $portBusy = $true }
    catch { $portBusy = $false }
    finally { $probe.Dispose() }
    if ($portBusy) {
        Write-Host "Port $Port is already in use. Open http://localhost:$Port/docs to check the existing server."
        Write-Host "To reload .env, stop that server with Ctrl+C in its terminal, then run this script again."
        Write-Host "Or use another port: .\scripts\start.ps1 -Port 8001"
        exit 1
    }
    if (-not (Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
        Write-Host 'Created .env. Add your provider key locally; without it Telegis uses fallback.'
    }
    if ($Python -eq 'python' -and (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        $Python = Join-Path $projectRoot '.venv/Scripts/python.exe'
    }
    & $Python -m uvicorn app.main:app --host 0.0.0.0 --port $Port --no-access-log --no-use-colors
    exit $LASTEXITCODE
}
finally { Pop-Location }
