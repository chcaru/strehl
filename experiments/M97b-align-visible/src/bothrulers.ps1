# M97 -- re-run BOTH ruler stacks on the auto-sized instrument.
#
# The angled arms are re-measured, not carried over, because autosize() derives
# HALF_WIN/BG_MED from the measured pitch and lands a pixel or two away from the
# hand-tuned 33/301. Mixing a hand-tuned treatment with an auto-sized control
# would be exactly the kind of quiet inconsistency this milestone exists to
# catch.
#
# ROIs. Angled: the graduations lie below the engraved baseline, which runs
# diagonally; 3250..4900 x 3000..4600 is inside it everywhere. Flat-on: the
# baseline is horizontal at y~3120 and the millimetre ticks hang below it, so
# 200..6900 x 3250..4650. Both were read off the 1/8 thumbnails.
$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = 'utf-8'
$s = "experiments\M97b-align-visible\src\angstraight.py"
$o = "C:\dev\strehl-out\M97"

$sets = @(
    @{ tag = "ang";  roi = "3250,3000,4900,4600"; pre = "angruler" },
    @{ tag = "flat"; roi = "200,3250,6900,4650";  pre = "flatruler" }
)

foreach ($set in $sets) {
    $t = $set.tag; $roi = $set.roi; $p = $set.pre
    Write-Host "############ $t  ROI=$roi ############"
    foreach ($arm in @("ALIGNED", "ZOOMNULL")) {
        Write-Host "=== $t $arm ==="
        python $s measure $arm "$o\$p-$arm.tif" --roi $roi --json "$o\$t-ALIGNED-x.json".Replace("ALIGNED-x", "$arm") --overlay "$o\$t-ov-$arm.png"
    }
    Write-Host "=== $t PLACEBO ==="
    python $s measure PLACEBO "$o\$p-ALIGNED.tif" --roi $roi --json "$o\$t-PLACEBO.json"
    Write-Host "=== $t SHIFT3 ==="
    python $s plant "$o\$p-ALIGNED.tif" --shift 3.0 --roi $roi --json "$o\$t-SHIFT3.json"
    Write-Host "=== $t BENDA2 ==="
    python $s plant "$o\$p-ALIGNED.tif" --bend 2.0 --roi $roi --json "$o\$t-BENDA2.json"
    Write-Host "=== $t BENDA4 ==="
    python $s plant "$o\$p-ALIGNED.tif" --bend 4.0 --roi $roi --json "$o\$t-BENDA4.json"
    Write-Host "=== $t BENDZ4 ==="
    python $s plant "$o\$p-ZOOMNULL.tif" --bend 4.0 --roi $roi --json "$o\$t-BENDZ4.json"
}
Write-Host "=== done ==="
