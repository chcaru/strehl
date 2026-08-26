# Every measurement of the BUILD-HIGHLIGHT comparison, over every arm.
#
# Run after h7_allarms.ps1. One binary produced every file being compared, so
# these are within-build comparisons; the project has measured cross-build ones
# to be void outside the green plane.

$ErrorActionPreference = "Stop"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$r = "C:\dev\strehl-out\BUILD-HIGHLIGHT\renders"

$pairs = @(
    @("foam", "$r\foam-before.tif", "$r\foam-after.tif"),
    # The negative control: the same instrument, the same before arm, an
    # exaggerated knee. A statistic that has never been shown to move is not
    # evidence, so this pair exists to move it.
    @("foam-NEGCTL", "$r\foam-before.tif", "$r\foam-negctl.tif"),
    # The null / placebo: no blown highlights, so nothing may move.
    @("109MSDCF-NULL", "$r\109MSDCF-before.tif", "$r\109MSDCF-after.tif"),
    @("coffee-bubbles", "$r\coffee-bubbles-before.tif", "$r\coffee-bubbles-after.tif"),
    @("tweezers-cpl", "$r\tweezers-cpl-before.tif", "$r\tweezers-cpl-after.tif"),
    @("coffee-bean", "$r\coffee-bean-before.tif", "$r\coffee-bean-after.tif")
)

foreach ($p in $pairs) {
    & python "$repo\experiments\BUILD-HIGHLIGHT\src\h6_compare.py" $p[0] $p[1] $p[2]
    if ($LASTEXITCODE -ne 0) { Write-Output "  !! h6 exited $LASTEXITCODE on $($p[0])" }
    Write-Output ""
}
Write-Output "ALL MEASUREMENTS DONE"
