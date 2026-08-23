# M42 — the window ladder for `tenengrad-sq`. Owner question Q1.
#
# GATE NOTE (inherited from M17, and it bit once already). The edge tile's margin is
# `max_regulariser_radius + max_support(measures) + probe.max_blur_radius()`, and the tile
# geometry decides where the planted edge lands and which corpus texture is extracted.
# `--steps 0,2,4,8,16,32` and the presence of a `w40` measure are load-bearing: drop
# either and the scene moves (`vertical@261` instead of M13's `vertical@274`) and every
# number changes silently. Gate 1 below is what catches it.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m42-window-ladder.exe"

# M13's own 20-window ladder, verbatim from experiments/m13-window-depth/run-m13.ps1.
$W = @(0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40)
$MAG = ($W | ForEach-Object { "tenengrad-w$_" }) -join ","        # M13's operator, the gate
$SQ = ($W | ForEach-Object { "tenengrad-sq-w$_" }) -join ","      # M17's operator, the question
$MEAS = "$MAG,$SQ,tgrms-w13"                                      # + the degree-check arm
$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"

Write-Host "== 0. audit the read-only corpora =="
& $exe audit --out data\audit-before.txt

Write-Host "== 1. GATE 3 + axis 2: M13's 36 occluding-edge cells, both operators, 20 windows =="
foreach ($stk in @(@("109MSDCF", $S109, "2080,1056,384,256", "2480,1040,384,256"),
                   @("119MSDCF", $S119, "2016,1152,384,256", "2528,1152,384,256"))) {
    $rows = @()
    $hdr = $null
    foreach ($seed in @(20260823, 771117, 4242424)) {
        $tmp = "data\_edge-tmp.csv"
        & $exe edge $stk[1] --label $stk[0] --roi-near $stk[2] --roi-far $stk[3] `
            --frames 41 --steps 0,2,4,8,16,32 --widths 1 --seed $seed `
            --shape vertical --shape horizontal --shape bar `
            --measures $MEAS --out $tmp
        $lines = Get-Content $tmp
        if ($null -eq $hdr) { $hdr = $lines[0]; $rows += $hdr }
        $rows += $lines[1..($lines.Length - 1)]
    }
    $rows | Set-Content "data\edge-$($stk[0]).csv"
    Remove-Item "data\_edge-tmp.csv" -ErrorAction SilentlyContinue
}

Write-Host "== 2. axis 3: N vs window on the flat ROIs M11/M13 committed =="
& $exe noise $S109 --label 109MSDCF --widths 1 --measures $MEAS `
    --roi 2272,1344,256,256 --roi 2496,432,256,256 --roi 2656,1504,256,256 --roi 320,1344,256,256 `
    --roi-kind flat --out data\noise-109MSDCF.csv
& $exe noise $S119 --label 119MSDCF --widths 1 --measures $MEAS `
    --roi 2896,1968,256,256 --roi 3056,416,256,256 --roi 2704,1664,256,256 --roi 3056,1568,256,256 `
    --roi-kind flat --out data\noise-119MSDCF.csv

Write-Host "== 3. axis 4: the blind-spot cure vs window, with M17's null and positive controls =="
$BSN = ($MEAS -split ',' | ForEach-Object { "$_-nonorm" }) -join ','
& $exe blindspot --out data\blindspot-norm.csv --measures $MEAS `
    --dir $S109 --label 109MSDCF --roi 2272,1344,255,255 --size 257
& $exe blindspot --out data\blindspot-nonorm.csv --measures $BSN `
    --dir $S109 --label 109MSDCF --roi 2272,1344,255,255 --size 257

Write-Host "== 4. axis 5: cost vs window, alternating direction, per-setting minimum =="
& $exe m17cost --out data\cost-measures.csv --measures $MEAS --reps 3 --passes 8

Write-Host "== 5. analysis =="
python m42_analyse.py
