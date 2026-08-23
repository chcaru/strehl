# M15 -- does the focus-measure window optimum survive the merge regulariser?
#
# The whole measurement chain, in order. Mirrors run-m13.ps1's shape:
# audit-before -> selftest -> xcheck -> Gate A replication -> noise ladder ->
# the main (window x regulariser) sweep -> audit-after -> analyse.
#
# The harness is M13's, UNMODIFIED. Nothing under experiments/m13-window-depth,
# crates/ or docs/research/M*.md is written by this script. Every corpus path is
# READ-ONLY and the audit brackets the whole run to prove it.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "..\m13-window-depth\target\release\m13-window-depth.exe"

# --- ladders (see PREREGISTRATION.md sections 1 and 3) ------------------------

# M13's exact 20-point window ladder, for the Gate A replication.
$W13 = @(0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40)
$MEAS13 = ($W13 | ForEach-Object { "tenengrad-w$_" }) -join ","

# M15's 24-point ladder: M13's, plus w4, w7, w14, w16. Endpoints unchanged.
$W15 = @(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40)
$MEAS15 = ($W15 | ForEach-Object { "tenengrad-w$_" }) -join ","

# The regulariser axis. `width` is the box side; radius is (width-1)/2.
$WIDTHS = "1,3,5,9,13,17,25,33,49"

# M13's three seeds, then two new ones.
$SEEDS13 = @(20260823, 771117, 4242424)
$SEEDS15 = @(20260823, 771117, 4242424, 13371337, 90210)

$S109 = "C:\dev\macro\test\109MSDCF"
$S119 = "C:\dev\macro\test\119MSDCF"

# stack label, path, near ROI, far ROI -- ROIs identical to run-m13.ps1, which
# took them from M11's COMMITTED CSVs, not from run-m11.ps1 (the ROI trap).
$STACKS = @(
    @("109MSDCF", $S109, "2080,1056,384,256", "2480,1040,384,256"),
    @("119MSDCF", $S119, "2016,1152,384,256", "2528,1152,384,256")
)

Write-Host "== 0. audit before =="
& $exe audit --out data\audit-before.txt

Write-Host "== 1. self-test (Gate C: metric nulls, positive and complementarity controls) =="
& $exe selftest --out data\selftest.txt

Write-Host "== 2. Gate B1: cross-check the regulariser against M2's published noise ratios =="
& $exe xcheck $S109 --label 109MSDCF --out data\xcheck-109MSDCF.txt

Write-Host "== 3. Gate A: replicate M13's edge sweep EXACTLY (20 windows, 3 seeds, width 1) =="
foreach ($stk in $STACKS) {
    $rows = @()
    $hdr = $null
    foreach ($seed in $SEEDS13) {
        $tmp = "data\_repro-tmp.csv"
        & $exe edge $stk[1] --label $stk[0] --roi-near $stk[2] --roi-far $stk[3] `
            --frames 41 --steps 0,2,4,8,16,32 --widths 1 --seed $seed `
            --shape vertical --shape horizontal --shape bar `
            --measures $MEAS13 --out $tmp
        $lines = Get-Content $tmp
        if ($null -eq $hdr) { $hdr = $lines[0]; $rows += $hdr }
        $rows += $lines[1..($lines.Length - 1)]
        Remove-Item $tmp
    }
    $rows | Set-Content -Encoding ascii "data\repro-edge-$($stk[0]).csv"
    Write-Host "  wrote data\repro-edge-$($stk[0]).csv ($($rows.Length - 1) rows)"
}

Write-Host "== 4. Gate B2: merged noise N vs regulariser width on M11's flat ROIs =="
& $exe noise $S109 --label 109MSDCF --widths $WIDTHS `
    --measures "tenengrad-w5,tenengrad-w13,tenengrad-w40,ring-1-3" `
    --roi 2272,1344,256,256 --roi 2496,432,256,256 --roi 2656,1504,256,256 --roi 320,1344,256,256 `
    --roi-kind flat --out data\noise-109MSDCF.csv
& $exe noise $S119 --label 119MSDCF --widths $WIDTHS `
    --measures "tenengrad-w5,tenengrad-w13,tenengrad-w40,ring-1-3" `
    --roi 2896,1968,256,256 --roi 3056,416,256,256 --roi 2704,1664,256,256 --roi 3056,1568,256,256 `
    --roi-kind flat --out data\noise-119MSDCF.csv

Write-Host "== 5. THE SURFACE: 24 windows x 9 regulariser widths x 3 shapes x 6 steps x 5 seeds =="
foreach ($stk in $STACKS) {
    $rows = @()
    $hdr = $null
    foreach ($seed in $SEEDS15) {
        $tmp = "data\_edge-tmp.csv"
        & $exe edge $stk[1] --label $stk[0] --roi-near $stk[2] --roi-far $stk[3] `
            --frames 41 --steps 0,2,4,8,16,32 --widths $WIDTHS --seed $seed `
            --shape vertical --shape horizontal --shape bar `
            --measures $MEAS15 --out $tmp
        $lines = Get-Content $tmp
        if ($null -eq $hdr) { $hdr = $lines[0]; $rows += $hdr }
        $rows += $lines[1..($lines.Length - 1)]
        Remove-Item $tmp
    }
    $rows | Set-Content -Encoding ascii "data\edge-$($stk[0]).csv"
    Write-Host "  wrote data\edge-$($stk[0]).csv ($($rows.Length - 1) rows)"
}

Write-Host "== 6. audit after =="
& $exe audit --out data\audit-after.txt

Write-Host "== 7. analyse =="
python m15_analyse.py --out data\analysis.txt

Write-Host "done."
