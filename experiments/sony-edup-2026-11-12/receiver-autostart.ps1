$ErrorActionPreference = 'Stop'
$receiverDirectory = Join-Path $env:LOCALAPPDATA 'StrehlCaptureReceiver'
$receiverExecutable = Join-Path $receiverDirectory 'strehl-capture-receiver.exe'
$receiverConfiguration = Join-Path $receiverDirectory 'receiver.json'
if (-not (Test-Path -LiteralPath $receiverExecutable) -or -not (Test-Path -LiteralPath $receiverConfiguration)) {
    throw 'Strehl receiver installation or configuration is missing'
}
$existingReceiver = Get-CimInstance Win32_Process -Filter "Name = 'strehl-capture-receiver.exe'" | Where-Object { $_.ExecutablePath -eq $receiverExecutable }
if (-not $existingReceiver) {
    $receiverProcess = Start-Process -FilePath $receiverExecutable -ArgumentList '--config', ('"' + $receiverConfiguration + '"') -WorkingDirectory $receiverDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $receiverDirectory 'receiver.log') -RedirectStandardError (Join-Path $receiverDirectory 'receiver-error.log')
    $receiverProcess.Id | Set-Content -LiteralPath (Join-Path $receiverDirectory 'receiver.pid')
}
