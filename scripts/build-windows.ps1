param([switch]$WithBrowser, [switch]$OneFile)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Comando falhou: $LASTEXITCODE" } }
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    Check-Exit
}
$Python = '.venv\Scripts\python.exe'
& $Python -m pip install -r packaging/requirements-build.txt
Check-Exit
# Chromium is mandatory; -WithBrowser remains accepted for old invocations.
$BuildArgs = @('packaging/build_windows.py')
$BuildArgs += '--with-browser'
if ($OneFile) { $BuildArgs += '--onefile' }
& $Python @BuildArgs
Check-Exit
Write-Host 'Pacote gerado na pasta artifacts/.'
