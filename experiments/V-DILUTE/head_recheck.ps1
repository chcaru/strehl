# Re-verify the load-bearing statistic on HEAD, because the merge moved.
#
# Discipline 34: the pin 9b05d0b7 is stale. Measured directly -- pin vs HEAD on
# bee-3-cpl N=299 default differ in 71.35% of samples (max |d| 881) and the
# band-0 `averaged` duty cycle moved 0.4% -> 8.4%, so 78fed9a1's per-frame noise
# floor changed the DEFAULT path, not only opt-in ones.
#
# The verdict rests on n_eff = noise(hard-max)/noise(default) at matched N: 1.0
# is winner-take-all, N is a plain mean. If n_eff stays near 1.0 at both ends of
# the depth range on HEAD, the refutation transfers. If it climbs with N on HEAD,
# the dilution hypothesis is alive on current code and ORCH must be told at once.
#
# N=22 spans the FULL focus range by striding, NOT --limit, which would take the
# first 22 frames and change the range instead of the density.
$new  = "C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"
$runs = "C:\dev\strehl-out\V-DILUTE\runs"
$stk  = "C:\dev\strehl-out\V-DILUTE\stacks\bee_head22"
$bee  = "D:\personal\macro\bee-3-cpl"
$sha  = (Get-FileHash $new -Algorithm SHA256).Hash.Substring(0,16)
Write-Host "HEAD binary sha16 $sha  commit $(git -C 'C:\dev\blog\death-of-software\projects\strehl' rev-parse --short HEAD)"

New-Item -ItemType Directory -Force -Path $stk | Out-Null
$src = Get-ChildItem $bee -File -Filter *.ARW | Sort-Object Name
$idx = 0..21 | ForEach-Object { [int][math]::Round($_ * 298.0 / 21.0) }
foreach ($i in $idx) {
  $f = $src[$i]; $d = Join-Path $stk $f.Name
  if (-not (Test-Path $d)) { Copy-Item $f.FullName $d }
}
Write-Host "staged $((Get-ChildItem $stk -File).Count) frames spanning $($src[$idx[0]].Name)..$($src[$idx[-1]].Name)"

function Arm {
  param($Tag, $Dir, $Extra)
  $o = "$runs\$Tag.tif"
  if (Test-Path $o) { Write-Host "$Tag exists"; return }
  $a = @('stack', $Dir, '--merge', 'pyramid', '--out', $o) + $Extra
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & $new @a 2>&1
  $sw.Stop(); $out | Set-Content "$runs\$Tag.log"
  Write-Host "$Tag : $([math]::Round($sw.Elapsed.TotalSeconds,1))s  $(($out | Select-String '^averaged').Line)"
}

Arm 'HEAD_n22_default'  $stk  @()
Arm 'HEAD_n22_hardmax'  $stk  @('--pyramid-select','hard-max')
Arm 'HEAD_n299_hardmax' $bee  @('--pyramid-select','hard-max')
Remove-Item $stk -Recurse -Force
Write-Host "cleaned; C: free $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB"
