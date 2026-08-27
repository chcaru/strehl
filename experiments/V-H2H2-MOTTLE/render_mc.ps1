# Render one subject at several values of STREHL_PYRAMID_MEAN_COARSE.
#
# ZERO CODE EDITS.  Every arm is the SEALED SHIP-V4 PIN, hash-verified, with
# exactly one environment variable differing between arms.  That is the same
# discipline STREHL_FULLRES_GATHER was measured under and it is the reason two
# builds made hours apart cannot be mistaken for an A/B here.
#
# The render recipe is V-GATHER/certmeasure.py's, reused rather than reinvented:
#   --linear-srgb --demosaic
# --linear-srgb DOES NOT IMPLY --demosaic (V-H2H2 section 8.9), so --demosaic is
# passed explicitly and the lattice is read back FROM THE FILE afterwards.
#
# An unrecognised STREHL_PYRAMID_MEAN_COARSE value PANICS by design
# (pyramid.rs mean_coarse_default).  That is the liveness proof for the switch
# and this script asserts it before trusting any arm.

$ErrorActionPreference = 'Stop'

$PIN  = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$WANT = '44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490'
$RAW  = 'D:\personal\macro'
$OUT  = 'C:\dev\strehl-out\V-H2H2\mottle'

$subject = $args[0]
$levels  = if ($args.Count -gt 1) { $args[1..($args.Count-1)] } else { @(0,1,2,3) }

$got = (Get-FileHash $PIN -Algorithm SHA256).Hash
if ($got -ne $WANT) { throw "PIN HASH MISMATCH: $got" }
"pin verified: $($got.Substring(0,16))"

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

# Liveness: the switch must be READ.  A value that names no integer must panic.
# Without this an unset-and-ignored switch is indistinguishable from one that works.
# NOTE: strehl writes a build banner to stderr on every run, so this MUST NOT be
# run under `$ErrorActionPreference='Stop'` with an inline capture -- PowerShell
# promotes any native stderr write to a terminating error and the probe dies
# before it can read the exit code.  Log to a file and gate on $LASTEXITCODE.
$probeLog = Join-Path $OUT 'liveness.log'
$env:STREHL_PYRAMID_MEAN_COARSE = 'not-an-integer'
$ErrorActionPreference = 'Continue'
& $PIN stack (Join-Path $RAW $subject) --out (Join-Path $OUT 'liveness.tif') --linear-srgb --demosaic --limit 2 *> $probeLog
$rc = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
Remove-Item Env:\STREHL_PYRAMID_MEAN_COARSE -ErrorAction SilentlyContinue
$probe = (Get-Content $probeLog -Raw)
if ($rc -eq 0) { throw "LIVENESS FAILED: a bad STREHL_PYRAMID_MEAN_COARSE was accepted (rc=0). The switch is not read." }
if ($probe -notmatch 'STREHL_PYRAMID_MEAN_COARSE') { throw "LIVENESS FAILED: rc=$rc but the message never names the switch:`n$probe" }
"liveness: bad value rejected, rc=$rc, message names the switch"
Remove-Item (Join-Path $OUT 'liveness.tif') -ErrorAction SilentlyContinue

foreach ($mc in $levels) {
    $tif = Join-Path $OUT ("{0}--mc{1}.tiff" -f $subject, $mc)
    $log = Join-Path $OUT ("{0}--mc{1}.log"  -f $subject, $mc)
    if (Test-Path $tif) { "skip (exists): $tif"; continue }

    if ($mc -eq 'unset') {
        Remove-Item Env:\STREHL_PYRAMID_MEAN_COARSE -ErrorAction SilentlyContinue
    } else {
        $env:STREHL_PYRAMID_MEAN_COARSE = "$mc"
    }
    "--- $subject  mean_coarse=$mc  $(Get-Date -Format HH:mm:ss) ---"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ErrorActionPreference = 'Continue'
    & $PIN stack (Join-Path $RAW $subject) --out $tif --linear-srgb --demosaic *> $log
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $sw.Stop()
    Remove-Item Env:\STREHL_PYRAMID_MEAN_COARSE -ErrorAction SilentlyContinue
    if ($rc -ne 0) { "  FAILED rc=$rc -- see $log"; continue }
    "  ok in $([int]$sw.Elapsed.TotalSeconds)s -> $tif"
}
"DONE $subject"
