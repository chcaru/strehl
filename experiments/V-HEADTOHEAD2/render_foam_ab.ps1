# V-H2H2 -- the `foam` specular-fringing discriminator, from ONE binary.
#
# THE QUESTION.  Are the coloured rims on foam's blown speculars a property of
# the SUBJECT (real colour, must not be "fixed") or of the ESTIMATOR (a merge
# or gather artifact, must be routed for fix)?
#
# THE DISCRIMINATOR.  Subject colour is invariant to how the merge gathers.
# An estimator artifact is keyed to the gather lattice and MUST move when the
# lattice changes.  `STREHL_FULLRES_GATHER` changes exactly that: arm 0
# gathers each frame from its own half-resolution CFA phase plane, arm 1
# demosaics to full sensor resolution before the warp.  Two different lattices,
# one binary, one warpmap, nothing else different.
#
# This is a STRONGER test than the one in `foam_fringe.py`, whose load-bearing
# arm (retention through the merge) cannot separate SCENE from a DETERMINISTIC
# PIPELINE DEFECT -- both are frame-invariant and both survive averaging.
#
# RULE 47: the whole invocation, including flags left at their defaults and
# every environment variable the tool reads.
#
#   binary        C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#                 (the same pin used for every other number in this lane)
#   subcommand    stack <DIR> --out <OUT> --merge pyramid --pyramid-gate 4.5
#   NOT passed    --srgb, --exposure, --auto-exposure, --limit, --resampler,
#                 --gate, --threads.  The render is LINEAR: no tone gain, no
#                 sRGB transfer, no display S-curve.  There is therefore no
#                 grade to remove and NO EXPOSURE TO PIN -- which matters here,
#                 because --auto-exposure picks a gain per image and would make
#                 any cross-arm chroma comparison meaningless.
#   env  STREHL_FULLRES_GATHER  0 / 1   <-- THE VARIABLE. Any other value panics
#                                           by design; that is intended.
#        STREHL_WARPMAP         solved ONCE for foam and reused by both arms, so
#                               registration is identical and the gather kernel
#                               is the only difference.
#        every other STREHL_*   cleared below, by name, before every render.

$ErrorActionPreference = 'Continue'
$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$root = 'C:\dev\strehl-out\V-H2H2'
$rend = "$root\renders"
$logs = "$root\logs"
$wm   = "$root\warpmaps"
$src  = 'D:\personal\macro\foam'

New-Item -ItemType Directory -Force -Path $rend, $logs, $wm | Out-Null

foreach ($v in 'STREHL_FULLRES_GATHER','STREHL_ALIGN','STREHL_WARPMAP','STREHL_FIX_HALO',
                'STREHL_MERGE','STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE',
                'STREHL_COVER','STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR') {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

# --- one alignment solve, shared by both arms -------------------------------
$map = "$wm\foam.warpmap.txt"
if (-not (Test-Path $map)) {
    Write-Host "solving warpmap for foam ..."
    $o = & $exe align $src --out $map 2>&1
    $o | Out-File -FilePath "$logs\foam-align.txt" -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "align failed, exit $LASTEXITCODE" }
}
Write-Host "warpmap: $map"

# --- the two arms -----------------------------------------------------------
foreach ($g in '0', '1') {
    $tag = "foam-g$g"
    $out = "$rend\$tag.tiff"
    if (Test-Path $out) { Write-Host "$tag exists, skipped"; continue }
    $env:STREHL_WARPMAP        = $map
    $env:STREHL_FULLRES_GATHER = $g
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $o  = & $exe stack $src --out $out --merge pyramid --pyramid-gate 4.5 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()
    $o | Out-File -FilePath "$logs\$tag.txt" -Encoding utf8
    Write-Host ("{0}: exit {1}, {2:N1} s -> {3}" -f $tag, $code, $sw.Elapsed.TotalSeconds, $out)
    if ($code -ne 0) { throw "$tag failed, exit $code" }
}

Remove-Item Env:\STREHL_FULLRES_GATHER, Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
Write-Host "done"
