param([string]$Owner = "$PSScriptRoot\..\..\docs\OWNER-ACTIONS.md",
      [string]$M157 = "$PSScriptRoot\..\..\docs\research\M157-comparator-viability.md")

# Forward verifier for the 2026-09-06 OWNER-ACTIONS amendments:
#   * the seven-axis publication scope note and the Helicon correction
#   * the $0 inversion route, including the correction of MY OWN nominal-label error
#   * Ask 5, the calibration-slide reshoot owed after I burned the existing session
#
# Owner-facing text gets stricter treatment than internal notes: every number
# here is one the owner may act on, so each is checked against the lane report
# or the capture tree rather than against my own prose.

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$pass = 0; $fail = 0

function Flat([string]$p) {
  $lines = Get-Content -LiteralPath $p -Encoding UTF8 | ForEach-Object { $_ -replace '^\s*>\s?', '' }
  (($lines -join ' ') -replace '\s+', ' ')
}
function Check([string]$name, [bool]$ok, [string]$detail = '') {
  if ($ok) { $script:pass++; Write-Output ("  PASS  " + $name) }
  else { $script:fail++; Write-Output ("  FAIL  " + $name + $(if ($detail) { "  [$detail]" } else { '' })) }
}

$own = Flat $Owner
$plan = Flat "$root\docs\proposals\2026-08-sota-path.md"
$m135 = Flat "$root\docs\research\M135-detail-instrument.md"

Write-Output 'A. the seven-axis scope note is accurate against the PLAN'
Check 'plan sentence exists'            ($plan.Contains('The end-state sentence the project should be able to print'))
Check 'plan says Helicon if obtainable' ($plan.Contains('Helicon if obtainable'))
Check 'owner note states seven axes'    ($own -match 'it licenses \*\*seven\*\*: M1, M2, M3, M8, M9, M10, M11')
Check 'owner note names the five'       ($own -match 'no instrument for M4, M5, M6, M7 or M12')
Check 'owner note quotes Helicon clause' ($own.Contains('*"Helicon if obtainable"*'))
Check 'owner note owns the error as mine' ($own -match 'Both were my inventions, not your requirements')
# Same pinning problem: the Helicon quotation survives a mutation that reassigns
# blame for it to the owner's plan, so the attribution gets its own canonical check.
Check 'owner note attributes Helicon requirement to ME' ($own -match 'had made \*\*Helicon mandatory\*\* where your plan says')
Check 'owner note does not blame the plan' (-not ($own -match 'because your plan required it'))

# --- added 2026-09-06, M157 comparator viability -------------------------------
# The purchase gate and the technical gate are different gates. A licence clears
# only the first, and the scorecard's actual requirement -- native-size 16-bit
# LINEAR TIFF -- is [NOT FOUND] in Zerene's public documentation for the specific
# command we depend on. These checks exist so that distinction cannot quietly
# collapse back into "buy Zerene and (d) is cleared".
$m157 = Flat $M157
Check 'M157 brief is committed'                 ($m157.Length -gt 20000)
Check 'M157 records the provenance of the brief' ($m157 -match 'extracted from the lane transcript by the orchestrator')
Check 'M157 rules the linear contract NOT FOUND' ($m157 -match '\*\*\[NOT FOUND\]\*\* Neither statement is explicitly attached to')
Check 'M157 verifies it exports INPUT images'    ($m157 -match 'exporting adjusted \*\*input images\*\*')
Check 'M157 records both edition prices'         ($m157.Contains('Prosumer Edition, $189') -and $m157.Contains('Professional Edition, $289'))

Check 'owner note adds the technical question'   ($own -match 'The technical question, which the same email also settles')
Check 'owner note states purchase != gate closed' ($own -match 'clears the licence gate but\s+should not be recorded as closing the common-linear-input gate')
Check 'owner email asks all five sub-questions'  ($own -match 'native size' -and $own -match '\*\*16-bit\*\* TIFF' -and $own -match 'whether\s+the data is \*\*linear\*\*' -and $own -match 'ICC profile / colour space' -and $own -match 'batch or command-line')
Check 'owner note conditions the yes on answer 3' ($own -match 'provided\*\s+answer 3 confirms native-size 16-bit linear output')
Check 'owner note tells him to stop if 8-bit'    ($own -match 'tell me before buying')
# The email must remain FREE and remain ordered before the purchase.
Check 'Ask 1 still costs nothing'               ($own -match 'send one email\. \*\*\$0, five minutes')
Check 'Ask 1 still precedes any purchase'       ($own -match 'do it before any purchase')
# Currency of the page itself. This is owner-facing, and a stale "last updated"
# line invites him to act on a page he thinks is current when it is not.
Check 'page cites the current STATUS range'     ($own -match 'STATUS\.md` §2\.9\.28-2\.9\.52')
Check 'page names the lanes it now reflects'    ($own -match 'Last updated after lanes M157, M159, M160, M161')
# Two-sided by construction: read the upper bound OUT of the owner page, then
# require STATUS to actually contain that section. A hardcoded section number
# here would assert a fact about STATUS while proving nothing about the claim
# the owner page is making, and would survive the page citing anything at all.
$citedTo = if ($own -match 'STATUS\.md` §2\.9\.28-2\.9\.(\d+)') { $matches[1] } else { '' }
Check 'STATUS actually has the section cited'   (($citedTo -ne '') -and ((Flat "$root\docs\STATUS.md") -match ("### 2\.9\." + [regex]::Escape($citedTo) + "\b"))) "cited=2.9.$citedTo"
Check 'owner note cites the commit'     ($own.Contains('6b966d8c'))
Check 'owner note keeps the five publishable' ($own -match 'their results will still be published')

Write-Output ''
Write-Output 'B. the inversion numbers, checked against M135 and recomputed'
Check 'M135 warns off nominal labels'   ($m135.Contains('Do not use nominal lens labels as the ratio'))
Check 'M135 states measured 2.7015'     ($m135.Contains('2.7015'))
Check 'M135 states the 1.33x hard max'  ($m135.Contains('1.33'))
Check 'M135 states LCB95 >= 2.0 gate'   ($m135.Contains('LCB95(M_reference / M_scored) >= 2.0'))
Check 'M135 says no second optic needed' ($m135.Contains('A second macro optic is not required'))
# 2.7015 occurs three times in OWNER-ACTIONS (the new note plus two pre-existing
# capture-request lines), so a bare Contains() is satisfied by a duplicate and a
# corrupted value in the new note reads as fine. Each measured number gets ONE
# canonical site and the check is pinned to that site's sentence.
Check 'owner note states 2.7015 at its canonical site' ($own -match 'measured rig the conservative converter-on ratio is `2\.7015`')
Check 'owner note states 1.9296'        ($own.Contains('1.9296'))
Check 'owner note states 2.0312'        ($own.Contains('2.0312'))
Check 'owner note says below the bar'   ($own -match '\*\*below the bar, not at it\.\*\*')
Check 'owner note owns the label error' ($own -match 'One correction, and it is mine')
Check 'arithmetic: 2.7015/1.40 = 1.9296' ([Math]::Round(2.7015 / 1.40, 4) -eq 1.9296)
Check 'arithmetic: 2.7015/1.33 = 2.0312' ([Math]::Round(2.7015 / 1.33, 4) -eq 2.0312)
Check 'arithmetic: nominal state is really below 2.0' ((2.7015 / 1.40) -lt 2.0)
Check 'arithmetic: the rescued state really clears 2.0' ((2.7015 / 1.33) -gt 2.0)
Check 'owner note says no second optic required' ($own -match 'a second macro optic is not\s+required')
Check 'owner note says do not shoot yet' ($own -match '\*\*Do not shoot\s+yet\*\*')
Check 'owner note quotes the revised state' ($own.Contains('BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE'))
Check 'M135 carries that same state'    ($m135.Contains('BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE'))
Check 'owner note states the shared-prime limit' ($own -match 'not\s+absolute object truth')

Write-Output ''
Write-Output 'C. Ask 5 frame counts re-counted from the capture tree, not copied'
$hr = 'D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl'
if (Test-Path $hr) {
  $c = @{}
  foreach ($d in Get-ChildItem $hr -Directory) {
    $c[$d.Name] = (Get-ChildItem $d.FullName -File -Recurse -Include *.ARW, *.arw -ErrorAction SilentlyContinue).Count
  }
  Check 'disk: tilted-sw4-cpl = 182'  ($c['tilted-sw4-cpl'] -eq 182)  "got $($c['tilted-sw4-cpl'])"
  Check 'disk: tilted-sw10-cpl = 92'  ($c['tilted-sw10-cpl'] -eq 92)  "got $($c['tilted-sw10-cpl'])"
  Check 'disk: flat-sw4-cpl = 186'    ($c['flat-sw4-cpl'] -eq 186)    "got $($c['flat-sw4-cpl'])"
  Check 'disk: very-tilted = 197'     ($c['very-tilted-all-axis-sw10-cpl'] -eq 197) "got $($c['very-tilted-all-axis-sw10-cpl'])"
  $sum = ($c.Values | Measure-Object -Sum).Sum
  Check 'disk: total = 657'           ($sum -eq 657) "got $sum"
  Check 'Ask 5 total matches disk'    ($own -match '657\s+frames')
  $missing = @('182', '92', '186', '197') | Where-Object { -not $own.Contains($_) }
  Check 'Ask 5 states every per-stack count' ($missing.Count -eq 0) "missing: $($missing -join ',')"
} else {
  Check 'capture tree reachable' $false "missing $hr"
}

Write-Output ''
Write-Output 'D. Ask 5 states the burn, its limits, and does not oversell it'
Check 'Ask 5 exists'                     ($own -match 'Ask 5 — reshoot the calibration slide')
Check 'Ask 5 marked \$0'                 ($own -match 'Ask 5 — reshoot the calibration slide, eventually\. \*\*\$0\.\*\*')
Check 'Ask 5 says not urgent'            ($own -match 'Not urgent')
Check 'Ask 5 states the burn plainly'    ($own -match 'deliberately burned for instrument\s+development')
Check 'Ask 5 states the holdout rule'    ($own -match 'burns every member of it')
Check 'Ask 5 gives the real reason'      ($own -match 'genuine\s+optical improvement pair')
Check 'Ask 5 admits it cannot score'     ($own -match 'It commissions the instrument\. It cannot\s+score it')
Check 'Ask 5 names the circularity'      ($own -match 'as its own truth would be circular')
Check 'Ask 5 tells owner not to shoot early' ($own -match 'Do not shoot it yet')
Check 'Ask 5 credits the lane against interest' ($own -match 'against\s+its own interest')
# Pinned to the canonical sentence rather than to the conclusion alone: a mutation
# can insert a contradicting claim upstream while leaving the conclusion intact,
# and a check that reads only the conclusion will pass a self-contradicting file.
Check 'Ask 5 limitation stated at its canonical site' ($own -match 'it cannot finish the detail question on its own: the four stacks lack the')
Check 'Ask 5 makes no scoring claim'     (-not ($own -match 'it can score the axis'))

Write-Output ''
Write-Output 'E. no bar was quietly lowered in an owner-facing document'
Check 'Zerene ask still says Professional $289' ($own -match 'Ask 3 — buy Zerene \*\*Professional, \$289\*\*')
Check 'Helicon still not recommended for purchase' ($own -match 'Do not buy Helicon yet')
Check 'M8 FAIL not contradicted here'    (-not ($own -match 'M8 (now )?passes'))

Write-Output ''
Write-Output "RESULT: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
