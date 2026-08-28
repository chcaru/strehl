# Concentration, flat vs detail, per band -- ORCH's acceptance criterion #1,
# measured across the significance arms on the SHIPPING (pyramid) backend.
#
# THE CLAIM UNDER TEST: the merge concentrates MORE in flat regions than in
# detail regions (fact 1811: 1.0000 flat vs 0.8214 detail at band 0, 0.7837 vs
# 0.2989 at band 2). That inversion is a merge selecting on noise where there is
# nothing to select on. `p_eff` is aimed exactly at it, and the claim is that
# the inversion collapses.
#
# ORCH, in advance: "a fall in flat concentration with detail concentration also
# falling is dilution, not a fix." So both columns are reported, always.
#
# THE 1000x ARM IS A COMMISSIONING ARM, not a candidate. It exists so that
# "concentration did not move" can be distinguished from "concentration cannot
# move under this knob". A metric that has only ever been shown not to respond
# is not evidence either.

$ErrorActionPreference = "Stop"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$cli  = Join-Path $root "target\release\strehl.exe"
$dump = "C:\dev\strehl-out\V-H2H2\wdump"
$stack = "D:\personal\macro\coffee-bean"
$outdir = Join-Path $env:TEMP "vh2h2-sig"
New-Item -ItemType Directory -Force -Path $dump, $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "strehl.exe sha256: $sha0"
Write-Host "stack            : $stack (limit 20, --merge pyramid)"
Write-Host ""

$arms = @{ "0" = "sig0"; "1" = "sig1"; "1000" = "sighot" }
foreach ($arm in @("0", "1", "1000")) {
    $tag = $arms[$arm]
    $env:STREHL_PYRAMID_SIGNIFICANCE = $arm
    $env:STREHL_PYRAMID_WEIGHT_DUMP = Join-Path $dump $tag
    $out = Join-Path $outdir "conc-$tag.tif"
    Remove-Item $out -ErrorAction SilentlyContinue
    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid -l 20 -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe changed during arm $arm"; exit 2 }
    if ($rc -ne 0) {
        Write-Host "arm $arm FAILED rc=$rc"
        ($log -split "`n" | Select-Object -Last 10) | ForEach-Object { Write-Host "    $_" }
        exit 1
    }
    $dims = Join-Path $dump "$tag-dims.json"
    if (-not (Test-Path $dims)) { Write-Host "arm $arm wrote NO DUMP -- $dims missing"; exit 1 }
    Write-Host ("arm {0,-5} tif {1}  dump {2}" -f $arm, (Get-FileHash -Algorithm SHA256 $out).Hash.Substring(0,16), $tag)
}
Remove-Item Env:STREHL_PYRAMID_SIGNIFICANCE, Env:STREHL_PYRAMID_WEIGHT_DUMP -ErrorAction SilentlyContinue
if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe moved across the run"; exit 2 }
Write-Host ""
foreach ($arm in @("0", "1", "1000")) {
    Write-Host "================ arm STREHL_PYRAMID_SIGNIFICANCE=$arm ($($arms[$arm])) ================"
    & python -u (Join-Path $root "experiments\V-H2H2-MOTTLE\wanalyse.py") $arms[$arm] 2>&1 |
        Select-String -Pattern '^\s*\d|^k |subject dump|local sd' | ForEach-Object { Write-Host $_ }
    Write-Host ""
}
