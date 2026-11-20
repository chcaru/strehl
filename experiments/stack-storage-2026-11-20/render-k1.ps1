# Render the first 24 scarab planes from the lossless archives and from the calibrated
# (k = 1) copy made by s7, with the product's default four-shot route, into scratch.
#   pwsh -NoProfile -File render-k1.ps1 -Scratch C:\strehl-scratch
# An isolated cache keeps the user's cache untouched.
param([Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Join-Path $repo 'target\release\strehl.exe'
$out = Join-Path $Scratch 'k1-renders'
New-Item -ItemType Directory -Force $out | Out-Null
$env:STREHL_PIXEL_SHIFT = 'remosaic'
$env:STREHL_CACHE_DIR = Join-Path $Scratch 'k1-cache'
$jobs = @(
    @{ name = 'lossless'; dir = 'D:/StrehlCaptures/stack-1794786793543-11226'; extra = @('--limit', '24') },
    @{ name = 'k1'; dir = (Join-Path $Scratch 'storage-study\scarab-k1'); extra = @() }
)
foreach ($job in $jobs) {
    $tif = Join-Path $out "$($job.name).tif"
    if (Test-Path $tif) { Remove-Item $tif }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $extra = $job.extra
    & $exe stack $job.dir --demosaic @extra --out $tif *> (Join-Path $out "$($job.name).log")
    $code = $LASTEXITCODE
    $sw.Stop()
    $sha = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash.Substring(0, 16) } else { 'NO-OUTPUT' }
    Write-Output ("{0}: exit {1}, {2:n1} s, sha {3}" -f $job.name, $code, $sw.Elapsed.TotalSeconds, $sha)
}
