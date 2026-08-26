$exe = "C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
$out = "C:\dev\strehl-out\V-RIM"
$log = "$out\STAGE2.log"
"stage2 waiting $(Get-Date -Format o)" | Out-File $log -Encoding utf8
for ($i=0; $i -lt 240; $i++) {
  $n = (Select-String -Path "$out\lin\RENDER.log" -Pattern '^DONE ' -ErrorAction SilentlyContinue).Count
  if ($n -ge 26) { break }
  Start-Sleep -Seconds 30
}
"stage2 start $(Get-Date -Format o) after $n DONE lines" | Out-File $log -Append -Encoding utf8

# 1. retry the render that died with 0xC0000409 under memory pressure
$t = "$out\lin\dry-erase-marker-head-cpl-lin.tif"
if (-not (Test-Path $t) -or (Get-Item $t).Length -lt 1000000) {
  $t0 = Get-Date
  & $exe stack "D:\personal\macro\dry-erase-marker-head-cpl" --out $t --demosaic *> "$out\retry-dryerase.log"
  "retry dry-erase rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
}

# 2. single frames spanning the bracket, both anchors, to find the in-focus silhouette
foreach ($spec in @(
    @{d="flower-bud-alone-cpl"; p="fb"; f=@(10,30,50,70,90)},
    @{d="coffee-bean";          p="cb"; f=@(45,58,65)})) {
  foreach ($f in $spec.f) {
    $t = "$out\$($spec.p)-frame$f-lin.tif"
    if (Test-Path $t) { continue }
    $env:STREHL_ONLY_FRAME = "$f"
    $t0 = Get-Date
    & $exe stack "D:\personal\macro\$($spec.d)" --out $t --demosaic *> "$out\f-$($spec.p)-$f.log"
    "$($spec.p) frame $f rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
  }
}
Remove-Item Env:\STREHL_ONLY_FRAME -ErrorAction SilentlyContinue

# 3. attack 7: default BINNED mode, genuinely un-interpolated, for the demosaic bias test
foreach ($spec in @(@{d="coffee-bean"; p="cb"}, @{d="flower-bud-alone-cpl"; p="fb"})) {
  $t = "$out\$($spec.p)-binned.tif"
  if (Test-Path $t) { continue }
  $t0 = Get-Date
  & $exe stack "D:\personal\macro\$($spec.d)" --out $t *> "$out\binned-$($spec.p).log"
  "$($spec.p) binned rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
}
"stage2 end $(Get-Date -Format o)" | Out-File $log -Append -Encoding utf8
