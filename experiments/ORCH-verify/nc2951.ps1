# Negative controls for v2951.ps1.
#
# v2951 passed 69/69 on its first run. That is exactly the condition under which a
# checker is most likely to be inert, so nothing in it is trusted until each check
# has been made to fire by planting the precise defect it targets.
#
# THREE RULES, each learned from a control that was wrongly GREEN earlier in this
# program:
#   1. Every mutation anchor is a single line. Anchors that span a line break do not
#      match, and a silent miss reads as a pass. A miss here is a HARD ERROR.
#   2. Each negative control asserts its OWN NAMED check failed, not merely that the
#      run went red. Otherwise a checker that fails on everything scores full marks.
#   3. Benign controls must stay GREEN, which is what detects that fail-on-everything.
#
# NC11 is the load-bearing one. It corrupts a LANE REPORT rather than STATUS, to
# prove the input-side half of the two-sided design is live. Without it, v2951 could
# be verifying only that STATUS agrees with itself -- the exact defect that let
# "2.8/1.4 = 2.0" pass verification while both inputs were fiction.
#
# Files are restored from copies taken in $env:TEMP. Never `git checkout -- <path>`,
# which reverts to HEAD and has destroyed uncommitted work on this machine before.

$ErrorActionPreference = 'Stop'
$root    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$statusP = Join-Path $root 'docs\STATUS.md'
$m159P   = Join-Path $root 'docs\research\M159-noise-clause.md'
$verify  = Join-Path $PSScriptRoot 'v2951.ps1'

$bakS = Join-Path $env:TEMP 'nc2951_status.bak'
$bakM = Join-Path $env:TEMP 'nc2951_m159.bak'
Copy-Item $statusP $bakS -Force
Copy-Item $m159P   $bakM -Force

function Restore {
  Copy-Item $bakS $statusP -Force
  Copy-Item $bakM $m159P   -Force
}

$controls = @(
  @{ id='NC1';  desc='corrupt the median residual ratio';            file='S'; from='with minimum `1.335062`, p25 `1.483011`, and **zero of twelve sites below one**. Residual'; to='with minimum `1.335062`, p25 `1.483012`, and **zero of twelve sites below one**. Residual'; expect='STATUS states p25 1.483011'; benign=$false },
  @{ id='NC2';  desc='delete the Gaps top-level header';             file='S'; from='## 3. Gaps, ranked by what stands between here and print-worthy'; to='(section removed)'; expect='the Gaps top-level header still exists'; benign=$false },
  @{ id='NC3';  desc='flip the residual direction statement';        file='S'; from='is a badness, so higher is worse: there is no site at which the current build wins. This'; to='is a goodness, so higher is better: there is no site at which the current build loses. This'; expect='STATUS states residual direction explicitly'; benign=$false },
  @{ id='NC4';  desc='silently drop the anti-cheat retention';       file='S'; from='disclosures; and M4 and M12 retain their *anti-cheat components only* — the flat-power tell'; to='disclosures; and M4 and M12 are dropped entirely — the flat-power tell'; expect='STATUS retains anti-cheat components'; benign=$false },
  @{ id='NC5';  desc='undercount the contradictions found';          file='S'; from='threshold or `FAIL` moved. Claim D refuted, with fourteen operative contradictions. The'; to='threshold or `FAIL` moved. Claim D refuted, with three operative contradictions. The'; expect='STATUS states fourteen contradictions'; benign=$false },
  @{ id='NC6';  desc='hide that no axis is scored';                  file='S'; from='Still zero of seven gating axes scored. What changed is that the noise axis is no longer'; to='Progress is strong across the board. What changed is that the noise axis is no longer'; expect='STATUS still reports zero axes scored'; benign=$false },
  @{ id='NC7';  desc='corrupt ONE of two copies of a figure';        file='S'; from='drove that statistic to `0.571215x`: blurring a noisy field that contained real six-pixel'; to='drove that statistic to `0.581215x`: blurring a noisy field that contained real six-pixel'; expect='STATUS states blur reward at its canonical site'; benign=$false },
  @{ id='NC7b'; desc='corrupt the OTHER copy (the table row)';        file='S'; from='| M2 noise | flat-ROI residual *improves* under blur, `0.571215x` | M159 |'; to='| M2 noise | flat-ROI residual *improves* under blur, `0.591215x` | M159 |'; expect='STATUS table repeats blur reward consistently'; benign=$false },
  @{ id='NC8';  desc='delete a subsection header';                   file='S'; from='#### 2.9.51.4 Which makes one capture worth at least two axes'; to='(subsection removed)'; expect='subsection 2.9.51.4 present'; benign=$false },
  @{ id='NC9';  desc='claim the losing axis passes';                 file='S'; from='merely unscored: its single measurement is adverse at every site, and its licensed'; to='merely unscored: M2 now passes at every site, and its licensed'; expect='STATUS does not call the M2 result a win'; benign=$false },
  @{ id='NC10'; desc='erase the standing M8 failure';                file='S'; from='| M8 invented structure | bar unsatisfiable in the mandated `u16/65535` domain; M8-R still `FAIL` at `1.030569%` | M136 |'; to='| M8 invented structure | bar unsatisfiable in the mandated `u16/65535` domain; M8-R now `PASS` at `0.030569%` | M136 |'; expect='STATUS states M8-R FAIL 1.030569%'; benign=$false },
  @{ id='NC11'; desc='CORRUPT THE SOURCE REPORT, not STATUS';        file='M'; from='Distribution: minimum `1.335062`, p25 `1.483011`, median **`1.515208×`**,'; to='Distribution: minimum `9.999999`, p25 `1.483011`, median **`1.515208×`**,'; expect='M159 SOURCE contains 1.335062'; benign=$false },
  @{ id='NC12'; desc='strip the against-interest attribution';       file='S'; from='M159 corrected its own prior report, against its own lane''s interest. The owner''s'; to='M159 corrected its own prior report. The owner''s'; expect='STATUS credits M159 against interest'; benign=$false },
  @{ id='BENIGN-A'; desc='reword prose carrying no checked claim';   file='S'; from='Three rulers have been proven wrong before anything was measured with them. That is cheap.'; to='Three rulers were shown wrong before any number was taken from them. That is inexpensive.'; expect=''; benign=$true },
  @{ id='BENIGN-B'; desc='insert a heading-adjacent blank line';     file='S'; from='#### 2.9.51.6 Position'; to="#### 2.9.51.6 Position`r`n"; expect=''; benign=$true }
)

$correct = 0; $wrong = 0; $neg = 0; $ben = 0
$results = @()

# PRE-FLIGHT. Validate every anchor before mutating anything, so all misses are
# reported in one run. Discovering them one per run costs a full pass each time,
# and worse, it leaves earlier controls unverified while the harness aborts.
# Anchor misses here are usually character-level: an em dash typed as a hyphen, or
# a multiplication sign typed as the letter x.
$anchorFail = @()
foreach ($c in $controls) {
  $probe = if ($c.file -eq 'S') { Get-Content $statusP -Raw } else { Get-Content $m159P -Raw }
  $n = ([regex]::Matches($probe, [regex]::Escape($c.from))).Count
  if ($n -ne 1) { $anchorFail += ('{0}: {1} occurrences ({2})' -f $c.id, $n, $c.file) }
}
if ($anchorFail.Count -gt 0) {
  Write-Output 'PRE-FLIGHT FAILED. These anchors do not resolve to exactly one occurrence:'
  $anchorFail | ForEach-Object { Write-Output "  $_" }
  Write-Output ''
  Write-Output 'No mutation was applied. Controls are invalid until every anchor lands.'
  exit 2
}
Write-Output ("PRE-FLIGHT: all {0} anchors resolve uniquely." -f $controls.Count)
Write-Output ''

try {
foreach ($c in $controls) {
  Restore
  $path = if ($c.file -eq 'S') { $statusP } else { $m159P }
  $txt  = Get-Content $path -Raw

  # HARD ERROR on a miss. A mutation that does not land produces a green run that
  # looks identical to a control the checker correctly survived.
  $occ = ([regex]::Matches($txt, [regex]::Escape($c.from))).Count
  if ($occ -ne 1) {
    Restore
    throw "MUTATION TARGET NOT FOUND OR AMBIGUOUS for $($c.id): $occ occurrences of the anchor. Controls are invalid until this is fixed."
  }

  Set-Content $path -Value ($txt.Replace($c.from, $c.to)) -Encoding UTF8 -NoNewline

  $out = & $verify 2>&1 | Out-String
  $rc  = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 1 }

  if ($c.benign) {
    $ben++
    $ok = ($rc -eq 0)
    $note = if ($ok) { 'GREEN  (correct)' } else { 'RED    (WRONG - benign edit broke a check)' }
  } else {
    $neg++
    $named = $out -match ('FAIL\s+' + [regex]::Escape($c.expect))
    $ok = ($rc -ne 0) -and $named
    $note = if ($ok) { 'RED    (correct, named check fired)' }
            elseif ($rc -ne 0) { "RED    (WRONG - red, but '$($c.expect)' did not fire)" }
            else { 'GREEN  (WRONG - defect not detected)' }
  }

  if ($ok) { $correct++ } else { $wrong++ }
  $results += ('{0,-9} {1,-46} rc={2}  -> {3}' -f $c.id, $c.desc, $rc, $note)
}
}
finally {
  # ALWAYS restore. The first version of this harness let an exception inside the
  # verifier escape, which skipped the restore and left STATUS.md with a deleted
  # top-level header on disk. `git checkout --` would have "fixed" that by also
  # destroying the entire uncommitted section this run was written to verify.
  Restore
}

$results | ForEach-Object { Write-Output $_ }
Write-Output ''
Write-Output ("CONTROLS: {0}/{1} correct  (negative={2}, benign={3}, wrong={4})" -f $correct, $controls.Count, $neg, $ben, $wrong)

# Prove the restore worked, so a later run is not measuring a file this script damaged.
$final = & $verify 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { Write-Output ''; Write-Output 'ERROR: verifier is RED after restore; files may be damaged.'; exit 2 }
Write-Output 'POST-RESTORE: verifier GREEN, files intact.'
if ($wrong -gt 0) { exit 1 } else { exit 0 }
