# BUILD-BLEND -- the four sub-gate fallback arms, scored on ORCH's three
# instruments plus accept2.
#
# ORCH resolved (A) vs (B): sub-gate content in the notch bin is STRUCTURE
# (lag-1 0.7140 against a synthetic i.i.d.-noise pole of 0.2107), and the
# pyramid replaces it with something flatter and uncorrelated (r = 0.1156
# against a strong-edge pole of 0.9713). So this sweep is not a
# discrimination, it is a comparison of candidate repairs.
#
# --hard-max is deliberate and is ORCH's condition: above the gate it copies
# one frame's coefficient verbatim, so the fallback is the only remaining
# mechanism and nothing is confounded by weighting.
#
# PRE-REGISTERED PREDICTIONS, written before any arm was rendered:
#
#   P1  mean reproduces ORCH's published numbers: notch ampRatio 0.3292,
#       r(aligned) 0.1156, pyramid lag-1 0.5708. If it does not, the
#       comparison is not on ORCH's axis and every other row is void.
#   P2  best fills the notch amplitude furthest of the four but scores WORST
#       on the flat-bin guard rail, because a per-pixel max over 100 noise
#       samples is a positively biased, high-variance estimator. Amplitude
#       without correlation is the failure ORCH said it would fail an arm for.
#   P3  topk k=3 improves the notch and degrades the flat bins, in between
#       mean and best on both. Whether it clears BOTH ends is the open
#       question and I do not predict it.
#   P4  power p=4 holds the flat bins closest to mean of the three repairs,
#       because near-uniform |L| across frames drives its weights to uniform
#       and it degrades to the mean by construction. If P4 fails, the
#       adaptivity argument for Power is wrong and I retract it.
#
# A NOTE ON WHAT THIS SCRIPT CANNOT SETTLE: I am the author of these arms.
# ORCH re-runs the instruments independently and that run is the one that
# counts. This exists to stop me nominating an arm I have not looked at.

# NOTE ON $ErrorActionPreference: it is deliberately NOT "Stop". blend-render
# writes its banner to stderr, and with `*>` redirection under Stop that
# becomes a terminating NativeCommandError on the FIRST arm -- the render
# succeeds and the script dies anyway. Explicit rc checks below instead.
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$subject = "tweezers-cpl"
$src     = "D:\personal\macro\$subject"
$ctrl    = "C:\dev\strehl-out\ORCH-CLAMP\clean6\$subject--ctrl.tiff"
$tgt     = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep"
$bex     = "$tgt\release\examples\blend-render.exe"
$root    = "C:\dev\strehl-out\BUILD-BLEND\fallback"
$inst    = "C:\dev\strehl-out\ORCH-CLAMP"

foreach ($p in @($src, $ctrl, $bex)) {
  if (-not (Test-Path $p)) { throw "missing input: $p" }
}
# ORCH's reference arm was rendered with lateral CA OFF, and its log records
# "off (STREHL_FIX_CA unset)". That protocol is STALE: the default flipped
# between their pin and HEAD, so leaving the variable unset now turns CA ON
# and the arms stop being comparable to the ctrl they are scored against.
# Set it off explicitly and assert the log agrees.
$env:STREHL_FIX_CA = "off"

$arms = [ordered]@{
  "mean"  = @("--fallback", "mean")
  "best"  = @("--fallback", "best")
  "topk3" = @("--fallback", "topk", "--fallback-k", "3")
  "pow4"  = @("--fallback", "power", "--fallback-power", "4")
}

"subject  : $subject"
"frames   : $((Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count)"
"binary   : $bex"
"commit   : $(& git -C C:\dev\blog\death-of-software\projects\strehl rev-parse --short HEAD)"
""

foreach ($a in $arms.Keys) {
  $out = "$root\$a"
  New-Item -ItemType Directory -Force -Path $out | Out-Null
  $tif = "$out\$subject--blend.tiff"
  $log = "$out\$subject--blend.log"

  # Hardlink rather than copy: the ctrl is 198 MB and four copies buy
  # nothing. Same volume, so this is free.
  $lnk = "$out\$subject--ctrl.tiff"
  if (-not (Test-Path $lnk)) { New-Item -ItemType HardLink -Path $lnk -Target $ctrl | Out-Null }

  if (Test-Path $tif) { "SKIP  $a (already rendered)"; continue }
  "RENDER $a ..."
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $bex $src $tif --hard-max --gate 4 --base-mean --camera-linear @($arms[$a]) *> $log
  $rc = $LASTEXITCODE
  $sw.Stop()
  "   rc=$rc  $([int]$sw.Elapsed.TotalSeconds)s  $((Get-Item $tif -EA SilentlyContinue).Length/1MB -as [int]) MB"
  if ($rc -ne 0 -or -not (Test-Path $tif)) { "   FAILED -- see $log"; continue }

  # Guard: if CA is on, this arm is not comparable to ORCH's ctrl and every
  # number derived from it is confounded. Fail loudly rather than quietly.
  $ca = (Select-String -Path $log -Pattern 'lateral CA' | Select-Object -First 1).Line
  "   $($ca -replace '\s+', ' ')"
  if ($ca -notmatch 'off') { throw "CA is ON for arm $a -- not comparable to the ctrl" }
  (Select-String -Path $log -Pattern 'averaged' | Select-Object -First 1).Line
}

""
"=============== INSTRUMENTS ==============="
foreach ($a in $arms.Keys) {
  $out = "$root\$a"
  if (-not (Test-Path "$out\$subject--blend.tiff")) { continue }
  foreach ($i in @("ampcurve", "structure", "whitetest")) {
    $s = "$inst\$i.py"
    if (-not (Test-Path $s)) { "  (missing instrument $i.py)"; continue }
    "----- $a / $i -----"
    & python $s $out $subject *> "$out\$i.txt"
    Get-Content "$out\$i.txt"
  }
  "----- $a / accept2 -----"
  & python "$inst\accept2.py" $out --ref ctrl *> "$out\accept2.txt"
  Get-Content "$out\accept2.txt"
}
