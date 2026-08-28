# NEGATIVE CONTROL for the geometry finding.
#
# Measured: two renders of one subject, same binary, same flags, differing only
# in WHICH frames were in the stack, do not land on the same pixel grid. The
# disagreement is a displacement field of 3-19 px rms with a magnification
# component of 0.16-1.07%.
#
# That claim has an innocent alternative that would make it worthless: strehl
# might simply be nondeterministic, in which case the geometry differs between
# ANY two renders and the frame set has nothing to do with it. The two readings
# have opposite consequences -- one is a property of the merge's reference
# selection that other lanes must design around, the other is a bug of a
# completely different kind -- and nothing measured so far distinguishes them.
#
# So: render the SAME frame set twice, into two different files, with the same
# binary and the same flags. If the outputs are byte-identical, the renderer is
# deterministic and the geometry difference is caused by the frame set, which is
# the claim. If they differ, the claim is withdrawn.
#
# This is the cheap control that decides which of two stories is true, and it
# costs two renders of the shallowest rung.

$ErrorActionPreference = 'Stop'

$EXE = 'C:\dev\strehl-out\V-H2H2\target\release\strehl.exe'
$SRC = 'C:\dev\strehl-out\V-H2H2\ladder2\n18a'
$OUT = 'C:\dev\strehl-out\V-H2H2\ladder2\determinism'

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$n = (Get-ChildItem $SRC -Filter *.ARW).Count
"binary: $((Get-FileHash $EXE -Algorithm SHA256).Hash.Substring(0,16))"
"input : $SRC ($n frames, identical for both passes)"

foreach ($pass in @('pass1', 'pass2')) {
    $tif = Join-Path $OUT "$pass.tiff"
    if (Test-Path $tif) { "skip (exists): $pass"; continue }
    "--- $pass  $(Get-Date -Format HH:mm:ss) ---"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ErrorActionPreference = 'Continue'
    & $EXE stack $SRC --out $tif --linear-srgb --demosaic *> (Join-Path $OUT "$pass.log")
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $sw.Stop()
    if ($rc -ne 0) { throw "$pass FAILED rc=$rc" }
    "  ok in $([int]$sw.Elapsed.TotalSeconds)s"
}

$h1 = (Get-FileHash (Join-Path $OUT 'pass1.tiff') -Algorithm SHA256).Hash
$h2 = (Get-FileHash (Join-Path $OUT 'pass2.tiff') -Algorithm SHA256).Hash
"`npass1 $($h1.Substring(0,32))"
"pass2 $($h2.Substring(0,32))"
if ($h1 -eq $h2) {
    "IDENTICAL -- the renderer is deterministic on a fixed frame set, so the geometry"
    "  difference measured between different frame sets is caused by the frame set."
} else {
    "DIFFER -- the renderer is NOT deterministic. The geometry finding is withdrawn:"
    "  it cannot be attributed to the frame set until this is explained."
    exit 1
}
