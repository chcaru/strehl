$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $root 'outputs/sony-raw-storage-2026-11-13'
$install = Join-Path $env:LOCALAPPDATA 'StrehlCaptureReceiver'
$exe = Join-Path $install 'strehl-capture-receiver.exe'
$candidate = Join-Path $root 'target/release/strehl-capture-receiver.exe'
$configuration = Get-Content -LiteralPath (Join-Path $root 'outputs/pi-capture-2026-11-11/private/headless.json') -Raw | ConvertFrom-Json
$state = Invoke-RestMethod -Uri 'http://10.0.0.178:8787/api/state' -Headers @{ Authorization = 'Bearer ' + $configuration.pairing_key } -TimeoutSec 10
if ($state.busy -or $state.pending_control -ne 0 -or $state.storage.pending_frames -ne 0 -or $state.phase -notin @('ready','complete','stopped')) { throw 'Camera must be idle with no pending transfer before receiver update' }
$before = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$after = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
$backup = Join-Path $output 'receiver-before.exe'
if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $exe -Destination $backup }
if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $before) { throw 'Rollback copy verification failed' }
$processes = @(Get-CimInstance Win32_Process -Filter "Name = 'strehl-capture-receiver.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
if ($processes.Count -gt 1) { throw 'Unexpected duplicate receiver processes' }
foreach ($receiverProcess in $processes) {
    Stop-Process -Id $receiverProcess.ProcessId
    Wait-Process -Id $receiverProcess.ProcessId -ErrorAction SilentlyContinue
}
try {
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        try { Copy-Item -LiteralPath $candidate -Destination $exe -Force; break }
        catch { if ($attempt -eq 19) { throw }; Start-Sleep -Milliseconds 250 }
    }
    & (Join-Path $install 'Start receiver automatically.ps1')
    $receiverConfig = Get-Content -LiteralPath (Join-Path $install 'receiver.json') -Raw | ConvertFrom-Json
    $deadline = (Get-Date).AddSeconds(15)
    do {
        try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8789/api/status' -Headers @{ Authorization = 'Bearer ' + $receiverConfig.key } -TimeoutSec 2; break }
        catch { if ((Get-Date) -ge $deadline) { throw }; Start-Sleep -Milliseconds 200 }
    } while ($true)
    if ($health.compress_raw -ne $true) { throw 'New receiver did not default to compressed storage' }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $after) { throw 'Installed binary hash mismatch' }
    Copy-Item -LiteralPath (Join-Path $root 'target/release/strehl-raw-archive.exe') -Destination (Join-Path $install 'strehl-raw-archive.exe') -Force
    Copy-Item -LiteralPath (Join-Path $root 'tools/sony-control/restore-raws.ps1') -Destination $install -Force
    Copy-Item -LiteralPath (Join-Path $root 'tools/sony-control/Restore RAWs.cmd') -Destination $install -Force
    @{ compress_raw=$health.compress_raw; archive_tool_sha256=(Get-FileHash -LiteralPath (Join-Path $install 'strehl-raw-archive.exe') -Algorithm SHA256).Hash; before_sha256=$before; after_sha256=$after; backup=$backup; protocol=$health.protocol; encodings=$health.raw_encodings; destination=$health.folder; sign_in_launcher_preserved=$true } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'receiver-install.json')
    'Receiver installed; compressed storage defaults on; restore tool installed; existing settings and startup retained.'
} catch {
    # Restore only this owned receiver executable, never its configuration or RAWs.
    Get-CimInstance Win32_Process -Filter "Name = 'strehl-capture-receiver.exe'" | Where-Object { $_.ExecutablePath -eq $exe } | ForEach-Object { Stop-Process -Id $_.ProcessId; Wait-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
    Copy-Item -LiteralPath $backup -Destination $exe -Force
    & (Join-Path $install 'Start receiver automatically.ps1')
    throw
}
