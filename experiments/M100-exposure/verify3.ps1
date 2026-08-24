# M100 verification, rebased a SECOND time onto 894f9f7 (post-M95).
#
# M95 landed a chroma-cositing fix in image_out.rs after the first rebase, and
# that changes the BINNED --srgb render's bytes. It does not touch merge_cmd.rs,
# main.rs or color.rs, so the M100 patch applies unchanged and the CHOSEN
# exposures cannot move (they are computed in merge_cmd.rs, before image_out).
# What can move is the clipping accounting, so everything is re-measured here.
#
# Two binaries from the same tree, differing only by the M100 patch.
# READ-ONLY on D:\personal\macro.
$ErrorActionPreference = 'Continue'
$head = 'C:\dev\strehl-out\M100\v3\strehl-head.exe'
$m100 = 'C:\dev\strehl-out\M100\v3\strehl-m100.exe'
$out = 'C:\dev\strehl-out\M100\v3'
$log = "$out\logs"
New-Item -ItemType Directory -Force -Path $log | Out-Null
$BEE = 'D:\personal\macro\bee-3-cpl'

function Sha($p) { (Get-FileHash -Algorithm SHA256 $p).Hash }
function Run($exe, $name, $argv) {
    & $exe @argv 2> "$log\$name.err"
    if ($LASTEXITCODE -ne 0) { Write-Output ("  [{0}] exit {1}" -f $name, $LASTEXITCODE) }
}
function Line($name, $pat) {
    $raw = [IO.File]::ReadAllBytes("$log\$name.err")
    $t = if ($raw[0] -eq 255 -and $raw[1] -eq 254) { [Text.Encoding]::Unicode.GetString($raw) }
         else { [Text.Encoding]::UTF8.GetString($raw) }
    ($t -split "`r?`n") | Where-Object { $_ -match $pat }
}

Write-Output "================ B1: BYTE-FREEZE of the default path ================"
Run $head 'h-linear' @('stack', $BEE, '--limit', '60', '--out', "$out\h-linear.tif")
Run $m100 'm-linear' @('stack', $BEE, '--limit', '60', '--out', "$out\m-linear.tif")
Write-Output "  pre-M87 HEAD  : $(Sha 'C:\dev\strehl-out\M100\freeze-before-linear.tif')"
Write-Output "  HEAD 894f9f7  : $(Sha "$out\h-linear.tif")"
Write-Output "  HEAD + M100   : $(Sha "$out\m-linear.tif")"
Write-Output ("  B1 : {0}" -f $(if ((Sha "$out\m-linear.tif") -eq (Sha "$out\h-linear.tif")) { 'PASS' } else { 'FAIL' }))
$leak = Line 'm-linear' '^exposure'
Write-Output ("  advisory silent on the measurement path : {0}" -f $(if ($leak) { "LEAK: $leak" } else { 'yes' }))

Write-Output ""
Write-Output "================ B2: --exposure 0 round trip ================"
Run $head 'h-srgb' @('stack', $BEE, '--limit', '60', '--srgb', '--out', "$out\h-srgb.tif")
Run $m100 'm-srgb' @('stack', $BEE, '--limit', '60', '--srgb', '--out', "$out\m-srgb.tif")
Run $m100 'm-srgb-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--exposure', '0', '--out', "$out\m-srgb-e0.tif")
Run $head 'h-demo' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--out', "$out\h-demo.tif")
Run $m100 'm-demo' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--out', "$out\m-demo.tif")
Run $m100 'm-demo-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--exposure', '0', '--out', "$out\m-demo-e0.tif")
Write-Output "  --srgb              HEAD : $(Sha "$out\h-srgb.tif")"
Write-Output "  --srgb              M100 : $(Sha "$out\m-srgb.tif")"
Write-Output "  --srgb --exposure 0 M100 : $(Sha "$out\m-srgb-e0.tif")"
Write-Output "  --srgb --demosaic   HEAD : $(Sha "$out\h-demo.tif")"
Write-Output "  --srgb --demosaic   M100 : $(Sha "$out\m-demo.tif")"
Write-Output "  ... --exposure 0    M100 : $(Sha "$out\m-demo-e0.tif")"

Write-Output ""
Write-Output "================ B6 + the advisory ================"
Run $m100 'auto' @('stack', $BEE, '--limit', '60', '--srgb', '--auto-exposure', '--out', "$out\auto.tif")
Line 'auto' '^(exposure|\s+(rule|reproduce))' | ForEach-Object { "  $_" }
$flag = ((Line 'auto' 'reproduce this exact file') -split 'with ')[-1].Trim()
Run $m100 'auto-repro' @('stack', $BEE, '--limit', '60', '--srgb', $flag, '--out', "$out\auto-repro.tif")
Write-Output "  --auto-exposure : $(Sha "$out\auto.tif")"
Write-Output "  $flag : $(Sha "$out\auto-repro.tif")"
Write-Output "  advisory on a plain --srgb run:"
Line 'm-srgb' '^(exposure|\s+(thing|Nothing))' | ForEach-Object { "    $_" }

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
    Write-Output ("  {0,-9} exit {1}  {2}" -f $case[0], $LASTEXITCODE, ((Line $case[0] 'Error:') -join ' ').Trim())
}

Write-Output ""
Write-Output "================ corpus: before and after, full frame counts ================"
foreach ($s in @('bee-3-cpl','bee-2-cpl','lead-1-cpl','flat-on-ruler-cpl','highly-angled-ruler-mm-cpl','coffee-bean','foam')) {
    Run $m100 "base-$s" @('stack', "D:\personal\macro\$s", '--srgb', '--out', "$out\tune-$s-srgb.tif")
    Run $m100 "auto-$s" @('stack', "D:\personal\macro\$s", '--srgb', '--auto-exposure', '--out', "$out\auto-$s.tif")
    Write-Output ("  {0,-28} {1}" -f $s, ((Line "auto-$s" '^exposure') -join ''))
}
Write-Output "VERIFY3 DONE"
