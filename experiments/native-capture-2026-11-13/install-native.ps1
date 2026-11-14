[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$DesktopExe,
    [Parameter(Mandatory=$true)][string]$CaptureSettings,
    [Parameter(Mandatory=$true)][string]$ReceiverDirectory,
    [Parameter(Mandatory=$true)][string]$UserSettingsDirectory,
    [Parameter(Mandatory=$true)][string]$BackupDirectory
)
$ErrorActionPreference='Stop'
$nativeExe=(Resolve-Path -LiteralPath $DesktopExe).Path
$receiverRoot=(Resolve-Path -LiteralPath $ReceiverDirectory).Path
$packageRoot=Split-Path -Parent $nativeExe
if (!(Test-Path -LiteralPath (Join-Path $packageRoot 'source/desktop-source.json')) -or
    !(Test-Path -LiteralPath (Join-Path $packageRoot 'RAW-DECODER-NOTICE.md'))) {
    throw 'Keep the desktop source/relink kit and notices with the executable.'
}
$configPath=Join-Path $receiverRoot 'receiver.json'
$configuration=Get-Content -LiteralPath $CaptureSettings -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($configuration.receiver_config) -ne [IO.Path]::GetFullPath($configPath)) {
    throw 'Native capture settings must reuse this receiver configuration.'
}
if (Test-Path -LiteralPath $BackupDirectory) {throw 'Choose a fresh private backup directory.'}
New-Item -ItemType Directory -Path $BackupDirectory | Out-Null
$preserved=@()
foreach ($name in @('receiver.json','receiver.runs.json','Start receiver automatically.ps1','Start receiver.ps1','Stop receiver.ps1','native-desktop.json')) {
    $path=Join-Path $receiverRoot $name
    if (Test-Path -LiteralPath $path) {
        Copy-Item -LiteralPath $path -Destination (Join-Path $BackupDirectory $name)
        $preserved+=@{path=$path;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
    }
}
New-Item -ItemType Directory -Path $UserSettingsDirectory -Force | Out-Null
$settingsPath=Join-Path $UserSettingsDirectory 'capture.json'
if (Test-Path -LiteralPath $settingsPath) {
    Copy-Item -LiteralPath $settingsPath -Destination (Join-Path $BackupDirectory 'native-capture-before.json')
}
Copy-Item -LiteralPath $CaptureSettings -Destination $settingsPath
@{executable=$nativeExe} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $receiverRoot 'native-desktop.json') -Encoding utf8
$automatic=@'
$ErrorActionPreference='Stop'
$receiverDirectory=$PSScriptRoot
$configPath=Join-Path $receiverDirectory 'receiver.json'
$config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$desktop=Get-Content -LiteralPath (Join-Path $receiverDirectory 'native-desktop.json') -Raw | ConvertFrom-Json
if (!(Test-Path -LiteralPath $desktop.executable)) { throw 'The source-inclusive Strehl desktop package has moved.' }
$port=([string]$config.bind).Split(':')[-1]
try {
    $status=Invoke-RestMethod -Uri ('http://127.0.0.1:'+ $port +'/api/status') -Headers @{Authorization=('Bearer '+$config.key)} -TimeoutSec 3
    if ($status.ok) { return }
} catch { }
$process=Start-Process -FilePath $desktop.executable -ArgumentList '--capture-receiver','--config',('"'+$configPath+'"') -WorkingDirectory (Split-Path -Parent $desktop.executable) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $receiverDirectory 'receiver.log') -RedirectStandardError (Join-Path $receiverDirectory 'receiver-error.log')
$process.Id | Set-Content -LiteralPath (Join-Path $receiverDirectory 'receiver.pid')
'@
$manual=@'
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Start receiver automatically.ps1')
$desktop=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'native-desktop.json') -Raw | ConvertFrom-Json
# This is the user's interactive launcher; the receiver itself stays hidden.
Start-Process -FilePath $desktop.executable -ArgumentList '--capture' -WorkingDirectory (Split-Path -Parent $desktop.executable)
'@
$stop=@'
$ErrorActionPreference='Stop'
$desktop=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'native-desktop.json') -Raw | ConvertFrom-Json
$configPath=Join-Path $PSScriptRoot 'receiver.json'
$legacy=Join-Path $PSScriptRoot 'strehl-capture-receiver.exe'
# User-invoked stop only. Never match the interactive Strehl window.
Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -eq $legacy -or
    ($_.ExecutablePath -eq $desktop.executable -and $_.CommandLine.Contains('--capture-receiver') -and $_.CommandLine.Contains($configPath))
} | ForEach-Object { Stop-Process -Id $_.ProcessId }
'@
Set-Content -LiteralPath (Join-Path $receiverRoot 'Start receiver automatically.ps1') -Value $automatic -Encoding utf8
Set-Content -LiteralPath (Join-Path $receiverRoot 'Start receiver.ps1') -Value $manual -Encoding utf8
Set-Content -LiteralPath (Join-Path $receiverRoot 'Stop receiver.ps1') -Value $stop -Encoding utf8
# Existing sign-in registration points to the same automatic script; no new
# startup entry is created, and an already-running receiver is not terminated.
& (Join-Path $receiverRoot 'Start receiver automatically.ps1')
foreach ($name in @('receiver.json','receiver.runs.json')) {
    $before=Join-Path $BackupDirectory $name
    if ((Test-Path -LiteralPath $before) -and (Get-FileHash -LiteralPath $before).Hash -ne (Get-FileHash -LiteralPath (Join-Path $receiverRoot $name)).Hash) {
        throw "Unexpected receiver state change: $name"
    }
}
$desktopFolder=[Environment]::GetFolderPath('DesktopDirectory')
if ($desktopFolder) {
    $link=Join-Path $desktopFolder 'Strehl Capture.lnk'
    if (Test-Path -LiteralPath $link) {Copy-Item -LiteralPath $link -Destination (Join-Path $BackupDirectory 'Strehl Capture.lnk')}
    $shell=New-Object -ComObject WScript.Shell
    $shortcut=$shell.CreateShortcut($link)
    $shortcut.TargetPath=$nativeExe
    $shortcut.Arguments='--capture'
    $shortcut.WorkingDirectory=$packageRoot
    $shortcut.IconLocation=$nativeExe+',0'
    $shortcut.Save()
}
@{executable=$nativeExe;settings=$settingsPath;receiver_configuration_preserved=$true;existing_receiver_left_running=$true;preserved=$preserved} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $BackupDirectory 'installation.json') -Encoding utf8
Write-Output 'Native Capture settings and existing receiver launchers installed; current receiver left running.'
