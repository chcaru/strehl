$e="C:\dev\strehl-out\V-HULLCOST\t8\target\release\strehl.exe"
$o="C:\dev\strehl-out\V-HULLCOST\out"
foreach($subj in @("coffee-bean","foam","flower-bud-alone-cpl","couch-fibers-cpl")){
  foreach($arm in @("clamped","unclamped")){
    $f="$o\$subj-$arm.tiff"
    if(Test-Path $f){ Write-Output "SKIP $subj/$arm"; continue }
    $env:STREHL_VHULLCOST_HULL=$arm
    $sw=[Diagnostics.Stopwatch]::StartNew()
    & $e stack "D:\personal\macro\$subj" -o $f 2>&1 | Out-Null
    Write-Output "DONE $subj/$arm exit=$LASTEXITCODE elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,1))s"
  }
}
Write-Output "ALL RENDERS COMPLETE"
