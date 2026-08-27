# BUILD-BLEND -- does the veil win survive at gate 2?  (ORCH request 3a)
#
# ORCH measured the veil reduction at --gate 4, but MergeConfig::default() is
# gate 2.0, so the wired-in pyramid is a different build from the one the veil
# win was measured on. Two lines separate the shipped product from the
# measured one and one of them is the gate.
#
# PROTOCOL NOTES THAT MATTER FOR COMPARABILITY:
#
# 1. Lateral CA. ORCH's clean6 ctrl log records 'off (STREHL_FIX_CA unset)'.
#    That protocol is STALE -- the default flipped between their pin and HEAD,
#    so leaving the variable unset NOW turns CA on and the arm stops being
#    comparable to the ctrl it is scored against. Set off explicitly, assert
#    the log agrees, and fail the arm if it does not.
#
# 2. One veilpair invocation per subject carrying ctrl + gate4 + gate2
#    together. veilpair.py builds the subject mask and distance transform once
#    from the reference and applies it unchanged to every arm, so passing all
#    three in one call guarantees an identical pixel population. Scoring gate2
#    in a separate run would let the mask differ and reintroduce exactly the
#    confound ORCH built the tool to remove.
#
# 3. The gate-4 arm is ORCH's own clean6 render, not a re-render. That keeps
#    their published numbers reproducible as the middle column.
#
# PRE-REGISTERED, before any render:
#   Q1 does gate 2 keep the veil reduction? I do not predict the direction.
#      The veil is a LOW-frequency, large-scale quantity (measured out to 200
#      px), and the gate sweep showed everything above 272 DN is completely
#      gate-independent (0.9833-0.9882 over a 16x gate range). If the veil
#      lives in that gate-independent population, gate 2 keeps it.
#   Q2 my honest expectation from Q1's reasoning is that it DOES survive,
#      which would mean the gate can be chosen on detail/noise grounds alone
#      -- ORCH's own stated consequence.

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$subjects = @("flower-bud-alone-cpl", "dry-erase-marker-head-cpl")
$clean6   = "C:\dev\strehl-out\ORCH-CLAMP\clean6"
$bex      = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe"
$root     = "C:\dev\strehl-out\BUILD-BLEND\gate2veil"
$veil     = "C:\dev\strehl-out\ORCH-CLAMP\veilpair.py"

foreach ($p in @($bex, $veil)) { if (-not (Test-Path $p)) { throw "missing: $p" } }
$env:STREHL_FIX_CA = "off"
New-Item -ItemType Directory -Force -Path $root | Out-Null

"binary : $bex"
"commit : $(& git -C C:\dev\blog\death-of-software\projects\strehl rev-parse --short HEAD)"
""

foreach ($s in $subjects) {
  $src   = "D:\personal\macro\$s"
  $ctrl  = "$clean6\$s--ctrl.tiff"
  $g4    = "$clean6\$s--blend.tiff"
  $g2    = "$root\$s--gate2.tiff"
  $log   = "$root\$s--gate2.log"

  "===== $s ====="
  foreach ($p in @($src, $ctrl, $g4)) {
    if (-not (Test-Path $p)) { "  MISSING $p -- skipping subject"; continue }
  }
  if (-not (Test-Path $src) -or -not (Test-Path $ctrl) -or -not (Test-Path $g4)) { continue }

  if (-not (Test-Path $g2)) {
    "  RENDER gate 2 ($((Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count) frames) ..."
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $bex $src $g2 --gate 2 --base-mean --camera-linear *> $log
    $rc = $LASTEXITCODE
    $sw.Stop()
    "   rc=$rc  $([int]$sw.Elapsed.TotalSeconds)s"
    if ($rc -ne 0 -or -not (Test-Path $g2)) { "   FAILED -- see $log"; continue }
    $ca = (Select-String -Path $log -Pattern 'lateral CA' | Select-Object -First 1).Line
    "   $($ca -replace '\s+',' ')"
    if ($ca -notmatch 'off') { throw "CA is ON for $s -- not comparable to the ctrl" }
    (Select-String -Path $log -Pattern 'averaged' | Select-Object -First 1).Line
  } else { "  SKIP render (exists)" }

  # ctrl first = the reference the mask is built from; then the two arms.
  "  --- veilpair: ctrl | gate4 | gate2 ---"
  & python $veil $ctrl $g4 $g2 *> "$root\$s--veil.txt"
  Get-Content "$root\$s--veil.txt"
  ""
}
