param([Parameter(Mandatory = $true)][string]$Package)
# Deploy a desktop package over the installed Strehl (receiver stopped and started again),
# then close the window the start script opens and launch a controllable one.
$ErrorActionPreference = 'Stop'
$r = "$env:LOCALAPPDATA\StrehlCaptureReceiver"
$dst = "$env:LOCALAPPDATA\Programs\Strehl"
& "$r\Stop receiver.ps1"
Start-Sleep 1
Get-CimInstance Win32_Process -Filter "Name='Strehl.exe'" | Where-Object { $_.ExecutablePath -eq "$dst\Strehl.exe" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Confirm:$false }
Start-Sleep 1
foreach ($n in 'Strehl.exe', 'strehl-cli.exe', 'strehl-source.zip', 'desktop-package.json', 'README.md', 'REBUILD.md', 'RAW-DECODER-NOTICE.md', 'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-LGPL-2.1') {
    Copy-Item -LiteralPath (Join-Path $Package $n) -Destination (Join-Path $dst $n) -Force
}
if (Test-Path "$dst\source") { Remove-Item -LiteralPath "$dst\source" -Recurse -Force -Confirm:$false }
Copy-Item -LiteralPath "$Package\source" -Destination "$dst\source" -Recurse
& "$r\Start receiver.ps1"
Start-Sleep 3
Get-CimInstance Win32_Process -Filter "Name='Strehl.exe'" | Where-Object { -not $_.CommandLine.Contains('--capture-receiver') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Confirm:$false }
(Get-Content "$dst\desktop-package.json" | ConvertFrom-Json).build_id
