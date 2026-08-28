# V-SPEED halo assignment: path-scoped commit with index.lock retry.
# Nine other agents share this working tree, so `git add -A` and a bare
# `git commit` would sweep their files into my commit. Every path is named.
$ErrorActionPreference = 'Continue'
Set-Location C:\dev\blog\death-of-software\projects\strehl

$paths = @(
  'crates/strehl-core/src/pyramid.rs',
  'docs/research/V-SPEED-HALO.md',
  'experiments/V-DRIFT/clipaudit.py',
  'experiments/V-SPEED/aura.py',
  'experiments/V-SPEED/sharp.py',
  'experiments/V-SPEED/annulus.py',
  'experiments/V-SPEED/abscore.py',
  'experiments/V-SPEED/armprofile.py',
  'experiments/V-SPEED/decompose.py',
  'experiments/V-SPEED/auradump.py',
  'experiments/V-SPEED/halodiag.py',
  'experiments/V-SPEED/tweezers.py',
  'experiments/V-SPEED/sweepscore.py',
  'experiments/V-SPEED/sweep.ps1',
  'experiments/V-SPEED/ab.ps1',
  'experiments/V-SPEED/hullcommission.ps1',
  'experiments/V-SPEED/commit.ps1'
) | Where-Object { Test-Path $_ }

function Invoke-GitRetry {
  param([string[]]$GitArgs, [int]$Tries = 8)
  for ($i = 1; $i -le $Tries; $i++) {
    $out = & git @GitArgs 2>&1
    $rc = $LASTEXITCODE
    if ($rc -eq 0) { return @{ rc = 0; out = $out } }
    if ("$out" -match 'index\.lock') {
      Write-Host "  index.lock contention, attempt $i; waiting"
      Start-Sleep -Seconds ([Math]::Min(20, 3 * $i))
      continue
    }
    return @{ rc = $rc; out = $out }
  }
  return @{ rc = 1; out = 'gave up on index.lock' }
}

Write-Host "staging $($paths.Count) paths"
$r = Invoke-GitRetry -GitArgs (@('add', '--') + $paths)
Write-Host "  add rc=$($r.rc)"
if ($r.rc -ne 0) { Write-Host $r.out; exit 1 }

$msg = @'
V-SPEED: audit the halo premise, refute it, and refute the candidate fix

ORCH handed this lane four HALO verdicts from halo_profile.py (7 clean /
4 HALO / 15 skipped of 26) and asked for the mechanism and a fix. The
premise did not survive the audit and neither did my own best candidate.

The instrument. halo_profile.py's `overshoot` is a HEIGHT, not a
prominence: it never asks for background on both sides of the feature.
Its argmax lands in the outermost annulus on 11 of 11 scorable subjects,
and dry-erase-marker-head-cpl flips +236.7 -> -325.7 DN purely by moving
the reference annulus. Of ORCH's four: tweezers-cpl and
dry-erase-marker-head-cpl CONFIRMED; flat-on-ruler-cpl and lavendar-cpl
REFUTED as lighting arches (172 px and 124 px wide). It was also blind to
five real halos, including the most merge-driven one in the corpus.

The replacement. aura.py is reference-free, uses prominence against both
shoulders, and separates a halo from a lighting arch by WIDTH rather than
amplitude. Commissioned 8/8 through four self-inflicted defects, and it
scores 26 of 26 subjects where the old instrument scored 11. Baseline:
7 HALO / 7 gradient / 12 clean.

The mechanism is real but minority. Coarse-band selection ringing is
confirmed -- monotone in band count and in exponent, sitting in a coarse
band. But the no-selection floor arm (--pyramid-exponent 0.001
--pyramid-sharpen 1.0, same frames, same alignment, same tone pipeline)
leaves 84-90% of the measured halo standing on four of five tonally
comparable subjects. Only tweezers-cpl is majority-merge, at 25%.

The candidate fix refuted itself. --pyramid-bands 5 scored -91.2% on
dry-erase-marker-head-cpl, the best number in the corpus. Printing all
three arms' radial profiles on one shared mask shows it darkens 135 px by
966 DN more than 310 px, turning a local maximum into a monotone rise --
the prominence clamps to zero and nothing was removed from a ring. The
additive model total = floor + merge excess is falsified by its own
-573.8% row, because --pyramid-bands is not a selection knob: it moves
the pyramid base from 1/128 to 1/32 scale and re-renders the background's
low frequencies by construction.

armprofile.py (commissioned 5/5, 6.9x plant separation; its first run
correctly FAILED a badly built plant) measures the width of each arm's
DIFFERENCE profile and separates a ring removal from a background tilt.
Result: tweezers-cpl is the only subject of twelve where bands5 removes a
ring locally (-984 DN at 36 px, FWHM 31.7 px, collapsing to -15 DN one
annulus out). dry-erase (152.7 px), bee-1-cpl (107.6 px) and coffee-bean
(92.8 px) are broad tilts.

NOT RECOMMENDING a default change. Raw corpus median -5.5%; coffee-bean
gets 8.8% worse; and on ORCH's named acceptance subject bee-1-cpl it
lifts black level +1412.3 DN, costs -2.87% sharpness and darkens the near
background -1613.5 DN over a 107 px band.

Two hypotheses killed by clean nulls: the convex hull (STREHL_HULL, added
here, default-off and byte-identical when unset, commissioned 5/5 --
~38 DN of a 1260 DN aura) and alignment drift.

Exposure confound ruled out by measurement, not assumption: all 26
faithful masters and 139 masters overall clip <=0.135%. This lane is in
ORCH's case 3, rendered without --auto-exposure.

Instruments: aura.py 8/8, annulus.py 5/5, armprofile.py 5/5, abscore.py
4/4, sharp.py 3/3, tweezers.py 2/2, hullcommission.ps1 5/5.

Binary 7252AF9C19A5BFE2 (strehl 0.0.0, cc98561582ab-dirty); both arms of
every A/B rendered by that one binary so no flag is confounded with
commit drift. Full write-up in docs/research/V-SPEED-HALO.md.
'@

$msgFile = Join-Path $env:TEMP 'vspeed-halo-msg.txt'
Set-Content -Path $msgFile -Value $msg -Encoding UTF8

$r = Invoke-GitRetry -GitArgs (@('commit', '-q', '-F', $msgFile, '--') + $paths)
Write-Host "  commit rc=$($r.rc)"
Write-Host $r.out
if ($r.rc -ne 0) { exit 1 }

git --no-pager log -1 --stat --format='%h %s'
