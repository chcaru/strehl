# M100 end-to-end verification, REBASED onto the current HEAD.
#
# The first verify tree was archived from the HEAD that preceded M87's halo
# work; M87 then landed three commits in merge_cmd.rs. Everything below is
# therefore re-run against two binaries built from the SAME current-HEAD
# source tree, differing only by the M100 patch:
#   strehl-head.exe  = HEAD, unpatched
#   strehl-m100.exe  = HEAD + the M100 patch in section 4 of the doc
# READ-ONLY on D:\personal\macro.
$ErrorActionPreference = 'Continue'
$head = 'C:\dev\strehl-out\M100\strehl-head.exe'
$m100 = 'C:\dev\strehl-out\M100\strehl-m100.exe'
$out = 'C:\dev\strehl-out\M100\v2'
$log = "$out\logs"
New-Item -ItemType Directory -Force -Path $log | Out-Null
$BEE = 'D:\personal\macro\bee-3-cpl'

function Sha($p) { (Get-FileHash -Algorithm SHA256 $p).Hash }
function Run($exe, $name, $argv) {
    & $exe @argv 2> "$log\$name.err"
    if ($LASTEXITCODE -ne 0) { Write-Output ("  [{0}] exit {1}" -f $name, $LASTEXITCODE) }
}

Write-Output "================ B1: BYTE-FREEZE of the default path ================"
Write-Output "bee-3-cpl --limit 60, no flags at all. Three binaries:"
Run $head 'h-linear' @('stack', $BEE, '--limit', '60', '--out', "$out\h-linear.tif")
Run $m100 'm-linear' @('stack', $BEE, '--limit', '60', '--out', "$out\m-linear.tif")
$pre = Sha 'C:\dev\strehl-out\M100\freeze-before-linear.tif'
$h = Sha "$out\h-linear.tif"
$m = Sha "$out\m-linear.tif"
Write-Output "  pre-M87 HEAD  : $pre"
Write-Output "  current HEAD  : $h"
Write-Output "  HEAD + M100   : $m"
Write-Output ("  B1 (M100 moves no byte)    : {0}" -f $(if ($m -eq $h) { 'PASS' } else { 'FAIL' }))
Write-Output ("  bonus (M87 moved no byte)  : {0}" -f $(if ($h -eq $pre) { 'PASS' } else { 'differs' }))

Write-Output ""
Write-Output "================ B2: --exposure 0 is not a gain of one ================"
Run $head 'h-srgb' @('stack', $BEE, '--limit', '60', '--srgb', '--out', "$out\h-srgb.tif")
Run $m100 'm-srgb' @('stack', $BEE, '--limit', '60', '--srgb', '--out', "$out\m-srgb.tif")
Run $m100 'm-srgb-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--exposure', '0', '--out', "$out\m-srgb-e0.tif")
Run $head 'h-demo' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--out', "$out\h-demo.tif")
Run $m100 'm-demo' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--out', "$out\m-demo.tif")
Run $m100 'm-demo-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--exposure', '0', '--out', "$out\m-demo-e0.tif")
Write-Output "  --srgb             HEAD : $(Sha "$out\h-srgb.tif")"
Write-Output "  --srgb             M100 : $(Sha "$out\m-srgb.tif")"
Write-Output "  --srgb --exposure 0 M100: $(Sha "$out\m-srgb-e0.tif")"
Write-Output "  --srgb --demosaic  HEAD : $(Sha "$out\h-demo.tif")"
Write-Output "  --srgb --demosaic  M100 : $(Sha "$out\m-demo.tif")"
Write-Output "  ... --exposure 0   M100 : $(Sha "$out\m-demo-e0.tif")"

Write-Output ""
Write-Output "================ B6: the printed choice reproduces the file ================"
Run $m100 'auto' @('stack', $BEE, '--limit', '60', '--srgb', '--auto-exposure', '--out', "$out\auto.tif")
Get-Content "$log\auto.err" | Select-String -Pattern '^(exposure|  +(rule|reproduce|ONE|saturation))' | ForEach-Object { "  $_" }
$flag = (Get-Content "$log\auto.err" | Select-String -Pattern 'reproduce this exact file with (--exposure=\S+)').Matches.Groups[1].Value
Run $m100 'auto-repro' @('stack', $BEE, '--limit', '60', '--srgb', $flag, '--out', "$out\auto-repro.tif")
Write-Output "  --auto-exposure : $(Sha "$out\auto.tif")"
Write-Output "  $flag  : $(Sha "$out\auto-repro.tif")"

Write-Output ""
Write-Output "================ the advisory line on a plain --srgb render ================"
Get-Content "$log\m-srgb.err" | Select-String -Pattern '^(exposure|  +(thing|Nothing))' | ForEach-Object { "  $_" }
Write-Output "  and on the DEFAULT linear path (must be silent):"
$q = Get-Content "$log\m-linear.err" | Select-String -Pattern 'exposure'
Write-Output ("  {0}" -f $(if ($q) { "LEAKED: $q" } else { '(nothing, correct)' }))

Write-Output ""
Write-Output "================ B7: refusals ================"
foreach ($case in @(
    @('r-noexp', @('stack', $BEE, '--limit', '2', '--exposure', '1.5')),
    @('r-noauto', @('stack', $BEE, '--limit', '2', '--auto-exposure')),
    @('r-both', @('stack', $BEE, '--limit', '2', '--srgb', '--exposure', '1', '--auto-exposure')),
    @('r-range', @('stack', $BEE, '--limit', '2', '--srgb', '--exposure', '99')),
    @('r-nan', @('stack', $BEE, '--limit', '2', '--srgb', '--exposure', 'NaN'))
)) {
    & $m100 @($case[1]) 2> "$log\$($case[0]).err"
    $code = $LASTEXITCODE
    $msg = (Get-Content "$log\$($case[0]).err" | Select-String -Pattern '^Error:').Line
    Write-Output ("  {0,-9} exit {1}  {2}" -f $case[0], $code, $msg)
}

Write-Output ""
Write-Output "================ negative exposure, = form ================"
Run $m100 'neg' @('stack', $BEE, '--limit', '2', '--srgb', '--exposure=-1.5', '--out', "$out\neg.tif")
Get-Content "$log\neg.err" | Select-String -Pattern '^exposure' | ForEach-Object { "  $_" }
Write-Output "VERIFY2 DONE"
