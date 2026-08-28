# V-KILLB0 render harness. Independent of ORCH-drift-check.
# Arm is named by the STREHL_GATE_FLOOR_SCALE value; "" = shipping default.
param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [string]$Scale = "",
    [string[]]$Subjects = @(),
    [string]$Out = "C:\dev\strehl-out\V-KILLB0",
    [string]$Exe = "C:\dev\blog\death-of-software\projects\strehl\target-vkill\release\strehl.exe"
)

# NOT "Stop": strehl writes its banner to stderr and that would terminate.
$ErrorActionPreference = "Continue"

$dest = Join-Path $Out $Tag
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$log = Join-Path $dest "render.log"
$sha = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0,16)
$commit = (git -C "C:\dev\blog\death-of-software\projects\strehl" rev-parse --short HEAD)
"=== V-KILLB0 tag=$Tag scale='$Scale' binary=$sha commit=$commit started=$(Get-Date -Format o)" |
    Out-File -FilePath $log -Encoding utf8

if ($Scale -ne "") { $env:STREHL_GATE_FLOOR_SCALE = $Scale }
else { Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue }

$i = 0
foreach ($spec in $Subjects) {
    $i++
    # spec is "name=path"
    $parts = $spec -split "=", 2
    $name = $parts[0]
    $path = $parts[1]
    $n = (Get-ChildItem $path -File -Filter *.ARW).Count
    $target = Join-Path $dest "${name}.tiff"
    if (Test-Path $target) { "[$i] ${name} SKIP (exists)" | Tee-Object -FilePath $log -Append; continue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $banner = & $Exe stack $path -o $target --srgb 2>&1 |
        Select-String -Pattern '^averaged|^measured floor|x white|exposure|^build' |
        ForEach-Object { $_.Line.Trim() }
    $sw.Stop()
    $ok = Test-Path $target
    "[$i] ${name} frames=$n secs=$([math]::Round($sw.Elapsed.TotalSeconds,1)) ok=$ok" | Tee-Object -FilePath $log -Append
    foreach ($b in $banner) { "        $b" | Out-File -FilePath $log -Append -Encoding utf8 }
}
"=== finished=$(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
