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
    { & $exe stack $src --out "$out\$s--ctrl.tiff" --gate 4 --demosaic }
  Run-Arm "blend pyramid camera-linear" "$out\$s-blend.log" `
    { & $bex $src "$out\$s--blend.tiff" --gate 4 --base-mean --camera-linear }
}

"`n=== outputs ==="
Get-ChildItem "$out\*.tiff" -EA SilentlyContinue | ForEach-Object { "  {0,-46} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }

"`n=== confound guard: lateral CA must be OFF, not merely mentioned ==="
# An earlier version of this guard matched the LABEL 'lateral CA' and fired on
# `lateral CA : off (STREHL_FIX_CA unset)`, which is the state we want. A
# presence check is not a state check. Outcomes are counted separately so that
# a log which never reports CA at all cannot read as a log that reported OFF.
$on = 0; $off = 0; $silent = 0
Get-ChildItem "$out\*.log" -EA SilentlyContinue | ForEach-Object {
  $l = Get-Content $_.FullName -Raw
  if ($l -match 'lateral CA\s*:\s*on')      { $on++;  "  {0,-42} ON -- CONFOUNDED" -f $_.Name }
  elseif ($l -match 'lateral CA\s*:\s*off') { $off++ }
  else                                       { $silent++ }
}
"  off (explicitly reported) : $off"
"  ON  (CONFOUNDED)          : $on"
"  no CA line at all         : $silent   (legacy binary does not print one)"
"  total logs                : $($off + $on + $silent)"
if ($on -gt 0) { "  DO NOT READ THE RESULT" } else { "  CA off in every arm that reports it OK" }
"DONE"
