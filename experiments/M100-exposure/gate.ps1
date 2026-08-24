# M100: does the automatic exposure choice move when a merge PARAMETER moves?
# This is the evidence for the section 2.4 recommendation: if --gate (a
# stacking-quality knob, not a brightness knob) shifts the chosen exposure,
# then auto-exposure-on-by-default would make two renders differ in brightness
# by an amount that is not the thing under test.
# The earlier run of this in verify.ps1 produced no exposure line because
# strehl only develops when --out is given. Fixed here.
$ErrorActionPreference = 'Continue'
$exe = 'C:\dev\strehl-out\M100\vt-target\release\strehl.exe'
$out = 'C:\dev\strehl-out\M100'
$log = "$out\logs"
$BEE = 'D:\personal\macro\bee-3-cpl'

Write-Output "================ gate sensitivity of the automatic choice ================"
Write-Output "bee-3-cpl, --limit 60, --srgb --auto-exposure, gate varied"
foreach ($g in @('0.0', '1.0', '2.0', '4.0')) {
    & $exe stack $BEE --limit 60 --srgb --auto-exposure --gate $g --out "$out\gate-$g.tif" 2> "$log\gate2-$g.err"
    $code = $LASTEXITCODE
    $l = (Get-Content "$log\gate2-$g.err" | Select-String -Pattern '^exposure').Line
    Write-Output ("  gate {0} (exit {1}) -> {2}" -f $g, $code, $l)
}

Write-Output ""
Write-Output "================ frame-count sensitivity of the automatic choice ================"
Write-Output "bee-3-cpl, --srgb --auto-exposure, --limit varied"
foreach ($n in @('30', '60', '120', '299')) {
    & $exe stack $BEE --limit $n --srgb --auto-exposure --out "$out\lim-$n.tif" 2> "$log\lim-$n.err"
    $code = $LASTEXITCODE
    $l = (Get-Content "$log\lim-$n.err" | Select-String -Pattern '^exposure').Line
    Write-Output ("  limit {0} (exit {1}) -> {2}" -f $n, $code, $l)
}
Write-Output "GATE DONE"
