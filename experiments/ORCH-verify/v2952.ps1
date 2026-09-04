# Forward verifier for STATUS section 2.9.52.
#
# Same two-sided design as v2951: every claim is checked once against STATUS and
# once against the lane report STATUS is quoting. A verifier that only proves a
# document agrees with itself certifies fiction.
#
# Section boundaries are computed from the NEXT header rather than from a distant
# landmark, because delimiting on "## 3. Gaps" swallowed a neighbouring section
# into the body when one was appended, which silently broke occurrence counts.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function ReadDoc([string]$rel) {
  $p = Join-Path $root $rel
  if (-not (Test-Path $p)) { throw "MISSING INPUT: $rel" }
  return (Get-Content $p -Raw)
}
function Flat([string]$s) { return ($s -replace '\s+', ' ') }

$st   = ReadDoc 'docs\STATUS.md'
$m161 = ReadDoc 'docs\research\M161-bar-feasibility.md'
$m159 = ReadDoc 'docs\research\M159-noise-clause.md'
$m135 = ReadDoc 'docs\research\M135-detail-instrument.md'
$sc   = ReadDoc 'docs\proposals\2026-09-sota-scorecard.md'

$m161F = Flat $m161
$m159F = Flat $m159

$script:pass = 0
$script:fail = 0
function Check([string]$name, [bool]$cond) {
  if ($cond) { $script:pass++; Write-Output "PASS  $name" }
  else       { $script:fail++; Write-Output "FAIL  $name" }
}

# ---------------------------------------------------------------- structure

$startIdx = $st.IndexOf('### 2.9.52 No bar is impossible')
Check 'section 2.9.52 exists' ($startIdx -ge 0)

$gapsIdx = $st.IndexOf('## 3. Gaps, ranked by what stands between here and print-worthy')
Check 'the Gaps top-level header still exists' ($gapsIdx -ge 0)
Check 'Gaps header survives AFTER 2.9.52'      ($gapsIdx -gt $startIdx)
Check 'prior section 2.9.51 still intact'      ($st.Contains('### 2.9.51 The noise axis is not merely unproven'))
Check 'prior section 2.9.50 still intact'      ($st.Contains('### 2.9.50 The document blocking publication was mine'))
Check 'section 3.1 still exists'               ($st.Contains('### 3.1 Blocking'))
Check 'section 3.2 still exists'               ($st.Contains('### 3.2 Important, not blocking'))
Check 'section 3.3 still exists'               ($st.Contains('### 3.3 Open against the brief'))
Check 'section 4 still exists'                 ($st.Contains('## 4. What the owner still owes'))
Check 'section 5 still exists'                 ($st.Contains('## 5. Landmines for whoever picks this up'))

$body = if ($startIdx -ge 0 -and $gapsIdx -gt $startIdx) {
  $st.Substring($startIdx, $gapsIdx - $startIdx)
} else { '' }
$bodyF = Flat $body

foreach ($n in 1..7) { Check "subsection 2.9.52.$n present" ($body.Contains("#### 2.9.52.$n ")) }
Check 'section 2.9.52 is bounded' ($body.Length -gt 1000 -and $body.Length -lt 20000)

# ------------------------------------------------- the headline, both directions

Check 'STATUS says no bar is impossible'   ($bodyF.Contains('No bar is impossible'))
Check 'M161 SOURCE says no new impossible' ($m161F.Contains('no new impossible bar'))
Check 'STATUS says three paths void'       ($bodyF.Contains('Three named licensing paths are void'))
Check 'M161 SOURCE says three paths void'  ($m161F.Contains('three named licensing paths are void'))

# ----------------------------------------------- per-axis verdicts, both sides
# Each axis verdict is pinned to its own row in the source table. The em dash is
# matched as '.' so a dash-character mismatch cannot silently fail the anchor.

Check 'M161 SOURCE rules M2 void'   ($m161F -match 'M2 . noise \| \*\*INSTRUMENT VOID\*\*')
Check 'M161 SOURCE rules M3 sound'  ($m161F -match 'M3 . occlusion halo / veil \| \*\*SOUND BUT UNMEASURED\*\*')
Check 'M161 SOURCE rules M9 void'   ($m161F -match 'M9 . certified acuity / `n_eff` \| \*\*INSTRUMENT VOID\*\*')
Check 'M161 SOURCE rules M10 void'  ($m161F -match 'M10 . physical depth \| \*\*INSTRUMENT VOID\*\*')
Check 'M161 SOURCE rules M11 sound' ($m161F -match 'M11 . speed \| \*\*SOUND BUT UNMEASURED\*\*')

Check 'STATUS table marks M1 void'   ($bodyF -match '\| M1 detail \| INSTRUMENT VOID')
Check 'STATUS table marks M2 void'   ($bodyF -match '\| M2 noise \| INSTRUMENT VOID')
Check 'STATUS table marks M3 sound'  ($bodyF -match '\| M3 occlusion veil \| \*\*SOUND BUT UNMEASURED\*\*')
Check 'STATUS table marks M8 bar'    ($bodyF -match '\| M8 invented structure \| BAR UNSATISFIABLE AS WRITTEN')
Check 'STATUS table marks M9 void'   ($bodyF -match '\| M9 certified acuity \| INSTRUMENT VOID')
Check 'STATUS table marks M10 void'  ($bodyF -match '\| M10 physical depth \| INSTRUMENT VOID')
Check 'STATUS table marks M11 sound' ($bodyF -match '\| M11 speed \| \*\*SOUND BUT UNMEASURED\*\*')

# Population assertions. If a row is added, removed, or a verdict is flipped, the
# counts move even when every individual presence check still finds a match.
Check 'exactly four INSTRUMENT VOID rows' (([regex]::Matches($bodyF, 'INSTRUMENT VOID')).Count -eq 4)
Check 'exactly two SOUND BUT UNMEASURED rows' (([regex]::Matches($bodyF, 'SOUND BUT UNMEASURED')).Count -eq 2)

# --------------------------------------------------- bars must not be lowered

Check 'STATUS states repairs do not lower bars' ($bodyF.Contains('do not lower their bars'))
Check 'M161 SOURCE says so at least 3 times'    (([regex]::Matches($m161F, 'does not lower the bar')).Count -ge 3)
Check 'STATUS keeps M8-R FAIL 1.030569%'        ($bodyF.Contains('`FAIL` at `1.030569%`'))
Check 'SCORECARD SOURCE still FAILs M8-R'       ((Flat $sc).Contains('M8-R `1.030569%`'))

# ------------------------------------------------------- the M9 = M1 mechanism

Check 'STATUS states the M9 invariance'      ($bodyF.Contains('exactly invariant to a common nonzero post-noise transfer'))
Check 'M161 SOURCE states that invariance'   ($m161F.Contains('exactly invariant to a common nonzero post-noise transfer'))
Check 'STATUS says blur and USM invisible'   ($bodyF.Contains('blur and unsharp mask are'))
Check 'M161 SOURCE says both invisible'      ($m161F.Contains('Blur and unsharp mask are therefore both invisible'))
Check 'STATUS names the shared cause'        ($bodyF.Contains('no external reference, and against such a judge blur is a'))
Check 'M135 SOURCE has the impossibility'    ((Flat $m135).Contains('The precise impossibility result'))
Check 'STATUS claims three axes unblocked'   ($bodyF.Contains('unblocks three gating axes, not one'))

# --------------------------------------------------------- the M10 null test

Check 'STATUS states the M10 null'      ($bodyF.Contains('zero, then with infinity'))
Check 'M161 SOURCE states the M10 null' ($m161F.Contains('Replacing every reported uncertainty by zero, infinity, or random values leaves every M10 pass/fail quantity unchanged'))
Check 'STATUS says input unread'        ($bodyF.Contains('does not read one of its own mandatory inputs'))

# ------------------------------------------- the correction that favours strehl

Check 'STATUS records the second comparator' ($bodyF.Contains('`1.377766x`'))
Check 'M159 SOURCE has 1.377766'             ($m159F.Contains('1.377766'))
Check 'STATUS records 0/11 below one'        ($bodyF.Contains('zero of eleven sites below one'))
Check 'M159 SOURCE says 0/11 below one'      ($m159F -match '0/11`?\*{0,2} below one')
Check 'STATUS records recovered-structure caveat' ($bodyF.Contains('may be recovered paper structure'))
Check 'M159 SOURCE states that caveat'       ($m159F.Contains('may be recovered paper structure'))
Check 'STATUS states the symmetric ignorance' ($bodyF.Contains('also stops it learning whether it is worse'))
Check 'STATUS keeps 1.515208x uninterpreted'  ($bodyF.Contains('uninterpretable until'))
Check 'M159 SOURCE contains 1.515208'         ($m159F.Contains('1.515208'))
# The self-criticism must remain, and must remain in the direction actually made.
Check 'STATUS owns error direction'           ($bodyF.Contains('made the project look worse than'))

# ------------------------------------------------------------ resequencing

Check 'STATUS attributes 23 attempts to M139' ($bodyF -match 'M139 held an exclusive host lock.*23 consecutive attempts')
Check 'STATUS states M12 is not gating'       ($bodyF.Contains('M12 is not one of the'))
Check 'STATUS names the orchestration gap'    ($bodyF.Contains('none was pointed at the artefact'))
Check 'STATUS names M162 as the artefact lane' ($bodyF.Contains('M162 is the'))

# --------------------------------------------------------------- honesty rails

Check 'STATUS still reports zero scored'  ($bodyF.Contains('Zero of seven gating axes scored'))
Check 'STATUS does not claim SOTA'        (-not ($bodyF -match 'state of the art (?:is |has been )?(?:reached|achieved)'))
Check 'STATUS does not claim an axis passed' (-not ($bodyF -match '(?:first|one) axis (?:is now |now )?scored'))

Write-Output ''
Write-Output "RESULT: $script:pass passed, $script:fail failed"
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
