# Every arm of the BUILD-HIGHLIGHT comparison, from ONE binary, in sequence.
#
# The endpoint change (Render::with_saturation) altered the binary, so the
# `before` arms rendered by the previous build are void: the project has
# measured cross-build comparisons to be untrustworthy outside the green plane.
# Everything is therefore re-rendered here, both arms, one process at a time --
# a single render peaks near 5.2 GB across four workers and two at once would
# swap.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$arms = @(
    # subject, arm, knee ("" = shipped default)
    @("foam", "before", "off"),
    @("foam", "after", ""),
    @("foam", "negctl", "0.05"),
    @("109MSDCF", "before", "off"),
    @("109MSDCF", "after", ""),
    @("coffee-bubbles", "before", "off"),
    @("coffee-bubbles", "after", ""),
    @("tweezers-cpl", "before", "off"),
    @("tweezers-cpl", "after", ""),
    @("coffee-bean", "before", "off"),
    @("coffee-bean", "after", "")
)

foreach ($a in $arms) {
    $t0 = Get-Date
    & "$here\h5_render.ps1" -Subject $a[0] -Arm $a[1] -Knee $a[2]
    if ($LASTEXITCODE -ne 0) { throw "render failed: $($a[0]) / $($a[1])" }
    Write-Output "elapsed  : $([int]((Get-Date) - $t0).TotalSeconds) s"
    Write-Output ""
}
Write-Output "ALL ARMS DONE"
