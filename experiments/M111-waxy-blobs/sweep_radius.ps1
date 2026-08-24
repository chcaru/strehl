# M111 arm E -- the REGULARISER_RADIUS sweep, the causal test of H1.
#
# H1 says the waxy plateaus are made by the merge regulariser: a 17x17 box over
# the focus field before the argmax. If that is the cause, the plateaus' linear
# scale moves with the radius and at radius 0 they dissolve into per-pixel
# speckle. If they are unmoved, H1 is dead however good the correlations look.
#
# NOT A SHIPPED PATH. `STREHL_M111_REG_RADIUS` exists only in this milestone's
# scratch build (see reg_radius.patch). `FOCUS_NOISE_SD` was measured AT radius
# 8 (facts 500, 84), so every other radius runs a gate whose unit is wrong by
# construction -- which is exactly why the sweep must also be read at matched
# admission, not only at a fixed --gate.
#
# Rule 47, the whole invocation:
#   stack   D:\personal\macro\dry-erase-marker-head-cpl, all 299 frames
#   flags   stack <dir> --srgb --exposure=-0.24 --gate 4 --out <tif>
#           --exposure is PINNED to the value --auto-exposure chose for the
#           baseline, so the arms differ in the regulariser and in nothing else.
#           --limit, --demosaic, --flat-roi, --detail-roi, --stats,
#           --target-n-eff, --index-map: all not passed.
#   STREHL_ALIGN            unset (registration ON)
#   STREHL_WARPMAP          pinned private copy (rule 45)
#   STREHL_FIX_HALO         unset ; STREHL_FIX_HALO_DELTA unset
#   STREHL_DUMP_ELECTION    unset ; STREHL_DUMP_MERGE_STATE set per arm
#   STREHL_M111_REG_RADIUS  the swept variable
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$root = "C:\dev\strehl-out\M111"
$exe = "$root\.cargo-target\release\strehl.exe"
$stack = "D:\personal\macro\dry-erase-marker-head-cpl"
$out = "$root\render"

Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
$env:STREHL_WARPMAP = "$root\marker-warpmap.txt"

$radii = @(0, 2, 4, 8, 16, 32)
foreach ($r in $radii) {
    $tag = "r$r"
    $dumpdir = "$out\state-$tag"
    $tif = "$out\marker-$tag.tif"
    if (Test-Path "$dumpdir\n_eff_gate4.00.npy") { "skip $tag (already rendered)"; continue }
    New-Item -ItemType Directory -Force -Path $dumpdir | Out-Null
    $env:STREHL_M111_REG_RADIUS = "$r"
    $env:STREHL_DUMP_MERGE_STATE = $dumpdir
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $o = & $exe stack $stack --srgb --exposure=-0.24 --gate 4 --out $tif 2>&1
    $c = $LASTEXITCODE
    $sw.Stop()
    $o | Out-String | Set-Content -Encoding utf8 "$out\marker-$tag.log"
    if ($c -ne 0) { throw "radius $r exited $c (expected 0)" }
    $ne = ($o | Select-String "^   4.00").Line
    "{0,-5} {1,7:N1}s  sha256={2}  {3}" -f $tag, $sw.Elapsed.TotalSeconds,
        (Get-FileHash $tif -Algorithm SHA256).Hash.Substring(0, 16), $ne.Trim()
}
Remove-Item Env:STREHL_M111_REG_RADIUS
Remove-Item Env:STREHL_DUMP_MERGE_STATE
"sweep done"
