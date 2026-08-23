# M16 -- remaining arms, reordered by decision value.
#
# Identical arm definitions to run-m16.ps1 (copy them line for line and diff if
# you doubt it); the ONLY change is the order in which they run, so the arms
# that decide H1 vs H2 land before the H3 amplitude ladder. `Run-Arm` skips any
# arm whose CSV already exists, so this script and run-m16.ps1 compose: running
# run-m16.ps1 afterwards fills in whatever is still missing and re-runs nothing.
#
# Uses target-aux (the binary that also has `--symmetrise` and `anisoscan`).
# `data/binary-equivalence.txt` records the check that target-aux and target
# produce byte-identical edge CSVs.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
Set-Location $PSScriptRoot
$exe = ".\target-aux\release\m16-orientation-fpn.exe"

$W15 = @(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40)
$MEAS = ($W15 | ForEach-Object { "tenengrad-w$_" }) -join ","
$WIDTHS = "1,17"
$MARGIN = 106
$SEEDS = "20260823,771117,4242424,13371337,90210"
$STEPS = "0,2,4,8,16,32"
$SHAPES = @("--shape", "vertical", "--shape", "horizontal", "--shape", "bar")

$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"
$STACKS = @(
    @("109MSDCF", $S109, "2080,1056,384,256", "2480,1040,384,256", "2080,1056,256,256", "2480,1040,256,256"),
    @("119MSDCF", $S119, "2016,1152,384,256", "2528,1152,384,256", "2016,1152,256,256", "2528,1152,256,256")
)

function Run-Arm {
    param([string]$Arm, [string[]]$Extra, [switch]$Square)
    foreach ($stk in $STACKS) {
        $out = "data\$Arm-$($stk[0]).csv"
        if (Test-Path $out) { Write-Host "  skip $out (exists)"; continue }
        $near = if ($Square) { $stk[4] } else { $stk[2] }
        $far = if ($Square) { $stk[5] } else { $stk[3] }
        & $exe edge $stk[1] --label $stk[0] --roi-near $near --roi-far $far `
            --frames 41 --steps $STEPS --widths $WIDTHS --margin $MARGIN `
            --seeds $SEEDS --measures $MEAS @SHAPES `
            --arm $Arm @Extra --out $out
        if ($LASTEXITCODE -ne 0) { throw "arm $Arm on $($stk[0]) failed" }
    }
}

Write-Host "== A6 control-square, real texture (H2) =="
Run-Arm "A6" @() -Square

Write-Host "== A8 square + TRANSPOSED texture (scene vs machinery) =="
Run-Arm "A8" @("--transpose") -Square

Write-Host "== A10 rect plant, square scored band (H2a alone) =="
Run-Arm "A10" @("--score-region", "256,256")

Write-Host "== A7 synthetic isotropic on a square ROI (N4: machinery symmetry) =="
Run-Arm "A7" @("--texture", "synth") -Square

Write-Host "== A4x64 synthetic + planted row FPN, 64x (H3 POSITIVE CONTROL) =="
Run-Arm "A4x64" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor")

Write-Host "== A5x64 the same, plus the fix (H3 fix confirmation) =="
Run-Arm "A5x64" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor", "--destripe", "mean")

Write-Host "== A4x8 synthetic + planted row FPN, 8x =="
Run-Arm "A4x8" @("--texture", "synth", "--fpn-sd", "3.016", "--fpn-axis", "row", "--fpn-stage", "sensor")

Write-Host "== A9 destripe-hp on the square ROI (H3 on symmetric geometry) =="
Run-Arm "A9" @("--destripe", "hp", "--hp-sigma", "4") -Square

Write-Host "== A5x64o oracle removal (the fix's own upper bound) =="
Run-Arm "A5x64o" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor", "--destripe", "oracle")

Write-Host "== audit after =="
& $exe audit --out data\audit-after.txt
if (Compare-Object (Get-Content data\audit-before.txt) (Get-Content data\audit-after.txt)) {
    throw "READ-ONLY CORPUS CHANGED"
}
Write-Host "  read-only corpora unchanged"
Write-Host "== done =="
