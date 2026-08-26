# n=2 -> n=6 for the silhouette discriminator. Classification and thresholds are
# fixed in PREREG-silhouette.md, written before this ran.
#
# Identical protocol to clean.ps1: both arms camera-linear, CA and photometric
# unset in BOTH, --gate 4, full resolution.
$ErrorActionPreference = "Continue"
$pin = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28"
$exe = "$pin\target\release\strehl.exe"
$bex = "$pin\target\release\examples\blend-render.exe"
$out = "C:\dev\strehl-out\ORCH-CLAMP\clean6"

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

# Carry the generating pair across by hardlink so accept2 scores all six under
# one invocation with one commissioning pass. Rendering them again would only
# risk a different pin.
foreach ($f in Get-ChildItem "C:\dev\strehl-out\ORCH-CLAMP\clean\*.tiff" -EA SilentlyContinue) {
  $dst = Join-Path $out $f.Name
  if (-not (Test-Path $dst)) { New-Item -ItemType HardLink -Path $dst -Target $f.FullName | Out-Null }
}

# NOTE: `strehl stack` BINS 2x2 by default (3520x2344). blend-render emits full
# 7040x4688. Without --demosaic the two arms differ by 4x in area and every
# gradient statistic is meaningless. The first run of this script omitted it and
# produced four unusable 47.2 MB ctrl arms.
$subjects = @("tweezers-cpl", "dry-erase-marker-head-cpl", "wrapped-text-1", "flat-on-ruler-cpl")

function Run-Arm($name, $log, $block) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $block 2>&1 | Out-File -FilePath $log -Encoding utf8
  $rc = $LASTEXITCODE
  $sw.Stop()
  "    {0,-30} exit={1} wall={2,7:N1} s" -f $name, $rc, $sw.Elapsed.TotalSeconds
  if ($rc -ne 0) { "      !! FAILED:"; Get-Content $log -Tail 14 | ForEach-Object { "       $_" } }
}

foreach ($s in $subjects) {
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { "  SKIP $s (not found)"; continue }
  $n = (Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count
  "`n=== $s ($n frames) ==="
  if (Test-Path "$out\$s--ctrl.tiff") { "    ctrl  already present, skipping" }
  else {
    Run-Arm "ctrl  legacy camera-linear" "$out\$s-ctrl.log" `
      { & $exe stack $src --out "$out\$s--ctrl.tiff" --gate 4 --demosaic }
  }
  if (Test-Path "$out\$s--blend.tiff") { "    blend already present, skipping" }
  else {
    Run-Arm "blend pyramid camera-linear" "$out\$s-blend.log" `
      { & $bex $src "$out\$s--blend.tiff" --gate 4 --base-mean --camera-linear }
  }
}

"`n=== outputs (ctrl and blend MUST match in size) ==="
Get-ChildItem "$out\*.tiff" -EA SilentlyContinue | ForEach-Object { "  {0,-46} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }

"`n=== confound guard: lateral CA must be OFF, not merely mentioned ==="
# The first version matched the LABEL 'lateral CA' and fired on
# `lateral CA : off (STREHL_FIX_CA unset)` -- which is the state we want. A
# presence check is not a state check. Outcomes are counted separately so a log
# that never reports CA cannot read as a log that reported OFF.
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
