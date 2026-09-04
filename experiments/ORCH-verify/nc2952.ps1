# Negative controls for v2952.ps1.
#
# Same three rules as nc2951, each earned from a control that was wrongly GREEN:
#   1. Anchors are single lines and are PRE-FLIGHTED before any mutation, so every
#      miss is reported in one run rather than one per run. Misses here are usually
#      character-level: an em dash typed as a hyphen, a multiplication sign typed
#      as the letter x, or a backtick that is not in the source.
#   2. Each negative control asserts its OWN NAMED check failed, not merely that
#      the run went red, or a fail-on-everything checker scores full marks.
#   3. Benign controls must stay GREEN, which is what detects that case.
#
# Restores run in a `finally` block. An earlier version of this harness let an
# exception escape and skipped the restore, leaving STATUS.md damaged on disk.
# Recovery is from $env:TEMP, never `git checkout --`, which reverts to HEAD and
# would destroy the uncommitted section under verification.

$ErrorActionPreference = 'Stop'
$root    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$statusP = Join-Path $root 'docs\STATUS.md'
$m161P   = Join-Path $root 'docs\research\M161-bar-feasibility.md'
$verify  = Join-Path $PSScriptRoot 'v2952.ps1'

$bakS = Join-Path $env:TEMP 'nc2952_status.bak'
$bakM = Join-Path $env:TEMP 'nc2952_m161.bak'
Copy-Item $statusP $bakS -Force
Copy-Item $m161P   $bakM -Force
function Restore {
  Copy-Item $bakS $statusP -Force
  Copy-Item $bakM $m161P   -Force
}

$controls = @(
  @{ id='NC1';  desc='flip a void verdict to sound';                file='S'; from='| M9 certified acuity | INSTRUMENT VOID (M161) | external truth reference plus transfer veto |'; to='| M9 certified acuity | **SOUND BUT UNMEASURED** (M161) | external truth reference plus transfer veto |'; expect='STATUS table marks M9 void'; benign=$false },
  @{ id='NC2';  desc='delete the Gaps top-level header';            file='S'; from='## 3. Gaps, ranked by what stands between here and print-worthy'; to='(section removed)'; expect='the Gaps top-level header still exists'; benign=$false },
  @{ id='NC3';  desc='erase the standing M8 failure';               file='S'; from='| M8 invented structure | BAR UNSATISFIABLE AS WRITTEN (M136) | licensed repair; M8-R `FAIL` at `1.030569%` stands |'; to='| M8 invented structure | BAR REPAIRED (M136) | licensed repair; M8-R `PASS` at `0.030569%` stands |'; expect='STATUS keeps M8-R FAIL 1.030569%'; benign=$false },
  @{ id='NC4';  desc='claim the repairs lowered the bars';          file='S'; from='scored. M161 ruled explicitly that the M2, M9 and M10 repairs **do not lower their bars**,'; to='scored. M161 ruled explicitly that the M2, M9 and M10 repairs relax their bars slightly,'; expect='STATUS states repairs do not lower bars'; benign=$false },
  @{ id='NC5';  desc='hide that nothing is scored';                 file='S'; from='Zero of seven gating axes scored, unchanged. What changed is the shape of the remaining'; to='Two of seven gating axes are now scored. What changed is the shape of the remaining'; expect='STATUS still reports zero scored'; benign=$false },
  @{ id='NC6';  desc='overstate the capture payoff';                file='S'; from='capture unblocks three gating axes, not one.**'; to='capture unblocks all seven gating axes at once.**'; expect='STATUS claims three axes unblocked'; benign=$false },
  @{ id='NC7';  desc='delete the strehl-favourable correction';     file='S'; from='better also stops it learning whether it is worse.** A higher fractional box9 residual is'; to='better is the only problem here.** A higher fractional box9 residual is'; expect='STATUS states the symmetric ignorance'; benign=$false },
  @{ id='NC8';  desc='drop the recovered-structure caveat';         file='S'; from='M159 §4.1 states that some or all of the excess may be recovered paper structure, and §4.2'; to='M159 §4.1 states that the excess is stochastic sensor noise, and §4.2'; expect='STATUS records recovered-structure caveat'; benign=$false },
  @{ id='NC9';  desc='corrupt the second-comparator ratio';         file='S'; from='`1.377766x`, with zero of eleven sites below one. The sign is robust across comparators.'; to='`1.377767x`, with zero of eleven sites below one. The sign is robust across comparators.'; expect='STATUS records the second comparator'; benign=$false },
  @{ id='NC10'; desc='delete a subsection header';                  file='S'; from='#### 2.9.52.4 M10 fails differently, by the cleanest null test anyone here has run'; to='(subsection removed)'; expect='subsection 2.9.52.4 present'; benign=$false },
  @{ id='NC11'; desc='add a fifth void row (population check)';     file='S'; from='| M3 occlusion veil | **SOUND BUT UNMEASURED** (M161) | ratify the bar, recommission controls, run it |'; to='| M3 occlusion veil | INSTRUMENT VOID (M161) | ratify the bar, recommission controls, run it |'; expect='exactly four INSTRUMENT VOID rows'; benign=$false },
  @{ id='NC12'; desc='CORRUPT THE SOURCE REPORT, not STATUS';       file='M'; from='| M10 — physical depth | **INSTRUMENT VOID** |'; to='| M10 — physical depth | **SOUND BUT UNMEASURED** |'; expect='M161 SOURCE rules M10 void'; benign=$false },
  @{ id='NC13'; desc='strip the self-criticism direction';          file='S'; from='I record the direction of my own error deliberately: it made the project look worse than'; to='I note this in passing: it changed how the project reads compared with'; expect='STATUS owns error direction'; benign=$false },
  @{ id='NC14'; desc='hide the orchestration gap';                  file='S'; from='measurement; none was pointed at the artefact.** The owner asked for a state-of-the-art'; to='measurement, which was the correct allocation.** The owner asked for a state-of-the-art'; expect='STATUS names the orchestration gap'; benign=$false },
  @{ id='BENIGN-A'; desc='reword prose carrying no checked claim';  file='S'; from='rediscover this the same way.'; to='repeat the same discovery.'; expect=''; benign=$true },
  @{ id='BENIGN-B'; desc='insert a heading-adjacent blank line';    file='S'; from='#### 2.9.52.7 Position'; to="#### 2.9.52.7 Position`r`n"; expect=''; benign=$true }
)

$correct = 0; $wrong = 0; $neg = 0; $ben = 0
$results = @()

$anchorFail = @()
foreach ($c in $controls) {
  $probe = if ($c.file -eq 'S') { Get-Content $statusP -Raw } else { Get-Content $m161P -Raw }
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
  $path = if ($c.file -eq 'S') { $statusP } else { $m161P }
  $txt  = Get-Content $path -Raw
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
finally { Restore }

$results | ForEach-Object { Write-Output $_ }
Write-Output ''
Write-Output ("CONTROLS: {0}/{1} correct  (negative={2}, benign={3}, wrong={4})" -f $correct, $controls.Count, $neg, $ben, $wrong)

$final = & $verify 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { Write-Output ''; Write-Output 'ERROR: verifier RED after restore; files may be damaged.'; exit 2 }
Write-Output 'POST-RESTORE: verifier GREEN, files intact.'
if ($wrong -gt 0) { exit 1 } else { exit 0 }
