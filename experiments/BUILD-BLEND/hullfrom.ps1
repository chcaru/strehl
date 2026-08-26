# `--hull-from` sweep: does confining the per-level hull bound to COARSE levels
# kill the clip without paying acuity?
#
# PROTOCOL is ORCH's clean one (C:\dev\strehl-out\ORCH-CLAMP\clean.ps1), which
# corrected a 2x inflation caused by confounding merge with lateral CA and with
# two different fitted tone curves. Camera-linear both arms, CA and photometric
# explicitly unset, --gate 4, --base-mean.
#
# REGISTERED PREDICTIONS, written before the first render:
#
#   The 2x2 factorial attributes 56% of the clip to the newly SELECTED coarsest
#   band and 3% to the exponent ramp. If that attribution is right, the
#   excursion is BORN at the coarse end and compounds downward through the
#   expands, so bounding at level 5-6 alone should remove most of the clip.
#
#   P1  --hull-from 6 removes a LARGE share of the 1.4015% clip.
#   P2  acuity at --hull-from 6 is within noise of the ref (>= 0.99). The
#       acuity statistics are a p99.9 gradient and a 2 px high-pass; a bound at
#       55 px has no mechanism to move either. If acuity DOES fall at
#       --hull-from 6, my mechanism story is wrong and the loss is not local to
#       the scale being bounded.
#   P3  clip falls monotonically as hull-from decreases (more levels bounded).
#   P4  acuity falls monotonically as hull-from decreases, reaching the already
#       measured ~0.953 at hull-from 1 (= plain --per-level).
#
#   The interesting outcome is P1 AND P2 together: clip bought at no acuity
#   cost, because the bound never touches a scale the eye or the metric reads.
#   The falsifying outcome is P2 failing -- that would say the acuity cost of
#   PerLevel is NOT paid at the level being bounded, and the whole
#   scale-separation argument collapses.
#
# All arms rendered by ONE binary so binary drift cannot confound the
# blend-vs-blend comparison. ORCH's legacy ctrl is the target, not an arm.
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$tgt = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep"
$bex = "$tgt\release\examples\blend-render.exe"
$out = "C:\dev\strehl-out\BUILD-BLEND\hullfrom"
$src = "D:\personal\macro\flower-bud-alone-cpl"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

if (-not (Test-Path $bex)) { "MISSING BINARY: $bex"; exit 1 }
if (-not (Test-Path $src)) { "MISSING SOURCE: $src"; exit 1 }
"blendrnd : $((Get-FileHash $bex -Algorithm SHA256).Hash.Substring(0,16))"
"CA       : $(if ($env:STREHL_FIX_CA) { $env:STREHL_FIX_CA } else { '<unset OK>' })"
"frames   : $((Get-ChildItem "$src\*.ARW" -EA SilentlyContinue).Count)"
""

# Arm name -> extra flags. "ref" is hull=InputRange, the 1.4015% arm.
$arms = [ordered]@{
  "ref"  = @()
  "hf6"  = @("--hull-from", "6")
  "hf4"  = @("--hull-from", "4")
  "hf2"  = @("--hull-from", "2")
}

foreach ($a in $arms.Keys) {
  $tif = "$out\flower-bud-alone-cpl--$a.tiff"
  $log = "$out\$a.log"
  if (Test-Path $tif) { "  $a already rendered, skipping"; continue }
  $sw = [Diagnostics.Stopwatch]::StartNew()
  # NOTE: redirect to a FILE. Piping to Select-Object -First N closes the pipe
  # and kills the renderer mid-run, which reports as exit -1 and reads exactly
  # like a merge failure. That cost a full cycle once already.
  & $bex $src $tif --gate 4 --base-mean --camera-linear @($arms[$a]) *> $log
  $rc = $LASTEXITCODE
  $sw.Stop()
  $mb = if (Test-Path $tif) { [math]::Round((Get-Item $tif).Length/1MB, 1) } else { 0 }
  "  {0,-5} exit={1,-4} wall={2,7:N1}s  {3,7:N1} MB" -f $a, $rc, $sw.Elapsed.TotalSeconds, $mb
  if ($rc -ne 0) { "    !! FAILED"; Get-Content $log -Tail 10 | ForEach-Object { "     $_" } }
}

"`n=== size check: a resolution mismatch wrecks every gradient statistic ==="
Get-ChildItem "$out\*.tiff" | ForEach-Object { "  {0,-42} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }

"`n=== CA must be absent from every log ==="
Get-ChildItem "$out\*.log" | ForEach-Object {
  $hit = Select-String -Path $_.FullName -Pattern 'lateral CA' -SimpleMatch
  "  {0,-14} {1}" -f $_.Name, $(if ($hit) { "PRESENT -- CONFOUNDED" } else { "absent OK" })
}
"DONE"
