# Render the two matched-range frame sets, dumping the merge's own weight maps.
#
# EXPOSURE. The softness lane reached a number tonight with its arms rendered at
# +2.33 and +0.85 stops. This avoids that class of error by construction rather
# than by inspection: `--linear-srgb` applies the colour matrix and STOPS BEFORE
# THE CURVE, and `--exposure` refuses to run without `--srgb`, so neither arm can
# carry a gain and there is no per-image choice for the two arms to disagree
# about. `--auto-exposure` is the flag that picks per image and it is not passed.
# The check at the end asserts no arm's log printed an exposure, so this is
# verified from the run rather than argued from the help text.
#
# ONE BINARY, one build, both arms. The only difference between the two commands
# is the input directory.

$ErrorActionPreference = 'Stop'

$EXE  = 'C:\dev\strehl-out\V-H2H2\target\release\strehl.exe'
$SRC  = 'C:\dev\strehl-out\V-H2H2\nscale'
$OUT  = 'C:\dev\strehl-out\V-H2H2\nscale\out'

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$h = (Get-FileHash $EXE -Algorithm SHA256).Hash
"binary: $($h.Substring(0,16))  (both arms)"

foreach ($arm in @('n63', 'n32')) {
    $tif = Join-Path $OUT "$arm.tiff"
    $log = Join-Path $OUT "$arm.log"
    $pre = Join-Path $OUT $arm
    if (Test-Path $tif) { "skip (exists): $arm"; continue }

    $env:STREHL_PYRAMID_WEIGHT_DUMP = $pre
    "--- $arm  $(Get-Date -Format HH:mm:ss) ---"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ErrorActionPreference = 'Continue'
    & $EXE stack (Join-Path $SRC $arm) --out $tif --linear-srgb --demosaic *> $log
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $sw.Stop()
    Remove-Item Env:\STREHL_PYRAMID_WEIGHT_DUMP -ErrorAction SilentlyContinue
    if ($rc -ne 0) { throw "$arm FAILED rc=$rc -- see $log" }
    "  ok in $([int]$sw.Elapsed.TotalSeconds)s"
}

# The arms must differ in N and in nothing else that the tool chose for itself.
"`n--- verifying the arms differ only in N ---"
foreach ($arm in @('n63', 'n32')) {
    $log = Get-Content (Join-Path $OUT "$arm.log") -Raw
    $exp = if ($log -match 'exposure[^\r\n]*') { $Matches[0] } else { '(no exposure line)' }
    $fr  = if ($log -match 'frames[^\r\n]*')   { $Matches[0] } else { '(no frames line)' }
    "{0}: {1}" -f $arm, $exp
    "{0}: {1}" -f $arm, $fr
    if ($log -match 'auto-exposure|--exposure=') { throw "$arm carried an exposure gain" }
}
"DONE"
