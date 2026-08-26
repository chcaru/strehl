$e="C:\dev\strehl-out\V-HULLCOST\t8\target\release\strehl.exe"
$o="C:\dev\strehl-out\V-HULLCOST\out"
foreach($h in @("even","odd")){
  foreach($arm in @("clamped","unclamped")){
    $env:STREHL_VHULLCOST_HULL=$arm
    $sw=[Diagnostics.Stopwatch]::StartNew()
    & $e stack "C:\dev\strehl-out\V-HULLCOST\split\$h" -o "$o\cb-$h-$arm.tiff" 2>&1 | Out-Null
    Write-Output "DONE $h/$arm exit=$LASTEXITCODE elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,1))s"
  }
}
Write-Output "SPLIT RENDERS COMPLETE"
