# V-DILUTE Experiment B2 -- the interleave-phase REPLICATE null.
#
# ORCH's Experiment B contrasts step-x2/full-range against step-x1/half-range at
# equal N. Its repaired ROI form gave 1.125x, which failed its paired significance
# test. What was never measured is the FLOOR: how much do two 150-frame subsets of
# bee differ when NOTHING about the design differs -- same focus range, same focus
# step, same density of near-focus competitors, same N?
#
# Odd-phase decimation (DSC00002,00004,...,00298; N=149) is exactly that replicate
# of the surviving even-phase arm B_step2_n150 (DSC00001,00003,...,00299; N=150).
# It shares the contrast's every nuisance -- subset alignment solve, FOV shrink,
# resample blur -- and shares NONE of its signal. Any effect B claims must exceed
# what this pair produces by chance.
$exe  = "C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
$runs = "D:\strehl-out\V-DILUTE\runs"
$stk  = "D:\strehl-out\V-DILUTE\stacks\bee_odd150"
$bee  = "D:\personal\macro\bee-3-cpl"

# Rule 2: never trust a result from an unverified binary.
$sha = (Get-FileHash $exe -Algorithm SHA256).Hash
if ($sha.Substring(0,16) -ne '44C2F2CD2E5B2894') { throw "WRONG BINARY: $($sha.Substring(0,16))" }
Write-Host "pin verified $($sha.Substring(0,16))"

New-Item -ItemType Directory -Force -Path $stk | Out-Null
$src = Get-ChildItem $bee -File -Filter *.ARW | Sort-Object Name
$sel = @(); for ($i = 1; $i -lt $src.Count; $i += 2) { $sel += $src[$i] }
Write-Host "odd-phase frames: $($sel.Count)  $($sel[0].Name) .. $($sel[-1].Name)"
foreach ($f in $sel) {
  $d = Join-Path $stk $f.Name
  if (-not (Test-Path $d)) { Copy-Item $f.FullName $d }   # D:\ is READ-ONLY; copy out only
}
Write-Host "staged $((Get-ChildItem $stk -File).Count) frames"

$o = "$runs\B_odd149_n149.tif"
if (Test-Path $o) { Write-Host "render exists, skipping" } else {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & $exe stack $stk --merge pyramid --out $o --confidence-map "$runs\B_odd149_n149_conf.tif" 2>&1
  $sw.Stop()
  $out | Set-Content "$runs\B_odd149_n149.log"
  Write-Host "rendered in $([math]::Round($sw.Elapsed.TotalSeconds,1))s"
  ($out | Select-String -Pattern 'field of view|^averaged|^wrote').Line | ForEach-Object { Write-Host "  $_" }
}
Remove-Item $stk -Recurse -Force        # rule 9: clean intermediates as I go
Write-Host "stack cleaned; C: free $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB"
