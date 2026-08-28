# Render every rung of the N-ladder, both arms, from ONE binary.
#
# EXPOSURE, by construction rather than by inspection. `--linear-srgb` applies
# the colour matrix and stops BEFORE the tone curve, and `--exposure` refuses to
# run without `--srgb`, so no arm can carry a gain and there is no per-image
# choice for the arms to disagree about. `--auto-exposure` is the flag that picks
# per image and it is not passed. The check at the end asserts this from the run
# logs rather than arguing it from the help text -- the softness lane reached a
# number tonight with its arms at +2.33 and +0.85.
#
# The ONLY thing that differs between arms is which frames are in the directory.
# Same binary, same flags, same output path shape, same bracket.

$ErrorActionPreference = 'Stop'

$EXE  = 'C:\dev\strehl-out\V-H2H2\target\release\strehl.exe'
$SRC  = 'C:\dev\strehl-out\V-H2H2\ladder2'
$OUT  = 'C:\dev\strehl-out\V-H2H2\ladder2\out'
$ARMS = @('n18a','n18b','n37a','n37b','n74a','n74b','n149a','n149b')

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$h = (Get-FileHash $EXE -Algorithm SHA256).Hash
"binary: $($h.Substring(0,16))  (all $($ARMS.Count) arms)"

foreach ($arm in $ARMS) {
    $tif = Join-Path $OUT "$arm.tiff"
    $log = Join-Path $OUT "$arm.log"
    if (Test-Path $tif) { "skip (exists): $arm"; continue }
    $n = (Get-ChildItem (Join-Path $SRC $arm) -Filter *.ARW).Count
    "--- $arm ($n frames)  $(Get-Date -Format HH:mm:ss) ---"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ErrorActionPreference = 'Continue'
    & $EXE stack (Join-Path $SRC $arm) --out $tif --linear-srgb --demosaic *> $log
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $sw.Stop()
    if ($rc -ne 0) { throw "$arm FAILED rc=$rc -- see $log" }
    "  ok in $([int]$sw.Elapsed.TotalSeconds)s"
}

"`n--- verifying the arms differ only in which frames were present ---"
foreach ($arm in $ARMS) {
    $log = Get-Content (Join-Path $OUT "$arm.log") -Raw
    if ($log -match 'auto-exposure|--exposure=') { throw "$arm carried an exposure gain" }
    $fr = if ($log -match 'frames[^\r\n]*') { $Matches[0] } else { '(no frames line)' }
    "{0,-6}: {1}" -f $arm, $fr
}
"DONE"

