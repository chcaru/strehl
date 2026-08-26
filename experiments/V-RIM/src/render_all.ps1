# V-RIM render driver: linear, camera-native, full-res demosaic. NO --srgb.
$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
$lib  = "D:\personal\macro"
$out  = "C:\dev\strehl-out\V-RIM\lin"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# coffee-bean and flower-bud first: re-rendering them lets me hash-compare
# against ORCH's own TIFFs, which is a free provenance check.
$order = @(
  "coffee-bean","flower-bud-alone-cpl",
  "109MSDCF","112MSDCF","113MSDCF","119MSDCF",
  "bee-1-cpl","bee-2-cpl","bee-3-cpl",
  "coffee-bubbles","couch-fibers-cpl","dry-erase-marker-head-cpl",
  "flat-on-ruler-cpl","flower-bud-with-background-fern-cpl",
  "flower-inner-edge-cpl","flowers-cpl","foam",
  "highly-angled-ruler-mm-cpl","lavendar-cpl","lead-1-cpl","leaf-2-cpl",
  "pencil-flatter-angle-cpl","pencil-steep-angle-cpl","tweezers-cpl",
  "wrapped-text-1","wrapped-text-2"
)

$log = Join-Path $out "RENDER.log"
"V-RIM render start $(Get-Date -Format o)" | Out-File -FilePath $log -Encoding utf8
"binary sha256 $((Get-FileHash $exe -Algorithm SHA256).Hash)" | Out-File -FilePath $log -Append -Encoding utf8
"command: strehl stack <DIR> --out <TIFF> --demosaic   (no --srgb)" | Out-File -FilePath $log -Append -Encoding utf8

foreach ($s in $order) {
  $dir = Join-Path $lib $s
  $tif = Join-Path $out "$s-lin.tif"
  if (Test-Path $tif) { "SKIP  $s (exists)" | Out-File -FilePath $log -Append -Encoding utf8; continue }
  $t0 = Get-Date
  $slog = Join-Path $out "$s.renderlog"
  & $exe stack $dir --out $tif --demosaic *> $slog
  $rc = $LASTEXITCODE
  $dt = ((Get-Date) - $t0).TotalSeconds
  $sz = if (Test-Path $tif) { (Get-Item $tif).Length } else { 0 }
  "DONE  {0,-40} rc={1} {2,7:N0}s {3,12} bytes" -f $s, $rc, $dt, $sz | Out-File -FilePath $log -Append -Encoding utf8
}
"V-RIM render end $(Get-Date -Format o)" | Out-File -FilePath $log -Append -Encoding utf8
