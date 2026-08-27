param([string]$Subject, [string]$Exposure, [int]$Nmax = 0)
# V-GATHER: render a subject's master AND per-frame single-frame arms from ONE
# binary with ONE flag set, so numerator and denominator share every stage:
# demosaic, CA, colour matrix, exposure gain, sRGB curve, and (COVER=0) geometry.
$pin  = "C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
$src  = "D:\personal\macro\$Subject"
$out  = "C:\dev\strehl-out\V-GATHER\sharp\$Subject"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_COVER = "0"
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\V-GATHER\sharp\_cache\$Subject"
New-Item -ItemType Directory -Force -Path $env:STREHL_CACHE_DIR | Out-Null
$n = (Get-ChildItem "$src\*.ARW").Count
$idx = if ($Nmax -gt 0 -and $Nmax -lt $n) { 0..($Nmax-1) | ForEach-Object { [int][math]::Round($_ * ($n-1) / ($Nmax-1)) } } else { 0..($n-1) }
$idx = $idx | Select-Object -Unique
Write-Host "$Subject : $n frames on disk, rendering master + $($idx.Count) single-frame arms, exposure=$Exposure"

Remove-Item Env:\STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
$mp = "$out\MASTER.tiff"
if (-not (Test-Path $mp)) {
  $sw=[Diagnostics.Stopwatch]::StartNew()
  & $pin stack $src --out $mp --srgb "--exposure=$Exposure" 2>"$out\MASTER.log" | Out-Null
  Write-Host ("  MASTER  {0,6:N1}s  exit {1}" -f $sw.Elapsed.TotalSeconds, $LASTEXITCODE)
}
foreach ($k in $idx) {
  $fp = "$out\f{0:d4}.tiff" -f $k
  if (Test-Path $fp) { continue }
  $env:STREHL_ONLY_FRAME = "$k"
  & $pin stack $src --out $fp --srgb "--exposure=$Exposure" 2>("$out\f{0:d4}.log" -f $k) | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Host "  frame $k FAILED exit $LASTEXITCODE" }
}
Remove-Item Env:\STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
Write-Host ("  done: {0} tiffs" -f (Get-ChildItem "$out\*.tiff").Count)
