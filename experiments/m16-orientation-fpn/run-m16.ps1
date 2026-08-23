# M16 -- orientation asymmetry and fixed-pattern noise.
#
# Answers SYNTHESIS section 10 question 20. Pre-registered in
# PREREGISTRATION.md, committed before any result here was computed.
#
# `C:\dev\macro`, `D:\macro-dark-frames` and `D:\personal\macro` are READ-ONLY
# and the audit brackets the whole run to prove it.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m16-orientation-fpn.exe"

# --- ladders, identical to M15's so the arms join to its CSVs ----------------

$W15 = @(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40)
$MEAS = ($W15 | ForEach-Object { "tenengrad-w$_" }) -join ","

# fact 83 is defined between width 1 and width 17. Those are the only two the
# arms need, but the MARGIN is pinned to M15's 106 px so the tile -- and hence
# the edge position inside the texture -- is M15's scene exactly. Gate 2 checks
# that field for field.
$WIDTHS = "1,17"
$MARGIN = 106
$SEEDS = "20260823,771117,4242424,13371337,90210"
$STEPS = "0,2,4,8,16,32"

$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"

# stack label, path, near ROI, far ROI, square near ROI, square far ROI.
# Rect ROIs identical to run-m15.ps1; square ROIs are M13's `planted` detail
# ROIs for the same stacks, both taken from M11's COMMITTED CSVs.
$STACKS = @(
    @("109MSDCF", $S109, "2080,1056,384,256", "2480,1040,384,256", "2080,1056,256,256", "2480,1040,256,256"),
    @("119MSDCF", $S119, "2016,1152,384,256", "2528,1152,384,256", "2016,1152,256,256", "2528,1152,256,256")
)

$SHAPES = @("--shape", "vertical", "--shape", "horizontal", "--shape", "bar")

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

Write-Host "== 0. audit before =="
& $exe audit --out data\audit-before.txt

Write-Host "== 1. selftest (G3, the treatment nulls and positive controls) =="
& $exe selftest | Tee-Object data\selftest.txt

Write-Host "== 2. plant characterisation (row/column structure, anisotropy) =="
if (-not (Test-Path data\fpnscan-109MSDCF.csv)) {
    & $exe fpnscan $S109 --label 109MSDCF --out data\fpnscan-109MSDCF.csv `
        --roi 1974,950,596,468 --roi 2374,934,596,468 --roi 2272,1344,256,256
}
if (-not (Test-Path data\fpnscan-119MSDCF.csv)) {
    & $exe fpnscan $S119 --label 119MSDCF --out data\fpnscan-119MSDCF.csv `
        --roi 1910,1046,596,468 --roi 2422,1046,596,468 --roi 2896,1968,256,256
}

# =============================================================================
# The arms. See PREREGISTRATION.md section 3.2.
# =============================================================================

Write-Host "== A0 control-rect (Gate 2: must reproduce M15 field for field) =="
Run-Arm "A0" @()

Write-Host "== A1 destripe-mean, real texture (H3, the reviewer's literal fix) =="
Run-Arm "A1" @("--destripe", "mean")

Write-Host "== A2 destripe-hp, real texture (H3, content-preserving) =="
Run-Arm "A2" @("--destripe", "hp", "--hp-sigma", "4")

Write-Host "== A3 synthetic isotropic texture, no FPN (H1) =="
Run-Arm "A3" @("--texture", "synth")

Write-Host "== A4 synthetic + planted row FPN (H3 POSITIVE CONTROL) =="
# 1x is M4's measured total per-pixel FPN sigma at base ISO -- an upper bound on
# the row-correlated part. 8x and 64x are there so the control cannot fail for
# want of amplitude.
Run-Arm "A4x1" @("--texture", "synth", "--fpn-sd", "0.377", "--fpn-axis", "row", "--fpn-stage", "sensor")
Run-Arm "A4x8" @("--texture", "synth", "--fpn-sd", "3.016", "--fpn-axis", "row", "--fpn-stage", "sensor")
Run-Arm "A4x64" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor")

Write-Host "== A5 synthetic + planted row FPN + the fix (H3 fix confirmation) =="
Run-Arm "A5x64" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor", "--destripe", "mean")
Run-Arm "A5x64o" @("--texture", "synth", "--fpn-sd", "24.128", "--fpn-axis", "row", "--fpn-stage", "sensor", "--destripe", "oracle")

Write-Host "== A6 control-square, real texture (H2) =="
Run-Arm "A6" @() -Square

Write-Host "== A7 synthetic isotropic on a square ROI (N4: machinery symmetry) =="
Run-Arm "A7" @("--texture", "synth") -Square

Write-Host "== A8 square + TRANSPOSED texture (scene vs machinery) =="
Run-Arm "A8" @("--transpose") -Square

Write-Host "== A9 destripe-hp on the square ROI (H3 on symmetric geometry) =="
Run-Arm "A9" @("--destripe", "hp", "--hp-sigma", "4") -Square

Write-Host "== A10 rect plant, square scored band (H2a alone) =="
Run-Arm "A10" @("--score-region", "256,256")

Write-Host "== 3. audit after =="
& $exe audit --out data\audit-after.txt
$before = Get-Content data\audit-before.txt
$after = Get-Content data\audit-after.txt
if (Compare-Object $before $after) { throw "READ-ONLY CORPUS CHANGED" }
Write-Host "  read-only corpora unchanged"

Write-Host "== 4. analyse =="
$env:PYTHONIOENCODING = 'utf-8'
python m16_gate1.py | Tee-Object data\gate1.txt
python m16_analyse.py | Tee-Object data\analysis.txt
