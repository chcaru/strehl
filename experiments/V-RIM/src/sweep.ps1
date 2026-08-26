$py = "C:\dev\strehl-out\V-RIM\vrim_rays.py"
$lin = "C:\dev\strehl-out\V-RIM\lin"
$js  = "C:\dev\strehl-out\V-RIM\json2"
$logd = "C:\dev\strehl-out\V-RIM\sweeplogs"
New-Item -ItemType Directory -Force -Path $logd | Out-Null
# the 14 subjects the pre-registration marked MEASURABLE
$subj = @("coffee-bean","flower-bud-alone-cpl","109MSDCF","119MSDCF",
          "bee-1-cpl","bee-2-cpl","bee-3-cpl","dry-erase-marker-head-cpl",
          "flower-bud-with-background-fern-cpl","highly-angled-ruler-mm-cpl",
          "lavendar-cpl","pencil-flatter-angle-cpl","pencil-steep-angle-cpl",
          "tweezers-cpl")
$log = "C:\dev\strehl-out\V-RIM\SWEEP.log"
"sweep start $(Get-Date -Format o)" | Out-File $log -Encoding utf8
for ($pass=1; $pass -le 40; $pass++) {
  $left = 0
  foreach ($s in $subj) {
    $tif = Join-Path $lin "$s-lin.tif"
    $out = Join-Path $js "$s-rays.json"
    if (Test-Path $out) { continue }
    if (-not (Test-Path $tif)) { $left++; continue }
    $t0 = Get-Date
    python $py $tif $s $js G *> (Join-Path $logd "$s.log")
    $rc = $LASTEXITCODE
    $dt = ((Get-Date)-$t0).TotalSeconds
    "pass $pass  $s rc=$rc $([math]::Round($dt))s" | Out-File $log -Append -Encoding utf8
  }
  if ($left -eq 0) { break }
  Start-Sleep -Seconds 60
}
"sweep end $(Get-Date -Format o)" | Out-File $log -Append -Encoding utf8
