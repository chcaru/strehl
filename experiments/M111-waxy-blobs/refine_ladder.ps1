# M111 -- refine the gate ladder where the Gaussian kernel actually has support.
#
# `softgate_prediction.py` reads the boolean n_eff map at gate g as the gap
# CDF evaluated at z = g/4 tolerances. The first ladder sampled
# z = 0.0625, 0.25, 1, 4, 16 -- and NOTHING between 1 and 4, which is precisely
# where the Gaussian falls from 0.607 to 0.0003. One bin spanning a factor of
# 1800 in weight makes the Stieltjes bounds useless: the seam and texture
# intervals came out at 0.96-4.87 and 1.00-2.59, overlapping, so the ladder
# could not answer the question either way.
#
# This adds z = 0.5, 0.75, 1.25, 1.5, 2, 2.5, 3, 3.5 (gates 2, 3, 5, 6, 8, 10,
# 12, 14). Beyond z = 4.71 the kernel is truncated to zero, so gate 16 already
# closes the support and no sample above it is needed.
#
# Every arm holds the byte-affecting environment identical to the first ladder
# and differs only in --gate, so the maps come from one registration and one
# pass one. STREHL_WARPMAP is pinned, which also makes every arm immune to fact
# 1446's unkeyed cache (P21: `alignment_for` reaches the poisoned path only when
# the override is unset).
#
# Exit codes are distinct: 0 all arms rendered, 3 harness failure.
$ErrorActionPreference = "Stop"
function Fail-Harness($m) { Write-Host "LADDER HARNESS ERROR: $m"; exit 3 }

$root  = "C:\dev\strehl-out\M111"
$exe   = "$root\.cargo-nc8\release\strehl.exe"
$stack = "D:\personal\macro\dry-erase-marker-head-cpl"   # READ-ONLY
$out   = "$root\render"

if (-not (Test-Path $exe)) { Fail-Harness "no binary at $exe" }

Remove-Item Env:STREHL_ALIGN            -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO         -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA   -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION    -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS  -ErrorAction SilentlyContinue
$env:STREHL_WARPMAP = "$root\marker-warpmap.txt"

$gates = @(2, 3, 5, 6, 8, 10, 12, 14)

foreach ($g in $gates) {
    $tag = "g$g"
    $dir = "$out\state-$tag"
    if (Test-Path "$dir\best_index.npy") { Write-Host "  gate $g : already present, skipping"; continue }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $env:STREHL_DUMP_MERGE_STATE = $dir
    $tif = "$out\marker-$tag.tif"

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $t0 = Get-Date
    $log = & $exe stack $stack --srgb --auto-exposure --gate $g --out $tif 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) {
        $log | Select-Object -Last 15 | ForEach-Object { Write-Host "    $_" }
        Fail-Harness "render failed at gate ${g}: exit $code (expected exactly 0)"
    }
    $secs = [int]((Get-Date) - $t0).TotalSeconds
    $npy = (Get-ChildItem $dir -Filter 'n_eff*.npy' | Select-Object -First 1).Name
    Write-Host ("  gate {0,-3}: {1,4}s  ->  {2}" -f $g, $secs, $npy)
    # The TIFF is not the artefact here; only the state maps are. Reclaim it.
    Remove-Item $tif -ErrorAction SilentlyContinue
}

Remove-Item Env:STREHL_DUMP_MERGE_STATE -ErrorAction SilentlyContinue
Write-Host "ladder complete"
exit 0
