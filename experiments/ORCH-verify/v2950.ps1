param([string]$Status = "$PSScriptRoot\..\..\docs\STATUS.md")

# Forward verifier for STATUS section 2.9.50.
# Every factual claim in that section is checked against its primary source:
# the owner's plan, the lane reports, the capture tree on D:, and live re-runs
# of the two gates the section quotes numbers from.
#
# Two mechanical rules are enforced throughout, both learned the hard way:
#   * blockquote '>' is stripped PER LINE before joining, never after.
#   * quotations are matched against whitespace-collapsed text, because a
#     phrase that wraps in the source will not match as a single string and
#     its failure to match would read as absence.

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$pass = 0; $fail = 0

function Flat([string]$p) {
  # strip blockquote markers per line, then join, then collapse whitespace
  $lines = Get-Content -LiteralPath $p -Encoding UTF8 | ForEach-Object { $_ -replace '^\s*>\s?', '' }
  (($lines -join ' ') -replace '\s+', ' ')
}
function Check([string]$name, [bool]$ok, [string]$detail = '') {
  if ($ok) { $script:pass++; Write-Output ("  PASS  " + $name) }
  else { $script:fail++; Write-Output ("  FAIL  " + $name + $(if ($detail) { "  [$detail]" } else { '' })) }
}

# ---- the section under test, isolated so checks cannot be satisfied elsewhere
$all = Get-Content -LiteralPath $Status -Encoding UTF8
$s = [array]::IndexOf($all, ($all | Where-Object { $_ -match '^### 2\.9\.50 ' } | Select-Object -First 1))
if ($s -lt 0) { Write-Output '  FAIL  section 2.9.50 present'; exit 1 }
$e = -1
for ($i = $s + 1; $i -lt $all.Count; $i++) { if ($all[$i] -match '^## 3\. Gaps') { $e = $i; break } }
if ($e -lt 0) { Write-Output '  FAIL  section 2.9.50 terminates'; exit 1 }
$secLines = $all[$s..($e - 1)]
$sec = ((($secLines | ForEach-Object { $_ -replace '^\s*>\s?', '' }) -join ' ') -replace '\s+', ' ')

Write-Output 'A. structure'
Check 'section 2.9.50 present and bounded' ($secLines.Count -gt 80) "lines=$($secLines.Count)"
Check 'has a Position subsection' ($sec -match '2\.9\.50\.7 Position')
Check 'records own errors' ($sec -match '2\.9\.50\.6 Two errors of my own, recorded')

Write-Output ''
Write-Output 'B. quotations from the owner plan (primary source)'
$plan = Flat "$root\docs\proposals\2026-08-sota-path.md"
$planQuotes = @(
  'Under assessment is an inversion -- score a 1.4x TC-off stack and use 2.8x bursts as its truth, giving exactly',
  'The invariance and the blindness are one property, not two',
  'Every candidate above was retired without such an arm ever being run',
  'Helicon if obtainable',
  'the fork rebuilt at its best-known build',
  'resolves detail at or beyond the best shipping comparator',
  'it can establish invention; it cannot name the inventor'
)
foreach ($q in $planQuotes) {
  $inPlan = $plan.Contains($q)
  $inSec = $sec.Contains($q)
  Check "plan contains: $($q.Substring(0,[Math]::Min(52,$q.Length)))" $inPlan
  if ($q -notmatch 'establish invention') {
    Check "  ...and 2.9.50 quotes it" $inSec
  }
}
# the D1 licence must be present in the plan exactly as the section describes it
Check 'plan licenses the detail clause with (D1: FRC + slant-edge)' ($plan -match 'D1: FRC \+\s*slant-edge')

Write-Output ''
Write-Output 'C. numbers quoted from the plan'
foreach ($n in @('1.268326', '.923468', '0.28125', '0.0625')) {
  Check "plan states $n" ($plan.Contains($n)) 
}
Check '2.9.50 states the reversed-arm pair' (($sec.Contains('1.268326')) -and ($sec.Contains('.923468')))

Write-Output ''
Write-Output 'D. the M8 FAIL is preserved, not retracted'
Check '2.9.50 states M8 still reads FAIL' ($sec -match 'M8 still\s+reads `FAIL` on M8-R at `1\.030569%`')
$scorecard = Flat "$root\docs\proposals\2026-09-sota-scorecard.md"
Check 'scorecard still carries the 1.030569% FAIL' ($scorecard.Contains('1.030569'))

Write-Output ''
Write-Output 'E. capture inventory re-counted from disk'
$hr = 'D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl'
if (Test-Path $hr) {
  $counts = @{}
  foreach ($d in Get-ChildItem $hr -Directory) {
    $counts[$d.Name] = (Get-ChildItem $d.FullName -File -Recurse -Include *.ARW, *.arw -ErrorAction SilentlyContinue).Count
  }
  Check 'tilted-sw4-cpl = 182'             ($counts['tilted-sw4-cpl'] -eq 182)             "got $($counts['tilted-sw4-cpl'])"
  Check 'tilted-sw10-cpl = 92'             ($counts['tilted-sw10-cpl'] -eq 92)             "got $($counts['tilted-sw10-cpl'])"
  Check 'flat-sw4-cpl = 186'               ($counts['flat-sw4-cpl'] -eq 186)               "got $($counts['flat-sw4-cpl'])"
  Check 'very-tilted-all-axis-sw10-cpl = 197' ($counts['very-tilted-all-axis-sw10-cpl'] -eq 197) "got $($counts['very-tilted-all-axis-sw10-cpl'])"
  $sum = ($counts.Values | Measure-Object -Sum).Sum
  Check 'frames sum to 657'                ($sum -eq 657)                                  "got $sum"
  $missing = @('182', '92', '186', '197', '657') | Where-Object { -not $sec.Contains($_) }
  Check '2.9.50 states each count' ($missing.Count -eq 0) "missing: $($missing -join ',')"
} else {
  Check 'capture tree reachable' $false "missing $hr"
}
Check 'the inversion arithmetic is stated' ($sec -match '2\.8/1\.4 = 2\.0x')
Check 'the inversion arithmetic is true'   ([Math]::Abs((2.8 / 1.4) - 2.0) -lt 1e-12)

Write-Output ''
Write-Output 'F. the burn decision is recorded as a decision, with its limit'
Check 'burn stated as deliberate and owned' ($sec -match 'deliberately burned that session for instrument development, and I own the\s+decision')
Check 'the may-not-score limit is stated'   ($sec -match 'may not report any number from it as a score')
Check 'holdout unit is stated correctly'    ($sec -match 'subject plus uninterrupted capture\s+session')

Write-Output ''
Write-Output 'G. live re-run: scope amendment gate'
Push-Location "$PSScriptRoot"
$vs = & .\v-scope.ps1 2>&1 | Out-String
$ns = & .\nc-scope.ps1 2>&1 | Out-String
Pop-Location
Check 'v-scope reports 35 passed, 0 failed' ($vs -match 'RESULT: 35 passed, 0 failed')
Check 'nc-scope reports 6 correctly RED'    ($ns -match 'NEGATIVE CONTROLS: 6 correctly RED, 0 wrongly GREEN')
Check '2.9.50 quotes 35/35 and 6/6'         (($sec -match '35/35') -and ($sec -match '6/6 negative controls'))

Write-Output ''
Write-Output 'H. live re-run: capture-request gate (numbers quoted in 2.9.50.5)'
$g = & python "$root\experiments\M156-capreq-verify\verify_capture_request.py" 2>&1 | Out-String
Check 'gate partitions 141 with zero skipped' ($g -match 'CHECKS total=141 passed=141 failed=0 skipped=0 accounted=141')
Check 'gate reconciles BLOCK_SUM to STATED_TOTAL' ($g -match 'BLOCK_SUM 891 STATED_TOTAL 891')
Check 'gate verdict GREEN' ($g -match 'VERDICT GREEN')
Check '2.9.50 quotes the partition verbatim' ($sec.Contains('total=141 passed=141 failed=0 skipped=0 accounted=141'))
Check '2.9.50 quotes BLOCK_SUM 891 / STATED_TOTAL 891' (($sec.Contains('BLOCK_SUM 891')) -and ($sec.Contains('STATED_TOTAL 891')))

Write-Output ''
Write-Output 'I. commit 6b966d8c is real and touched what the section says'
$show = & git -C $root show --stat --format='' 6b966d8c 2>&1 | Out-String
Check 'commit exists' ($LASTEXITCODE -eq 0)
Check 'commit touched the scorecard' ($show -match 'docs/proposals/2026-09-sota-scorecard\.md')
Check 'commit touched both verifier scripts' (($show -match 'v-scope\.ps1') -and ($show -match 'nc-scope\.ps1'))

Write-Output ''
Write-Output 'J. cross-reference into 2.9.49 resolves'
$prev = ((($all | ForEach-Object { $_ -replace '^\s*>\s?', '' }) -join ' ') -replace '\s+', ' ')
Check "2.9.49.7 really contains the phrase 2.9.50 attributes to it" ($prev.Contains("M136's disease at program scale"))
Check '2.9.50 attributes it to 2.9.49.7' ($sec -match "2\.9\.49\.7 named .M136's disease at program scale")

Write-Output ''
Write-Output 'K. the seven-axis claim is stated consistently with the six-clause sentence'
Check 'section distinguishes six clauses from seven axes' ($sec -match 'six clauses, but one clause carries two\s+axes')
Check 'section names all seven axes' (($sec -match 'M1, M2, M3, M8, M9, M10, M11'))
Check 'section names the five that are not licensed' ($sec -match 'M4, M5, M6, M7 or M12')

Write-Output ''
Write-Output "RESULT: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
