# Proof for thinning (decision D2): render a stack from all its planes and from every second
# plane, and compare. Nothing is deleted from the capture: the every-second-plane run is
# made of hard links to its archives (subset-run.py --link-from), removed afterwards.
#   pwsh -NoProfile -File prove-thinning.ps1 -Run D:/StrehlCaptures/<run> -Name <label> -Scratch C:\strehl-scratch
param([Parameter(Mandatory)][string]$Run, [Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Join-Path $repo 'target\release\strehl.exe'
$out = Join-Path $Scratch "thin-$Name"
New-Item -ItemType Directory -Force $out | Out-Null
$runRoot = Split-Path $Run -Parent
$subset = Join-Path $runRoot "thin-proof-$Name"
python (Join-Path $repo 'experiments\capture-pipeline-2026-11-20\subset-run.py') $Run $subset 2 0 --link-from $Run
$shots = (Get-Content (Join-Path $Run 'manifest.json') -Raw | ConvertFrom-Json).pixel_shift_shots
if ($shots -eq 4) { $env:STREHL_PIXEL_SHIFT = 'remosaic' } else { Remove-Item Env:STREHL_PIXEL_SHIFT -ErrorAction SilentlyContinue }
$env:STREHL_CACHE_DIR = Join-Path $Scratch "thin-cache-$Name"
try {
    foreach ($job in @(@{ n = 'full'; d = $Run }, @{ n = 's2'; d = $subset })) {
        $tif = Join-Path $out "$($job.n).tif"
        $sw = [Diagnostics.Stopwatch]::StartNew()
        & $exe stack $job.d --demosaic --out $tif *> (Join-Path $out "$($job.n).log")
        $code = $LASTEXITCODE
        Write-Output ("{0} {1}: exit {2}, {3:n1} s" -f $Name, $job.n, $code, $sw.Elapsed.TotalSeconds)
    }
    python (Join-Path $repo 'experiments\capture-pipeline-2026-11-20\compare-step-renders-2.py') $out (Join-Path $out 'crops') 'full,s2'
} finally {
    Remove-Item -Recurse -Force $subset
    Remove-Item -Recurse -Force $env:STREHL_CACHE_DIR -ErrorAction SilentlyContinue
}
