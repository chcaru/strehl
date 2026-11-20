# Render the scarab stack from all planes, every second and every fourth plane (run folders
# made by subset-run.py), with the product's default four-shot route, into scratch.
#   pwsh -NoProfile -File render-subsets.ps1 -Scratch C:\strehl-scratch
# An isolated cache keeps the user's cache untouched. Timings are indicative only (other work
# was running); the renders are for comparing detail.
param([Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Join-Path $repo 'target\release\strehl.exe'
$out = Join-Path $Scratch 'step-renders'
New-Item -ItemType Directory -Force $out | Out-Null
$env:STREHL_PIXEL_SHIFT = 'remosaic'
$env:STREHL_CACHE_DIR = Join-Path $Scratch 'step-cache'
$runs = [ordered]@{
    full = 'D:/StrehlCaptures/stack-1794786793543-11226'
    s2   = (Join-Path $Scratch 'step-s2')
    s4   = (Join-Path $Scratch 'step-s4')
}
foreach ($name in $runs.Keys) {
    $tif = Join-Path $out "$name.tif"
    if (Test-Path $tif) { Remove-Item $tif }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $runs[$name] --demosaic --out $tif *> (Join-Path $out "$name.log")
    $code = $LASTEXITCODE
    $sw.Stop()
    $sha = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash.Substring(0, 16) } else { 'NO-OUTPUT' }
    Write-Output ("{0}: exit {1}, {2:n1} s, sha {3}" -f $name, $code, $sw.Elapsed.TotalSeconds, $sha)
}
