# M13 — the exact measurement chain, in order.
#
# Mirrors run-m11.ps1's shape: audit-before -> selftest -> cross-check ->
# sweeps -> audit-after -> analyse. Every corpus path here is READ-ONLY and
# the audit brackets the whole run to prove it.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m13-window-depth.exe"

# The window ladder. `wN` is the operator's box RADIUS; the box is (2N+1)^2.
# Dense between w8 and w20 because that is where the edge objective turns over.
$W = @(0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40)
$MEAS = ($W | ForEach-Object { "tenengrad-w$_" }) -join ","

$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"

Write-Host "== 0. audit before =="
& $exe audit --out data\audit-before.txt

Write-Host "== 1. self-test (metric nulls, positive and complementarity controls) =="
& $exe selftest --out data\selftest.txt

Write-Host "== 2. cross-check against M2's published noise ratios =="
& $exe xcheck $S109 --label 109MSDCF --out data\xcheck-109MSDCF.txt

Write-Host "== 3. N vs window on flat ROIs (M11's committed-CSV ROIs) =="
& $exe noise $S109 --label 109MSDCF --widths 1 --measures $MEAS `
    --roi 2272,1344,256,256 --roi 2496,432,256,256 --roi 2656,1504,256,256 --roi 320,1344,256,256 `
    --roi-kind flat --out data\noise-109MSDCF.csv
& $exe noise $S119 --label 119MSDCF --widths 1 --measures $MEAS `
    --roi 2896,1968,256,256 --roi 3056,416,256,256 --roi 2704,1664,256,256 --roi 3056,1568,256,256 `
    --roi-kind flat --out data\noise-119MSDCF.csv

Write-Host "== 4. phi vs window on real texture (pointwise and Norm::None arms) =="
& $exe phi $S109 --label 109MSDCF --roi 2080,1056,512,512 --measures $MEAS `
    --out data\phi-109MSDCF.csv
$NONORM = ($W | ForEach-Object { "tenengrad-w$_-nonorm" }) -join ","
& $exe phi $S109 --label 109MSDCF --roi 2080,1056,512,512 --measures $NONORM `
    --out data\phi-109MSDCF-nonorm.csv

Write-Host "== 5. continuous plants: fronto-parallel (M11-matched) and tilted =="
& $exe planted $S109 --label 109MSDCF --frames 45 --w-true 22 --widths 1 --measures $MEAS `
    --roi 2080,1056,256,256 --roi 2480,1040,256,256 --roi 2880,1024,256,256 --roi-kind detail `
    --tilts 0 --out data\planted-109MSDCF-m11match.csv
& $exe planted $S119 --label 119MSDCF --frames 45 --w-true 22 --widths 1 --measures $MEAS `
    --roi 2016,1152,256,256 --roi 2272,1152,256,256 --roi 2528,1152,256,256 --roi-kind detail `
    --tilts 0 --out data\planted-119MSDCF-m11match.csv
& $exe planted $S109 --label 109MSDCF --frames 45 --w-true 22 --widths 1 --measures $MEAS `
    --roi 2080,1056,256,256 --roi 2480,1040,256,256 --roi-kind detail `
    --tilts 0,4,8,16,32 --out data\planted-109MSDCF-tilt.csv
& $exe planted $S119 --label 119MSDCF --frames 45 --w-true 22 --widths 1 --measures $MEAS `
    --roi 2016,1152,256,256 --roi 2272,1152,256,256 --roi-kind detail `
    --tilts 0,4,8,16,32 --out data\planted-119MSDCF-tilt.csv

Write-Host "== 6. THE EDGE: depth discontinuity, 3 geometries x 6 steps x 3 seeds =="
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

    # The distance profile is the figure behind the summary numbers. Emitting
    # it for the whole 20-point ladder produces 6 MB of CSV per stack, so it
    # is re-run here restricted to the three windows the report actually
    # cites: M11's recommendation, M13's, and the wide endpoint.
    & $exe edge $stk[1] --label $stk[0] --roi-near $stk[2] --roi-far $stk[3] `
        --frames 41 --steps 0,8,32 --widths 1 --seed 20260823 --shape vertical `
        --measures tenengrad-w5,tenengrad-w13,tenengrad-w40 `
        --out "data\_prof-summary.csv" --profile-out "data\edgeprof-$($stk[0]).csv"
    Remove-Item "data\_prof-summary.csv"
}

Write-Host "== 7. cost vs window =="
& $exe cost $S109 --label 109MSDCF --roi 2272,1344,512,512 --reps 9 `
    --measures "$MEAS,ring-1-3" --out data\cost-109MSDCF.csv

Write-Host "== 8. adaptive rule =="
.\run-adaptive.ps1

Write-Host "== 9. audit after =="
& $exe audit --out data\audit-after.txt

Write-Host "== 10. analyse =="
python m13_analyse.py --out data\analysis.txt

Write-Host "done."
