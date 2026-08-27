param([string]$Subject, [string]$Gauge = "lin", [string]$ExpStops = "")
$bin  = "C:\dev\strehl-out\V-SOFTCHECK\bin\strehl.exe"
$src  = "D:\personal\macro\$Subject"
$root = "C:\dev\strehl-out\V-SOFTCHECK\$Gauge\$Subject"
New-Item -ItemType Directory -Force -Path $root | Out-Null
foreach ($v in @("STREHL_FIX_CA","STREHL_EDGE_AWARE","STREHL_EDGE_TAU","STREHL_EDGE_CONF","STREHL_MERGE",
                 "STREHL_ALIGN","STREHL_CACHE_DIR","STREHL_PYRAMID_WORKERS","STREHL_ONLY_FRAME",
                 "STREHL_WARPMAP","STREHL_FIX_HALO_DELTA","STREHL_ACUITY","STREHL_FULLRES_GATHER")) {
  if (Test-Path "Env:\$v") { Remove-Item "Env:\$v" }
}
$flags = @()
if ($Gauge -eq "srgb") { $flags = @("--srgb","--exposure",$ExpStops) }
$n = (Get-ChildItem "$src\*.ARW").Count
Write-Host "SUBJECT $Subject  gauge=$Gauge  frames=$n  flags=$flags"
# master: complete bracket, no ONLY_FRAME
if (-not (Test-Path "$root\master.tiff")) {
  & $bin stack $src --out "$root\master.tiff" @flags 2>&1 | Out-File "$root\master.log" -Encoding utf8
}
for ($k = 0; $k -lt $n; $k++) {
  $f = "$root\f{0:d3}.tiff" -f $k
  if (Test-Path $f) { continue }
  $env:STREHL_ONLY_FRAME = "$k"
  & $bin stack $src --out $f @flags 2>&1 | Out-File ("$root\f{0:d3}.log" -f $k) -Encoding utf8
  Remove-Item Env:\STREHL_ONLY_FRAME
}
$got = (Get-ChildItem "$root\f*.tiff").Count
Write-Host "RENDERED $got of $n single-frame files; master exists = $(Test-Path "$root\master.tiff")"
if ($got -ne $n) { Write-Host "INCOMPLETE" } else { Write-Host "COMPLETE" }
