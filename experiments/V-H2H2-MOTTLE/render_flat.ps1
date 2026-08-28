# The discriminating arm: is the N-dependence the EXPONENT, or is it depth?
#
# The ladder can show that scene content falls as N rises. It cannot say why.
# At least one competing explanation is strong enough that ORCH asked all three
# lanes to look for it: a COMMON-CAUSE ARTIFACT. Two lanes converged tonight, and
# they share the binary, the masters and a band-energy statistic. The obvious
# common cause is not the merge's weighting at all --
#
#   bee-3-cpl drifts 232.7 px corner-to-corner across its bracket (the tool's own
#   help says so). If the alignment residual is even slightly imperfect, then
#   averaging MORE frames averages more independent residuals, and the result is
#   softer with depth for reasons that have nothing to do with the selection
#   exponent. That story predicts the softness lane's 63-vs-32 result, predicts
#   the tone lane's collapse on the deepest subject, and predicts my ladder --
#   all three, without the exponent being involved at all. It also explains that
#   lane's odd finding that 38.5% of strehl's "noise" on bee was LOW-FREQUENCY
#   content, which is what misregistration looks like and is not what grain looks
#   like.
#
# So the exponent has to be turned OFF and the ladder re-run. `--pyramid-sharpen
# 1.0` disables the per-octave ramp and `--pyramid-exponent 0.01` flattens what
# is left, leaving the band gate in place but making the weights near-equal: a
# plain average of the admitted frames.
#
#   if scene falls with N here TOO, at about the same rate, the exponent is
#     exonerated and the cause is depth or alignment. The fix in flight would not
#     have moved it and I should say so before anyone builds it.
#   if the fall is much weaker here, the exponent is implicated and the
#     confidence-scaled fix is aimed at the right thing.
#
# Two rungs are enough for a ratio, so this costs four renders, not eight.
# ONE BINARY, same flags but the two under test, same staged inputs as the main
# ladder -- so this arm and the default arm differ in the exponent and nothing
# else.

$ErrorActionPreference = 'Stop'

$EXE  = 'C:\dev\strehl-out\V-H2H2\target\release\strehl.exe'
$SRC  = 'C:\dev\strehl-out\V-H2H2\ladder2'
$OUT  = 'C:\dev\strehl-out\V-H2H2\ladder2\flat'
$ARMS = @('n18a','n18b','n149a','n149b')

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
"binary: $((Get-FileHash $EXE -Algorithm SHA256).Hash.Substring(0,16))  (flat-exponent arm)"

foreach ($arm in $ARMS) {
    $tif = Join-Path $OUT "$arm.tiff"
    $log = Join-Path $OUT "$arm.log"
    if (Test-Path $tif) { "skip (exists): $arm"; continue }
    $n = (Get-ChildItem (Join-Path $SRC $arm) -Filter *.ARW).Count
    "--- $arm ($n frames)  $(Get-Date -Format HH:mm:ss) ---"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ErrorActionPreference = 'Continue'
    & $EXE stack (Join-Path $SRC $arm) --out $tif --linear-srgb --demosaic `
        --pyramid-exponent 0.01 --pyramid-sharpen 1.0 *> $log
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $sw.Stop()
    if ($rc -ne 0) { throw "$arm FAILED rc=$rc -- see $log" }
    "  ok in $([int]$sw.Elapsed.TotalSeconds)s"
}

# The flags must have LANDED. A flag that parses and does nothing is
# indistinguishable from one that works, and this tool's own help says the
# project has shipped that failure before. The flat arm must differ from the
# default arm on the same input; if the two renders hash the same, the exponent
# flags did nothing and this whole comparison is vacuous.
"`n--- verifying the exponent flags actually changed the pixels ---"
foreach ($arm in $ARMS) {
    $d = Join-Path 'C:\dev\strehl-out\V-H2H2\ladder2\out' "$arm.tiff"
    $f = Join-Path $OUT "$arm.tiff"
    $hd = (Get-FileHash $d -Algorithm SHA256).Hash.Substring(0, 16)
    $hf = (Get-FileHash $f -Algorithm SHA256).Hash.Substring(0, 16)
    $same = if ($hd -eq $hf) { 'IDENTICAL -- FLAGS DID NOTHING' } else { 'differ (good)' }
    "{0,-6} default {1}  flat {2}  {3}" -f $arm, $hd, $hf, $same
    if ($hd -eq $hf) { throw "$arm : the exponent flags had no effect" }
}
"DONE"
