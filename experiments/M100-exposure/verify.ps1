# M100 end-to-end verification against the pre-registered bars.
# Runs the PATCHED binary built from C:\dev\strehl-out\M100\verify-tree and
# compares against the renders made by the UNPATCHED binary at HEAD.
# READ-ONLY on D:\personal\macro.
$ErrorActionPreference = 'Continue'
$exe = 'C:\dev\strehl-out\M100\vt-target\release\strehl.exe'
$out = 'C:\dev\strehl-out\M100'
$log = "$out\logs"
New-Item -ItemType Directory -Force -Path $log | Out-Null
$BEE = 'D:\personal\macro\bee-3-cpl'

function Sha($p) { (Get-FileHash -Algorithm SHA256 $p).Hash }
function Run($name, $argv) {
    & $exe @argv 2> "$log\$name.err"
    Write-Output ("[{0}] exit {1}" -f $name, $LASTEXITCODE)
}

Write-Output "================ B1: BYTE-FREEZE, default flags ================"
Run 'after-linear' @('stack', $BEE, '--limit', '60', '--out', "$out\after-linear.tif")
$b = Sha "$out\freeze-before-linear.tif"
$a = Sha "$out\after-linear.tif"
Write-Output "  before HEAD   : $b"
Write-Output "  after  patch  : $a"
Write-Output ("  B1: {0}" -f $(if ($a -eq $b) { 'PASS - bit identical' } else { 'FAIL' }))

Write-Output ""
Write-Output "================ B2: --exposure 0 round trip ================"
Run 'after-srgb' @('stack', $BEE, '--limit', '60', '--srgb', '--out', "$out\after-srgb.tif")
Run 'after-srgb-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--exposure', '0', '--out', "$out\after-srgb-e0.tif")
Run 'after-demo' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--out', "$out\after-srgb-demo.tif")
Run 'after-demo-e0' @('stack', $BEE, '--limit', '60', '--srgb', '--demosaic', '--exposure', '0', '--out', "$out\after-srgb-demo-e0.tif")
$bs = Sha "$out\freeze-before-srgb.tif"
$bd = Sha "$out\freeze-before-srgb-demo.tif"
Write-Output "  --srgb           HEAD   : $bs"
Write-Output "  --srgb           patch  : $(Sha "$out\after-srgb.tif")"
Write-Output "  --srgb -e0       patch  : $(Sha "$out\after-srgb-e0.tif")"
Write-Output "  --srgb --demosaic HEAD  : $bd"
Write-Output "  --srgb --demosaic patch : $(Sha "$out\after-srgb-demo.tif")"
Write-Output "  --srgb --demo -e0 patch : $(Sha "$out\after-srgb-demo-e0.tif")"

Write-Output ""
Write-Output "================ B6: the printed choice reproduces the file ================"
Run 'auto' @('stack', $BEE, '--limit', '60', '--srgb', '--auto-exposure', '--out', "$out\after-auto.tif")
Get-Content "$log\auto.err" | Select-String -Pattern 'exposure' | ForEach-Object { "  $_" }
$flag = (Get-Content "$log\auto.err" | Select-String -Pattern 'reproduce this exact file with (--exposure=\S+)').Matches.Groups[1].Value
Write-Output "  parsed flag: $flag"
Run 'auto-repro' @('stack', $BEE, '--limit', '60', '--srgb', $flag, '--out', "$out\after-auto-repro.tif")
Write-Output "  --auto-exposure     : $(Sha "$out\after-auto.tif")"
Write-Output "  $flag : $(Sha "$out\after-auto-repro.tif")"

Write-Output ""
Write-Output "================ B7: refusals ================"
foreach ($case in @(
    @('refuse-noexp', @('stack', $BEE, '--limit', '2', '--exposure', '1.5')),
    @('refuse-noauto', @('stack', $BEE, '--limit', '2', '--auto-exposure')),
    @('refuse-both', @('stack', $BEE, '--limit', '2', '--srgb', '--exposure', '1', '--auto-exposure')),
    @('refuse-range', @('stack', $BEE, '--limit', '2', '--srgb', '--exposure', '99'))
)) {
    Run $case[0] $case[1]
    Get-Content "$log\$($case[0]).err" | Select-Object -Last 3 | ForEach-Object { "    $_" }
}

Write-Output ""
Write-Output "================ negative exposure works, = form ================"
Run 'neg' @('stack', $BEE, '--limit', '2', '--srgb', '--exposure=-1.5', '--out', "$out\neg.tif")
Get-Content "$log\neg.err" | Select-String -Pattern 'exposure' | ForEach-Object { "  $_" }

Write-Output ""
Write-Output "================ gate sensitivity of the automatic choice ================"
foreach ($g in @('0.0', '1.0', '2.0', '4.0')) {
    Run "gate-$g" @('stack', $BEE, '--limit', '60', '--srgb', '--auto-exposure', '--gate', $g)
    $l = (Get-Content "$log\gate-$g.err" | Select-String -Pattern '^exposure').Line
    Write-Output "  gate $g -> $l"
}

Write-Output ""
Write-Output "================ shipped rule on the corpus (full frame counts) ================"
foreach ($s in @('bee-3-cpl','bee-2-cpl','lead-1-cpl','flat-on-ruler-cpl','highly-angled-ruler-mm-cpl','coffee-bean','foam')) {
    $dst = "$out\auto-$s.tif"
    if (Test-Path $dst) { Write-Output "  skip $s"; continue }
    Run "auto-$s" @('stack', "D:\personal\macro\$s", '--srgb', '--auto-exposure', '--out', $dst)
    $l = (Get-Content "$log\auto-$s.err" | Select-String -Pattern '^exposure').Line
    Write-Output "  $s -> $l"
}
Write-Output "VERIFY DONE"
