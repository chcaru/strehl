# M17 — the measurement chain, in order.
#
# Same shape as run-m13.ps1, and deliberately so: modes 0-6 below are M13's own
# harness invoked with M13's own arguments, because the only way this milestone
# is allowed to compare a new aggregator against `tenengrad-w13` is if the fork
# reproduces `tenengrad-w13`'s published rows first.
#
# GATE NOTE. `--steps 0,2,4,8,16,32` and the presence of `tenengrad-w40` in the
# measure set are NOT decoration. The edge tile's margin is
# `max_regulariser_radius + max_support(measures) + probe.max_blur_radius()`,
# and the tile geometry decides where the planted edge lands and which corpus
# texture is extracted. Drop `tenengrad-w40` (support 41) or shorten the step
# list and the whole scene moves: an early probe here rendered `vertical@261`
# instead of M13's `vertical@274` and every number changed.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m17-dual-response.exe"

# The candidate list, pre-registered in PREREGISTRATION.md section 1.
# `tenengrad-w13` is the status quo and `tenengrad-w40` is the margin pin.
$CAND = @(
    "tenengrad-w13",          # status quo: box MEAN of |grad|
    "tgmax-w13",              # box MAX of |grad|
    "tgp95-w13",              # 95th percentile
    "tgp99-w13",              # 99th percentile
    "tgdual-geo-w13",         # dual: sqrt(mean * max)
    "tgdual-sum-w13",         # dual: mean + max
    "tgdual-tie5-w13",        # dual: mean + 0.05 * max
    "tgrad-larger-w1-w13",    # question 19 candidate (b), max of two radii
    "tgrad-geo-w1-w13",       # question 19 candidate (b), geometric
    "tenengrad-sq-w13"        # question 19 candidate (c), squared magnitude
)
$MEAS = (($CAND + @("tenengrad-w40")) -join ",")
$NOISEMEAS = (($CAND + @("tenengrad-w0", "tenengrad-w40")) -join ",")

$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"

Write-Host "== 0. audit before =="
& $exe audit --out data\audit-before.txt

Write-Host "== 1. arithmetic gates (G2 lives in `cargo test`, G5 lives here) =="
& $exe m17check | Tee-Object -FilePath data\m17check.txt

Write-Host "== 2. GATE 4 + axis 3: N on the flat ROIs M13 committed =="
& $exe noise $S109 --label 109MSDCF --widths 1 --measures $NOISEMEAS `
    --roi 2272,1344,256,256 --roi 2496,432,256,256 --roi 2656,1504,256,256 --roi 320,1344,256,256 `
    --roi-kind flat --out data\noise-109MSDCF.csv
& $exe noise $S119 --label 119MSDCF --widths 1 --measures $NOISEMEAS `
    --roi 2896,1968,256,256 --roi 3056,416,256,256 --roi 2704,1664,256,256 --roi 3056,1568,256,256 `
    --roi-kind flat --out data\noise-119MSDCF.csv

Write-Host "== 3. GATE 3 + axis 2: M13's 36 occluding-edge cells =="
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
        Remove-Item $tmp
    }
    $rows | Set-Content -Encoding ascii "data\edge-$($stk[0]).csv"
    Write-Host "  wrote data\edge-$($stk[0]).csv ($($rows.Length - 1) rows)"
}

Write-Host "== 4. axis 1: the blind spot, analytic ladder (B1) + both controls =="
$NONORM = (($CAND + @("tenengrad-w1", "tenengrad-w3", "tenengrad-w0")) | ForEach-Object { "$_-nonorm" }) -join ","
$WITHCTL = (($CAND + @("tenengrad-w1", "tenengrad-w3", "tenengrad-w0")) -join ",")
& $exe blindspot --out data\blindspot-norm.csv --measures $WITHCTL `
    --dir $S109 --label 109MSDCF --roi 2272,1344,255,255 --size 257
& $exe blindspot --out data\blindspot-nonorm.csv --measures $NONORM `
    --dir $S109 --label 109MSDCF --roi 2272,1344,255,255 --size 257

Write-Host "== 5. axis 1: the blind spot, realistic compositor (B2) =="
& $exe blindspot-edge --out data\blindspot-edge.csv --measures $WITHCTL

Write-Host "== 6. axis 4: cost, alternating sweeps, per-setting minimum =="
& $exe boxcost --out data\boxcost.csv --radii 1,2,3,5,8,13,21,34,40 --reps 5 --passes 8 --with-pct
& $exe m17cost --out data\cost-measures.csv --measures $NOISEMEAS --reps 3 --passes 8

Write-Host "== 7. audit after =="
& $exe audit --out data\audit-after.txt

Write-Host "== 8. analyse =="
& python m17_analyse.py
