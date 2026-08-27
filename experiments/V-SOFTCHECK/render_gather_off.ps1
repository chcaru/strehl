# Render the COMPLETE bracket through the OLD per-phase-plane gather
# (STREHL_FULLRES_GATHER=0), so the plane-Nyquist wall can be priced against
# the shipping default rather than argued about.  Both arms come from the SAME
# pin, so the gather is the only variable.
param([string]$Subject = "119MSDCF", [string]$ExpStops = "+1.53")
$bin  = "C:\dev\strehl-out\V-SOFTCHECK\bin\strehl.exe"
$root = "C:\dev\strehl-out\V-SOFTCHECK\srgb-gatheroff\$Subject"
New-Item -ItemType Directory -Force -Path $root | Out-Null
foreach ($v in @("STREHL_FIX_CA","STREHL_EDGE_AWARE","STREHL_EDGE_TAU","STREHL_EDGE_CONF",
                 "STREHL_ACUITY","STREHL_MERGE","STREHL_WARPMAP","STREHL_ALIGN","STREHL_SOFT_GATE",
                 "STREHL_PHOTOMETRIC","STREHL_FIX_HALO","STREHL_VEIL","STREHL_COVER")) {
  Remove-Item "env:$v" -EA SilentlyContinue
}
$env:STREHL_FULLRES_GATHER = "0"
$n = (Get-ChildItem "D:\personal\macro\$Subject" -Filter *.ARW).Count
Remove-Item "env:STREHL_ONLY_FRAME" -EA SilentlyContinue
& $bin stack "D:\personal\macro\$Subject" --out "$root\master.tiff" --srgb --exposure $ExpStops 2>&1 |
  Out-File "$root\master.log"
for ($k = 0; $k -lt $n; $k++) {
  $env:STREHL_ONLY_FRAME = "$k"
  $f = "{0}\f{1:d3}.tiff" -f $root, $k
  & $bin stack "D:\personal\macro\$Subject" --out $f --srgb --exposure $ExpStops 2>&1 |
    Out-File ("{0}\f{1:d3}.log" -f $root, $k)
}
Remove-Item "env:STREHL_ONLY_FRAME" -EA SilentlyContinue
$got = (Get-ChildItem $root -Filter "f*.tiff").Count
Write-Host "GATHER-OFF $Subject : $got of $n frames; master exists = $(Test-Path "$root\master.tiff")"
