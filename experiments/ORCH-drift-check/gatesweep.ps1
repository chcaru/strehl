# Does the band-pass notch move with the pyramid noise gate?
#
# ampcurve.py found a deep notch in the pyramid/estimator band-pass ratio at a
# reference amplitude near 40 DN, on subjects whose amplitude ranges differ by
# 4x -- tweezers 0.3111 at 31-53 DN, flower-bud 0.4562 at 42-55 DN, recovering
# to ~0.98 high and >1.0 in the flattest tiles. A defect pinned to a constant
# ABSOLUTE DN across scenes is a threshold, not a contrast effect.
#
# pyramid.rs:638-647 has exactly one such threshold: `MergeConfig::gate`, "how
# many multiples of the modelled band-noise power a coefficient's local energy
# must exceed before it may influence selection. Below it NO frame wins and the
# merge averages." The clean6 blend arm was rendered at --gate 4.
#
# PRE-REGISTERED PREDICTION, written before this ran.
#   The gate is a threshold on POWER; the curve's x-axis is AMPLITUDE. So if the
#   notch is the gate crossover, its position must scale as sqrt(gate):
#
#       gate  1  ->  notch at ~0.50x of the gate-4 position   (~20 DN)
#       gate  4  ->  the measured position                    (~40 DN)
#       gate 16  ->  ~2.0x                                    (~80 DN)
#
#   REFUTED if the notch does not move, or moves the wrong way, or moves by a
#   factor unrelated to sqrt(gate). A notch that stays put under a 16x change in
#   the only threshold on that axis is not that threshold's fault.
#
# The estimator reference arm is held FIXED across all three -- it is not being
# varied and must not be re-rendered, or the ratio's denominator moves under the
# thing being measured.
$ErrorActionPreference = "Continue"
$pin  = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28"
$bex  = "$pin\target\release\examples\blend-render.exe"
$src  = "D:\personal\macro\tweezers-cpl"
$ctrl = "C:\dev\strehl-out\ORCH-CLAMP\clean6\tweezers-cpl--ctrl.tiff"
$root = "C:\dev\strehl-out\ORCH-CLAMP\gatesweep"

foreach ($p in @($bex, $ctrl, $src)) {
  if (-not (Test-Path $p)) { "MISSING: $p"; exit 1 }
}
"blend-render : $((Get-FileHash $bex -Algorithm SHA256).Hash.Substring(0,16))"
"reference    : held fixed, $(Split-Path $ctrl -Leaf)"
"frames       : $((Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count)"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue

foreach ($g in @(1, 4, 16)) {
  $d = "$root\g$g"
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  $lnk = "$d\tweezers-cpl--ctrl.tiff"
  if (-not (Test-Path $lnk)) { New-Item -ItemType HardLink -Path $lnk -Target $ctrl | Out-Null }
  $blend = "$d\tweezers-cpl--blend.tiff"
  if (Test-Path $blend) { "  gate $g : already rendered"; continue }
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $bex $src $blend --gate $g --base-mean --camera-linear 2>&1 |
    Out-File -FilePath "$d\render.log" -Encoding utf8
  $rc = $LASTEXITCODE
  $sw.Stop()
  "  gate {0,-3} exit={1} wall={2,6:N1} s" -f $g, $rc, $sw.Elapsed.TotalSeconds
  if ($rc -ne 0) { Get-Content "$d\render.log" -Tail 12 | ForEach-Object { "     $_" } }
}

# Guard: the three blend arms must be DIFFERENT files. If --gate silently did
# nothing, they would be identical and the sweep would read as "notch does not
# move" -- the refutation, produced by a broken instrument rather than by the
# merge. This is the same class as the CA label-vs-state defect.
"`n=== guard: the three arms must differ ==="
$h = @{}
foreach ($g in @(1, 4, 16)) {
  $f = "$root\g$g\tweezers-cpl--blend.tiff"
  if (Test-Path $f) { $h[$g] = (Get-FileHash $f -Algorithm SHA256).Hash.Substring(0, 16); "  gate {0,-3} {1}" -f $g, $h[$g] }
}
$u = ($h.Values | Sort-Object -Unique).Count
"  distinct hashes: $u of $($h.Count)"
if ($u -lt $h.Count) { "  !! --gate DID NOT CHANGE THE OUTPUT -- DO NOT READ THE SWEEP"; exit 1 }
"  all arms distinct OK"
"DONE"
