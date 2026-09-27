# Start local server and open browser
param(
  [string]$Root = "",
  [int]$Port = 8765
)

$ErrorActionPreference = "Continue"

if ([string]::IsNullOrWhiteSpace($Root)) {
  if ($PSScriptRoot) { $Root = $PSScriptRoot }
  else { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
}
$Root = (Resolve-Path $Root).Path

$py = Join-Path $Root "homr_gui\.venv\Scripts\python.exe"
$server = Join-Path $Root "server.py"
$url = "http://127.0.0.1:$Port/"

if (-not (Test-Path $py)) {
  Write-Host "python not found: $py"
  exit 1
}

function Test-ServerUp {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 1
    return ($r.StatusCode -eq 200)
  } catch {
    return $false
  }
}

$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listening -and -not (Test-ServerUp)) {
  Write-Host "Starting server..."
  Start-Process -FilePath $py -ArgumentList "`"$server`"" -WorkingDirectory $Root -WindowStyle Minimized
}

Write-Host "Waiting for server..."
$ok = $false
for ($i = 0; $i -lt 80; $i++) {
  if (Test-ServerUp) { $ok = $true; break }
  Start-Sleep -Milliseconds 250
}

if ($ok) { Write-Host "Server ready, opening browser..." }
else { Write-Host "Server not ready yet, trying browser anyway..." }

$opened = $false
try {
  Start-Process $url
  $opened = $true
  Write-Host "Opened $url"
} catch {}

if (-not $opened) {
  try {
    Start-Process explorer.exe $url
    $opened = $true
    Write-Host "Opened via explorer $url"
  } catch {}
}

if (-not $opened) {
  foreach ($browser in @("msedge.exe", "chrome.exe", "firefox.exe")) {
    try {
      Start-Process $browser $url
      $opened = $true
      Write-Host "Opened via $browser $url"
      break
    } catch {}
  }
}

if ($opened) { exit 0 }
Write-Host "Failed to open browser. Visit: $url"
exit 1