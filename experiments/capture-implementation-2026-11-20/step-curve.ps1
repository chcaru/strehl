# How coarse can the focus step get? Render one finely captured stack from every k-th plane
# (k = 1, 2, 3, 4, 6, 8, ...) and keep the renders for step-curve-analyse.py. The subsets are
# hard links to the capture's archives (subset-run.py --link-from), removed afterwards; the
# capture is only read. The render is the CLI default (pyramid merge), as in prove-thinning.ps1.
#   pwsh -NoProfile -File step-curve.ps1 -Run D:/StrehlCaptures/<run> -Name <label> -Strides '1,2,3,4,6,8' -Scratch C:\strehl-scratch
# -Strides is a comma-separated string: `pwsh -File` would pass 1,2,3 to an [int[]] as 123.
param([Parameter(Mandatory)][string]$Run, [Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Strides,
      [Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$ks = @($Strides.Split(',') | ForEach-Object { [int]$_ })
$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Join-Path $repo 'target\release\strehl.exe'
$out = Join-Path $Scratch "step-$Name"
New-Item -ItemType Directory -Force $out | Out-Null
$runRoot = Split-Path $Run -Parent
$shots = (Get-Content (Join-Path $Run 'manifest.json') -Raw | ConvertFrom-Json).pixel_shift_shots
if ($shots -eq 4) { $env:STREHL_PIXEL_SHIFT = 'remosaic' } else { Remove-Item Env:STREHL_PIXEL_SHIFT -ErrorAction SilentlyContinue }
foreach ($k in $ks) {
    $dir = $Run
    $subset = $null
    if ($k -gt 1) {
        $subset = Join-Path $runRoot "step-curve-$Name-s$k"
        python (Join-Path $repo 'experiments\capture-pipeline-2026-11-20\subset-run.py') $Run $subset $k 0 --link-from $Run
        $dir = $subset
    }
    # a cache per render: nothing measured for one subset is reused by another
    $env:STREHL_CACHE_DIR = Join-Path $Scratch "step-cache-$Name-s$k"
    try {
        $tif = Join-Path $out "s$k.tif"
        $sw = [Diagnostics.Stopwatch]::StartNew()
        & $exe stack $dir --demosaic --out $tif *> (Join-Path $out "s$k.log")
        $code = $LASTEXITCODE
        Write-Output ("{0} every {1}: exit {2}, {3:n1} s" -f $Name, $k, $code, $sw.Elapsed.TotalSeconds)
        if ($code -ne 0) { throw "render failed" }
    } finally {
        if ($subset) { Remove-Item -Recurse -Force $subset }
        Remove-Item -Recurse -Force $env:STREHL_CACHE_DIR -ErrorAction SilentlyContinue
    }
}
