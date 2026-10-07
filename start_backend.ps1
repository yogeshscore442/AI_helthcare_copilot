param([switch]$RealAI, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $projectPython)) { throw 'Create .venv and install requirements.txt first.' }
$env:AI_ENGINE_ROOT = Join-Path $PSScriptRoot 'yogesh\healthcare_copilot_AI-Engine-main'
$env:USE_MOCK_AI = if ($RealAI) { 'false' } else { 'true' }
$env:DISABLE_CACHE = 'true'
Push-Location (Join-Path $PSScriptRoot 'praveen\backend')
try { & $projectPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port }
finally { Pop-Location }
