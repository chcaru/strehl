# Render each subject once, capturing BOTH the merged image and the election
# map (the pass-one winner field, values = 0-based frame index, plane grid =
# half resolution per axis).
#
# The election map is a DEPTH ordering, not a brightness one, which is the
# whole point: two luminance-threshold silhouettes have already failed on these
# subjects -- a white flower on grey defeats a global threshold, and a
# median-over-focus image is smeared by the very defocus under study.
$exe = "C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"
$out = "C:\dev\strehl-out\VEIL"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Write-Output ("binary sha256 : " + (Get-FileHash $exe -Algorithm SHA256).Hash)

foreach ($s in @("lavendar-cpl","flower-bud-with-background-fern-cpl")) {
  $tif = Join-Path $out "$s-elect-render.tif"
  $map = Join-Path $out "$s-election.tif"
  if (Test-Path $map) { Write-Output "skip $s"; continue }
  Remove-Item Env:STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
  Remove-Item Env:STREHL_EDGE_AWARE -ErrorAction SilentlyContinue
  $env:STREHL_DUMP_ELECTION = $map
  $ErrorActionPreference = "Continue"
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $exe stack "D:\personal\macro\$s" --out $tif 2>&1 | Select-String -Pattern "election|collapse veto" | Select-Object -First 3
  $rc = $LASTEXITCODE
  $sw.Stop()
  Write-Output ("  {0}  rc={1}  {2:n1}s" -f $s, $rc, $sw.Elapsed.TotalSeconds)
}
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
Get-ChildItem $out -Filter *election*.tif | ForEach-Object { "{0,-56} {1}" -f $_.Name, $_.Length }
