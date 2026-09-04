param()

# Negative controls for v2953.ps1.
#
# Each control plants one defect into a COPY in $env:TEMP and requires the
# verifier to fail the SPECIFIC named check that defect targets. Merely going
# RED is not enough: a checker that fails for an unrelated reason looks
# identical from the outside.
#
# v2953 takes every input path as a parameter, so controls mutate copies and the
# real files are never touched. That is deliberate. An earlier harness here
# mutated the real STATUS.md and restored afterwards; a verifier crash escaped
# the harness, skipped the restore, and left the document damaged on disk with
# a section header deleted. Parameterised inputs remove that failure mode
# entirely rather than papering over it with a finally block.
#
# Controls span FIVE files. The source-side ones matter most: without them the
# verifier would only prove STATUS agrees with itself, which is not the property
# being claimed.

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$paths = @{
  status = (Resolve-Path "$here\..\..\docs\STATUS.md").Path
  owner  = (Resolve-Path "$here\..\..\docs\OWNER-ACTIONS.md").Path
  m157   = (Resolve-Path "$here\..\..\docs\research\M157-comparator-viability.md").Path
  m161   = (Resolve-Path "$here\..\..\docs\research\M161-bar-feasibility.md").Path
  scard  = (Resolve-Path "$here\..\..\docs\proposals\2026-09-sota-scorecard.md").Path
  m3     = (Resolve-Path "$here\..\..\docs\research\M161-m3-ratification.md").Path
  ncown  = (Resolve-Path "$here\nc-owner0906.ps1").Path
}
$orig = @{}
foreach ($k in $paths.Keys) { $orig[$k] = Get-Content -LiteralPath $paths[$k] -Raw -Encoding UTF8 }

$controls = @(
  @{ n = 'NC1 disown the scheduling error'; f = 'status'
     a = '**The correction is mine and it is the point of this section.**'
     b = '**A note on sequencing.**'
     e = 'owns the error' },

  @{ n = 'NC2 turn the veto into a quality metric'; f = 'status'
     a = 'Its contract is admissibility, not quality:'
     b = 'Its contract is to score which output is better:'
     e = 'veto is an admissibility gate' },

  @{ n = 'NC3 drop sharpening from the fire list'; f = 'status'
     a = 'It must fire on planted blur, on planted sharpening, on resampling, and on'
     b = 'It must fire on planted blur, on resampling, and on'
     e = 'fires on sharpening' },

  @{ n = 'NC4 delete the fires-on-everything failure mode'; f = 'status'
     a = 'halves are required: a veto that fires on everything blocks the program permanently by'
     b = 'halves are nice to have, though in practice over-firing is harmless because it merely delays by'
     e = 'names the fires-on-everything failure' },

  @{ n = 'NC5 collapse M10 back to a single gap'; f = 'status'
     a = '**M10 is three gaps, not one, and I had written otherwise where the owner would read it.**'
     b = '**M10 has a single outstanding gap, and the owner page states it correctly.**'
     e = 'section says three gaps not one' },

  @{ n = 'NC6 claim the veto needs the capture after all'; f = 'status'
     a = 'other under a common filter. That needs no ground truth and no new capture, and it can be'
     b = 'other under a common filter. That needs the same fresh capture the reference does, and it can be'
     e = 'states the veto needs no capture' },

  @{ n = 'NC7 announce an axis has been scored'; f = 'status'
     a = 'gating axes have **passed**. That is not the same as zero scored: the scorecard records M8 as'
     b = 'gating axes have cleared, and the first gate passed tonight: the scorecard records M8 as'
     e = 'scoreboard still zero of seven' },

  @{ n = 'NC8 corrupt the 23-of-23 rejection count'; f = 'status'
     a = 'gate rejected 23 of 23 attempts, and a'
     b = 'gate rejected 18 of 23 attempts, and a'
     e = 'records 23 of 23 rejections' },

  @{ n = 'NC9 misstate the sub-agent count'; f = 'status'
     a = 'spawned **fifteen** distinct'
     b = 'spawned **six** distinct'
     e = 'section states fifteen sub-agents' },

  # This header has been accidentally deleted twice by section-boundary bugs.
  @{ n = 'NC10 delete the ## 3. Gaps header'; f = 'status'
     a = '## 3. Gaps, ranked by what stands between here and print-worthy'
     b = 'Gaps, ranked by what stands between here and print-worthy'
     e = '## 3. Gaps header survives' },

  @{ n = 'NC11 duplicate the section'; f = 'status'
     a = '## 4. What the owner still owes, and what it would unlock'
     b = "### 2.9.53 duplicate stub`r`n`r`n## 4. What the owner still owes, and what it would unlock"
     e = 'exactly one 2.9.53 header' },

  # ---- SOURCE-SIDE: the claims 2.9.53 makes about OTHER documents ----
  @{ n = 'NC12 [source] restore the whole-of-M10 overstatement'; f = 'owner'
     a = '*One of three things M10 needs — and the only one that needs you.*'
     b = '*This is the whole of M10.*'
     e = 'OWNER no longer contains it' },

  @{ n = 'NC13 [source] widen the M10 angle band in OWNER'; f = 'owner'
     a = '`[10.014357, 10.516727] deg` — about `±0.25 deg`. That sounds demanding and it'
     b = '`[10.014357, 10.916727] deg` — about `±0.45 deg`. That sounds demanding and it'
     e = 'OWNER still has that band' },

  @{ n = 'NC14 [source] remove the NC22 bar-relaxation control'; f = 'ncown'
     a = "  @{ n = 'NC22 widen the admissible angle band (moves the bar)'"
     b = "  @{ n = 'NC22 disabled'"
     e = 'NC22 really exists' },

  @{ n = 'NC15 [source] upgrade M157 NOT FOUND to verified'; f = 'm157'
     a = '**[NOT FOUND]** Neither statement is explicitly attached to'
     b = '**[VERIFIED]** The linear contract is explicitly attached to'
     e = 'M157 really rules NOT FOUND' },

  @{ n = 'NC16 [source] unblock the OWNER email condition'; f = 'owner'
     a = 'is cleared — *provided*'
     b = 'is cleared — *regardless of whether*'
     e = 'OWNER email is conditional on answer 3' },

  # ---- benign: must stay GREEN ----
  @{ n = 'NC17 [source] erase the M8 FAIL from the scorecard'; f = 'scard'
     a = '**FAIL** — M8-R `1.030569%`, M8-O `1.326144%` against a bar of exactly `0.0000%`'
     b = '**PASS** — M8-R `0.000000%`, M8-O `0.000000%` against a bar of exactly `0.0000%`'
     e = 'scorecard still FAILs M8' },

  @{ n = 'NC18 [source] delete the only-score-in-the-program phrase'; f = 'scard'
     a = 'This is the only axis in the program with a produced-and-read score.'
     b = 'Several axes now carry produced-and-read scores.'
     e = 'scorecard really says only-score' },

  @{ n = 'NC19 [source] change the ratified M3 bar in its own report'; f = 'm3'
     a = 'The literal publication gate is `max_e max(h_e,v_e) <= 0.05` over the frozen'
     b = 'The literal publication gate is `max_e max(h_e,v_e) <= 0.09` over the frozen'
     e = 'M3 report really states that bar' },

  @{ n = 'NC20 claim the M3 bar relaxed the scorecard'; f = 'status'
     a = 'It is worth being explicit that this **tightens** the'
     b = 'It is worth being explicit that this **relaxes** the'
     e = 'section says M3 TIGHTENS' },

  @{ n = 'NC21 collapse passed-vs-scored back to shorthand'; f = 'status'
     a = 'seven passed, exactly one scored, and the one that scored failed.**'
     b = 'seven gating axes scored.**'
     e = 'distinguishes passed from scored' },

  @{ n = 'NC22 delete the stack-vs-session correction'; f = 'status'
     a = 'inversion stack cannot alone unblock M1, M2 and M9; one coordinated session can capture'
     b = 'inversion stack unblocks M1, M2 and M9 on its own, and one sitting can capture'
     e = 'records the stack-vs-session fix' },

  @{ n = 'BENIGN-A reword prose carrying no checked claim'; f = 'status'
     a = 'filed behind a blocker that only covers half of it.'
     b = 'filed behind a blocker that covers only one of its two halves.'
     e = ''; benign = $true },

  @{ n = 'BENIGN-B insert a blank line before the next header'; f = 'status'
     a = '## 4. What the owner still owes, and what it would unlock'
     b = "`r`n## 4. What the owner still owes, and what it would unlock"
     e = ''; benign = $true }
)

$pass = 0; $wrong = 0
foreach ($c in $controls) {
  $k = $c.f
  $base = $orig[$k]
  $cnt = ([regex]::Matches($base, [regex]::Escape($c.a))).Count
  if ($cnt -ne 1) { throw "MUTATION TARGET NOT UNIQUE: $($c.n) -- anchor occurs $cnt time(s) in '$k': '$($c.a)'" }
  $mut = $base.Replace($c.a, $c.b)
  if ($mut -eq $base) { throw "MUTATION DID NOT ALTER THE FILE: $($c.n)" }

  $tmp = Join-Path $env:TEMP ("nc2953-" + ($c.n -replace '[^A-Za-z0-9]', '') + ".md")
  Set-Content -LiteralPath $tmp -Value $mut -Encoding UTF8 -NoNewline

  $args = @{ Status = $paths.status; Owner = $paths.owner; M157 = $paths.m157; M161 = $paths.m161; Scorecard = $paths.scard; M3 = $paths.m3; NcOwn = $paths.ncown }
  switch ($k) {
    'status' { $args.Status = $tmp }
    'owner'  { $args.Owner  = $tmp }
    'm157'   { $args.M157   = $tmp }
    'm161'   { $args.M161   = $tmp }
    'scard'  { $args.Scorecard = $tmp }
    'm3'     { $args.M3     = $tmp }
    'ncown'  { $args.NcOwn  = $tmp }
  }

  $out = & "$here\v2953.ps1" @args 2>&1 | Out-String
  $rc = $LASTEXITCODE

  $isBenign = $c.ContainsKey('benign') -and $c.benign
  if ($isBenign) {
    $ok = ($rc -eq 0)
    if ($ok) { $pass++ } else { $wrong++ }
    "{0,-58} rc={1}  -> {2}" -f $c.n, $rc, $(if ($ok) { 'GREEN  (correct)' } else { 'RED    ** WRONGLY RED **' })
  }
  else {
    $named = $out -match ("FAIL\s+" + [regex]::Escape($c.e))
    $ok = ($rc -ne 0) -and $named
    if ($ok) { $pass++ } else { $wrong++ }
    $why = if ($rc -eq 0) { '** WRONGLY GREEN **' } elseif (-not $named) { "** RED but not on '$($c.e)' **" } else { 'RED    (correct)' }
    "{0,-58} rc={1}  -> {2}" -f $c.n, $rc, $why
  }
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$neg = ($controls | Where-Object { -not ($_.ContainsKey('benign') -and $_.benign) }).Count
$ben = $controls.Count - $neg
Write-Output ''
Write-Output "CONTROLS: $pass/$($controls.Count) correct  (negative=$neg, benign=$ben, wrong=$wrong)"
if ($wrong -gt 0) { exit 1 } else { exit 0 }
