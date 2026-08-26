$exe = "C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
$out = "C:\dev\strehl-out\V-RIM"
$log = "$out\STAGE3.log"
"stage3 start $(Get-Date -Format o)" | Out-File $log -Encoding utf8
while (Get-Process strehl -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 20 }
foreach ($f in @(110,130,150,170,190)) {
  $t = "$out\fb-frame$f-lin.tif"
  if (Test-Path $t) { continue }
  $env:STREHL_ONLY_FRAME = "$f"
  $t0 = Get-Date
  & $exe stack "D:\personal\macro\flower-bud-alone-cpl" --out $t --demosaic *> "$out\f-fb-$f.log"
  "fb frame $f rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
}
Remove-Item Env:\STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
"stage3 end $(Get-Date -Format o)" | Out-File $log -Append -Encoding utf8
