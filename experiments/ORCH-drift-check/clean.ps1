# Clean merge isolation: legacy `strehl stack` vs pyramid `blend-render`.
#
# The BUILD-BLEND bm/ pairs confound THREE changes and attribute them to one:
#   1. merge algorithm   (legacy estimator vs Laplacian multi-band)
#   2. lateral CA        (env set globally, but only blend-render honoured it)
#   3. tone curve        (both --srgb, with DIFFERENT fitted black/white points)
#
# This isolates (1): both arms camera-linear (no tone), CA explicitly off for both.
$ErrorActionPreference = "Continue"
$pin = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28"
$exe = "$pin\target\release\strehl.exe"
$bex = "$pin\target\release\examples\blend-render.exe"
$out = "C:\dev\strehl-out\ORCH-CLAMP\clean"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($p in @($exe, $bex)) {
  if (-not (Test-Path $p)) { "MISSING BINARY: $p"; exit 1 }
}
"pin      : $pin"
"strehl   : $((Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0,16))"
"blendrnd : $((Get-FileHash $bex -Algorithm SHA256).Hash.Substring(0,16))"
"CA       : $(if ($env:STREHL_FIX_CA) { $env:STREHL_FIX_CA } else { '<unset - OFF for both arms>' })"
""

# flower-bud-alone-cpl : the clipper, large featureless backdrop, halo subject
# couch-fibers-cpl     : the control -- fine texture, no silhouette, clips exactly 0
$subjects = @("flower-bud-alone-cpl", "couch-fibers-cpl")

function Run-Arm($name, $log, $block) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $block 2>&1 | Out-File -FilePath $log -Encoding utf8
  $rc = $LASTEXITCODE
  $sw.Stop()
  "    {0,-28} exit={1} wall={2,7:N1} s" -f $name, $rc, $sw.Elapsed.TotalSeconds
  if ($rc -ne 0) { "      !! FAILED:"; Get-Content $log -Tail 12 | ForEach-Object { "       $_" } }
}

foreach ($s in $subjects) {
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { "  SKIP $s (not found)"; continue }
  $n = (Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count
  "`n=== $s ($n frames) ==="
  Run-Arm "ctrl  legacy camera-linear" "$out\$s-ctrl.log" `
    { & $exe stack $src --out "$out\$s--ctrl.tiff" --gate 4 }
  Run-Arm "blend pyramid camera-linear" "$out\$s-blend.log" `
    { & $bex $src "$out\$s--blend.tiff" --gate 4 --base-mean --camera-linear }
}

"`n=== outputs ==="
Get-ChildItem "$out\*.tiff" -EA SilentlyContinue | ForEach-Object { "  {0,-46} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }

"`n=== CA line present in either log? (must be absent in BOTH) ==="
Get-ChildItem "$out\*.log" | ForEach-Object {
  $hit = Select-String -Path $_.FullName -Pattern 'lateral CA' -SimpleMatch
  "  {0,-40} {1}" -f $_.Name, $(if ($hit) { "PRESENT -- CONFOUNDED: $($hit[0].Line.Trim())" } else { "absent OK" })
}
"DONE"
