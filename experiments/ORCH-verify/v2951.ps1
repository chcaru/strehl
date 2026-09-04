# Forward verifier for STATUS section 2.9.51.
#
# DESIGN NOTE, earned the hard way in v2950. A verifier that checks only that a
# document agrees with itself will certify fiction. The failure there was a check
# named "the inversion arithmetic is true" which confirmed 2.8/1.4 = 2.0 -- a true
# statement about numbers that were lens labels rather than measurements. So every
# numeric claim below is checked TWICE: once that STATUS states it, and once that
# the lane report STATUS is quoting actually contains it.
#
# Also checks structure. The 2.9.50 insertion silently deleted the "## 3. Gaps"
# top-level header and orphaned ~190 lines; it was caught only by a bounds check
# written for an unrelated reason. Those bounds checks are now permanent.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function ReadDoc([string]$rel) {
  $p = Join-Path $root $rel
  if (-not (Test-Path $p)) { throw "MISSING INPUT: $rel" }
  return (Get-Content $p -Raw)
}

# Collapse whitespace so a quotation that wraps in the source still matches.
function Flat([string]$s) { return ($s -replace '\s+', ' ') }

$st   = ReadDoc 'docs\STATUS.md'
$m159 = ReadDoc 'docs\research\M159-noise-clause.md'
$m160 = ReadDoc 'docs\research\M160-scope-audit.md'
$m135 = ReadDoc 'docs\research\M135-detail-instrument.md'
$m136 = ReadDoc 'docs\research\M136-m8o-bar.md'
$sc   = ReadDoc 'docs\proposals\2026-09-sota-scorecard.md'

$stF   = Flat $st
$m159F = Flat $m159
$m160F = Flat $m160

$script:pass = 0
$script:fail = 0
function Check([string]$name, [bool]$cond) {
  if ($cond) { $script:pass++; Write-Output "PASS  $name" }
  else       { $script:fail++; Write-Output "FAIL  $name" }
}

# ---------------------------------------------------------------- structure

$startIdx = $st.IndexOf('### 2.9.51 The noise axis is not merely unproven')
Check 'section 2.9.51 exists' ($startIdx -ge 0)

$gapsIdx = $st.IndexOf('## 3. Gaps, ranked by what stands between here and print-worthy')
Check 'the Gaps top-level header still exists' ($gapsIdx -ge 0)
Check 'Gaps header survives AFTER 2.9.51 (not swallowed)' ($gapsIdx -gt $startIdx)
Check 'section 3.1 Blocking still exists'        ($st.Contains('### 3.1 Blocking'))
Check 'section 3.2 still exists'                 ($st.Contains('### 3.2 Important, not blocking'))
Check 'section 3.3 still exists'                 ($st.Contains('### 3.3 Open against the brief'))
Check 'section 4 still exists'                   ($st.Contains('## 4. What the owner still owes'))
Check 'section 5 still exists'                   ($st.Contains('## 5. Landmines for whoever picks this up'))
Check 'preceding section 2.9.50 still exists'    ($st.Contains('### 2.9.50 The document blocking publication was mine'))
Check '2.9.50.7 Position still exists'           ($st.Contains('#### 2.9.50.7 Position'))

$body = if ($startIdx -ge 0 -and $gapsIdx -gt $startIdx) {
  $st.Substring($startIdx, $gapsIdx - $startIdx)
} else {
  # Degrade to FAIL, never crash. A verifier that throws on a malformed document
  # reports nothing about WHICH check failed, so a negative control cannot prove
  # its named check fired -- and an exception mid-run aborts the caller's restore.
  ''
}
$bodyF = Flat $body

foreach ($n in 1..6) {
  Check "subsection 2.9.51.$n present" ($body.Contains("#### 2.9.51.$n "))
}
Check 'section 2.9.51 terminates before Gaps' ($body.Length -gt 1000 -and $body.Length -lt 20000)

# ------------------------------------------------- M2 numbers, both directions

Check 'STATUS states median 1.515208x'   ($bodyF.Contains('carries `1.515208x` the fork'))
Check 'M159 SOURCE contains 1.515208'    ($m159F.Contains('1.515208'))

Check 'STATUS states minimum 1.335062'   ($bodyF.Contains('1.335062'))
Check 'M159 SOURCE contains 1.335062'    ($m159F.Contains('minimum `1.335062`'))

Check 'STATUS states p25 1.483011'       ($bodyF.Contains('1.483011'))
Check 'M159 SOURCE contains 1.483011'    ($m159F.Contains('p25 `1.483011`'))

Check 'STATUS states zero of twelve win' ($bodyF.Contains('zero of twelve sites below one'))
Check 'M159 SOURCE says 0/12 below one'  ($m159F.Contains('0/12` below one'))

Check 'STATUS states blur reward at its canonical site' ($bodyF.Contains('drove that statistic to `0.571215x`'))
Check 'STATUS table repeats blur reward consistently'   ($bodyF.Contains('under blur, `0.571215x`'))
# The count assertion is the actual guard. This figure appears TWICE in the section
# (prose plus the pattern table), so a bare Contains() is satisfied by whichever copy
# was not corrupted -- the duplicate-presence failure that has now bitten this program
# three times. Pin each site AND assert the population.
Check 'blur figure occurs exactly twice, both intact'   (([regex]::Matches($bodyF, '0\.571215x')).Count -eq 2)
Check 'M159 SOURCE contains 0.571215'       ($m159F.Contains('0.571215'))
Check 'M159 SOURCE ties it to lost detail'  ($m159F.Contains('the statistic strongly rewards lost detail'))

Check 'STATUS states SHIP-V2 0.224x'        ($bodyF.Contains('0.224x'))
Check 'M159 SOURCE contains 0.224'          ($m159F.Contains('0.224'))
Check 'M159 SOURCE says numerator absent'   ($m159F.Contains('the SHIP-V2 numerator TIFF is absent'))

# Direction of the metric. Residual is a badness; if STATUS ever implies otherwise
# the adverse result silently becomes a win.
Check 'STATUS states residual direction explicitly' ($bodyF.Contains('Residual is a badness, so higher is worse'))
Check 'STATUS does not call the M2 result a win'    (-not ($bodyF -match 'M2 (?:now |currently )?(?:wins|passes|clears)'))

# --------------------------------------------------------- the clause itself

Check 'STATUS quotes the owner clause'   ($bodyF.Contains('at strictly lower noise'))
Check 'M159 SOURCE ruled it unclaimable' ($m159F.Contains('CANNOT BE CLAIMED TODAY'))
Check 'STATUS says cannot be claimed today' ($bodyF.Contains('cannot be claimed today'))

# --------------------------------------------------- three-instrument pattern

Check 'STATUS names M135 exact invariance' ($bodyF.Contains('exactly* invariant to a common nonzero scalar transfer'))
Check 'M135 SOURCE has the impossibility'  ((Flat $m135).Contains('The precise impossibility result'))

Check 'STATUS states M8-R FAIL 1.030569%'  ($bodyF.Contains('1.030569%'))
Check 'SCORECARD SOURCE still FAILs M8-R'  ((Flat $sc).Contains('**FAIL** - M8-R `1.030569%`') -or (Flat $sc).Contains('**FAIL** ' + [char]0x2014 + ' M8-R `1.030569%`'))
Check 'M136 SOURCE has the u16 domain bar' ((Flat $m136).Contains('65535'))

Check 'STATUS states the common cause'     ($bodyF.Contains('no external reference, and blur is a legal move'))
Check 'STATUS distinguishes noise/signal'  ($bodyF.Contains('removed noise* from *removed signal'))

# --------------------------------------------------------- one capture, two axes

Check 'STATUS states T_TR is M2 bound'     ($bodyF.Contains('T_TR'))
Check 'M135 SOURCE defines T_TR'           ((Flat $m135).Contains('T_TR'))
Check 'M159 SOURCE asks for transfer bound' ($m159F.Contains('transfer bound'))
Check 'STATUS states the $0 cost'          ($bodyF.Contains('`$0` capture session'))
Check 'STATUS claims two axes not one'     ($bodyF.Contains('unblocks both'))

# ------------------------------------------------------------ M160 audit facts

Check 'STATUS states A B C confirmed'      ($bodyF.Contains('Claims A, B and C'))
Check 'M160 SOURCE confirms A'             ($m160F.Contains('A - seven axes, five unnamed | **CONFIRMED**') -or $m160F.Contains('CLAIM A CONFIRMED'))
Check 'M160 SOURCE confirms C'             ($m160F.Contains('CLAIM C CONFIRMED'))
Check 'STATUS states D refuted'            ($bodyF.Contains('Claim D refuted'))
Check 'M160 SOURCE refutes D'              ($m160F.Contains('CLAIM D REFUTED'))

Check 'STATUS states fourteen contradictions' ($bodyF.Contains('fourteen operative contradictions'))
Check 'M160 SOURCE counts 14 failures'        ($m160F.Contains('passed=22 failed=14'))

Check 'STATUS quotes the governing rule'   ($bodyF.Contains('Every primary metric is a hard gate'))
Check 'M160 SOURCE quotes that rule'       ($m160F.Contains('Every primary metric is a hard gate'))
Check 'STATUS owns the miss in one line'   ($bodyF.Contains('I amended the section that'))

# -------------------------------------------------- joint-card binding (F4)

Check 'STATUS states M4 bound to M1/M2/M8' ($bodyF.Contains('bind M4 to M1/M2/M8'))
Check 'STATUS states M12 bound to M11'     ($bodyF.Contains('M12 to M11'))
Check 'M160 SOURCE has the M4 joint card'  ($m160F.Contains('M1 information + M2 noise + M4 flat power + M8 hull'))
Check 'M160 SOURCE has the M12 joint card' ($m160F.Contains('M11 runtime + M12 determinism'))

# The resolution must RETAIN the guards, not drop them. This is the check that
# would catch me quietly weakening the standard while calling it a scope fix.
Check 'STATUS retains anti-cheat components' ($bodyF.Contains('anti-cheat components only'))
Check 'STATUS names the flat-power tell'     ($bodyF.Contains('flat-power tell'))
Check 'STATUS names the worker-ladder tell'  ($bodyF.Contains('worker-ladder byte-identity'))
Check 'STATUS justifies retention by owner sentence' ($bodyF.Contains("guard the owner's own sentence"))

# --------------------------------------------------------------- honesty rails

Check 'STATUS still reports zero axes scored' ($bodyF.Contains('zero of seven gating axes scored'))
Check 'STATUS does not claim SOTA'            (-not ($bodyF -match 'state of the art (?:is |has been )?(?:reached|achieved)'))
Check 'STATUS credits M159 against interest'  ($bodyF.Contains('against its own lane'))

# ------------------------------------------------------------------- verdict

Write-Output ''
Write-Output "RESULT: $script:pass passed, $script:fail failed"
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
