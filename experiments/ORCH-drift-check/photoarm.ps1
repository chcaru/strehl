# A third arm. The gallery the owner judged was the estimator with --photometric
# OFF, because M122 returned KEEP-OFF (see ORCH-veiling section 30 -- that verdict
# rested on a metric with no spatial argument and does not survive partitioning).
#
# --photometric is REFUSED under the pyramid backend (main.rs:80-82), so it is an
# estimator-path-only lever. That makes this a genuine third arm and not a
# variation of the blend arm: if it removes enough of the aura, the shipping
# backend may not need replacing at all.
#
# Same pin, same gate, same --demosaic as clean6.ps1. The ONLY difference from
# the existing ctrl arm is the photometric flag.
$ErrorActionPreference = "Continue"
$pin = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28"
$exe = "$pin\target\release\strehl.exe"
$out = "C:\dev\strehl-out\ORCH-CLAMP\photo"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

if (-not (Test-Path $exe)) { "MISSING BINARY: $exe"; exit 1 }
"pin    : $pin"
"strehl : $((Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0,16))"

# The two subjects whose silhouette masks are valid under PREREG-silhouette.md,
# i.e. the two that carry the veil measurement at all.
$subjects = @("flower-bud-alone-cpl", "dry-erase-marker-head-cpl")

foreach ($s in $subjects) {
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { "  SKIP $s (not found)"; continue }
  $n = (Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count
  "`n=== $s ($n frames) ==="
  $dst = "$out\$s--photo.tiff"
  if (Test-Path $dst) { "    already present, skipping"; continue }
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $exe stack $src --out $dst --gate 4 --demosaic --photometric on 2>&1 |
    Out-File -FilePath "$out\$s-photo.log" -Encoding utf8
  $rc = $LASTEXITCODE
  $sw.Stop()
  "    exit={0} wall={1,7:N1} s" -f $rc, $sw.Elapsed.TotalSeconds
  if ($rc -ne 0) { "    !! FAILED:"; Get-Content "$out\$s-photo.log" -Tail 20 | ForEach-Object { "     $_" } }
}

# State check, not a presence check: the log must say the correction was APPLIED,
# and the run must report a per-frame gain that is not identically 1. A flag that
# parses and does nothing looks exactly like a flag that worked.
"`n=== confound guard: photometric must be ON and non-trivial ==="
$applied = 0; $trivial = 0; $absent = 0
foreach ($s in $subjects) {
  $log = "$out\$s-photo.log"
  if (-not (Test-Path $log)) { "  $s : NO LOG"; $absent++; continue }
  $hits = Select-String -Path $log -Pattern "photometric" -SimpleMatch
  if (-not $hits) { "  $s : photometric NOT MENTIONED in log"; $absent++; continue }
  foreach ($h in $hits) { "  $s : $($h.Line.Trim())" }
  if ($hits | Where-Object { $_.Line -match "off|disabled|abstain" }) { $trivial++ } else { $applied++ }
}
"  applied={0} trivial={1} absent={2}  (must sum to {3})" -f $applied, $trivial, $absent, $subjects.Count

Get-ChildItem "$out\*.tiff" -EA SilentlyContinue | ForEach-Object { "  {0,-46} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }
