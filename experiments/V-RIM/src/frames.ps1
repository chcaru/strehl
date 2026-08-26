$exe = "C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
$dir = "D:\personal\macro\coffee-bean"
$out = "C:\dev\strehl-out\V-RIM"
$log = "$out\FRAMES.log"
"frames start $(Get-Date -Format o)" | Out-File $log -Encoding utf8
foreach ($f in 10,30,75,95) {
  $t = "$out\cb-frame$f-lin.tif"
  if (Test-Path $t) { "skip $f" | Out-File $log -Append -Encoding utf8; continue }
  $env:STREHL_ONLY_FRAME = "$f"
  $t0 = Get-Date
  & $exe stack $dir --out $t --demosaic *> "$out\frame$f.log"
  $rc = $LASTEXITCODE
  "frame $f rc=$rc $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
}
Remove-Item Env:\STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
"frames end $(Get-Date -Format o)" | Out-File $log -Append -Encoding utf8
