param(
  [string]$Status = "$PSScriptRoot\..\..\docs\STATUS.md",
  [string]$Owner  = "$PSScriptRoot\..\..\docs\OWNER-ACTIONS.md",
  [string]$M157   = "$PSScriptRoot\..\..\docs\research\M157-comparator-viability.md",
  [string]$M161   = "$PSScriptRoot\..\..\docs\research\M161-bar-feasibility.md",
  [string]$Scorecard = "$PSScriptRoot\..\..\docs\proposals\2026-09-sota-scorecard.md",
  [string]$M3     = "$PSScriptRoot\..\..\docs\research\M161-m3-ratification.md",
  [string]$NcOwn  = "$PSScriptRoot\nc-owner0906.ps1"
)

# Forward verifier for STATUS section 2.9.53.
#
# Two-sided by construction. Every claim 2.9.53 makes about another document is
# checked against THAT DOCUMENT, not just against 2.9.53's own prose. A verifier
# that only reads STATUS proves the file agrees with itself, which is not the
# property anyone cares about.
#
# This verifier must DEGRADE TO FAIL, NEVER THROW. A verifier that crashes
# reports nothing about which check failed, and a crash inside a negative-control
# harness can skip the restore and leave the document damaged on disk. Both have
# happened here.

$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$pass = 0; $fail = 0

function Check([string]$name, [scriptblock]$test, [string]$detail = '') {
  $ok = $false
  try { $ok = [bool](& $test) } catch { $ok = $false; $detail = "threw: $($_.Exception.Message)" }
  if ($ok) { $script:pass++; Write-Output ("  PASS  " + $name) }
  else { $script:fail++; Write-Output ("  FAIL  " + $name + $(if ($detail) { "  [$detail]" } else { '' })) }
}
function Flat([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return '' }
  $lines = Get-Content -LiteralPath $p -Encoding UTF8 | ForEach-Object { $_ -replace '^\s*>\s?', '' }
  (($lines -join ' ') -replace '\s+', ' ')
}

$statusRaw = if (Test-Path -LiteralPath $Status) { Get-Content -LiteralPath $Status -Raw -Encoding UTF8 } else { '' }

# Delimit on the NEXT header, never on a distant landmark. Delimiting 2.9.51 on
# "## 3. Gaps" once silently swallowed a newly appended 2.9.52 into 2.9.51's
# body and corrupted every occurrence count taken from it.
$sec = ''
$mStart = [regex]::Match($statusRaw, '(?m)^### 2\.9\.53\b')
if ($mStart.Success) {
  $rest = $statusRaw.Substring($mStart.Index)
  # Skip PAST the whole header line before searching for the next header.
  # Searching from index 1 leaves "## 2.9.53 ..." at the start of the string,
  # where (?m)^ matches, so "## \d" matches the truncated header itself and the
  # section comes back one character long.
  $nl = $rest.IndexOf("`n")
  if ($nl -lt 0) {
    $sec = $rest
  } else {
    $body = $rest.Substring($nl + 1)
    $mEnd = [regex]::Match($body, '(?m)^(### 2\.9\.\d+|## \d)')
    $sec = if ($mEnd.Success) { $rest.Substring(0, $nl + 1 + $mEnd.Index) } else { $rest }
  }
}
$secF = (($sec -split "`r?`n" | ForEach-Object { $_ -replace '^\s*>\s?', '' }) -join ' ') -replace '\s+', ' '

$own  = Flat $Owner
$m157 = Flat $M157
$m161 = Flat $M161
$scard = Flat $Scorecard
$ncOwnRaw = if (Test-Path -LiteralPath $NcOwn) { Get-Content -LiteralPath $NcOwn -Raw -Encoding UTF8 } else { '' }

Write-Output 'A. the section exists, is delimited, and did not eat its neighbour'
Check 'section 2.9.53 exists'            { $mStart.Success }
Check 'section is non-trivial'           { $sec.Length -gt 3000 } "len=$($sec.Length)"
Check 'section did not swallow ## 3'     { -not ($sec -match '(?m)^## 3\. Gaps') }
Check '## 3. Gaps header survives'       { $statusRaw -match '(?m)^## 3\. Gaps, ranked by what stands between here and print-worthy' }
Check 'section 2.9.52 still present'     { $statusRaw -match '(?m)^### 2\.9\.52\b' }
Check 'exactly one 2.9.53 header'        { ([regex]::Matches($statusRaw, '(?m)^### 2\.9\.53\b')).Count -eq 1 }

Write-Output 'B. the correction it claims is MINE and is stated as a scheduling error'
Check 'owns the error'                   { $secF -match 'The correction is mine and it is the point of this section' }
Check 'names the two components'         { $secF -match 'a \*\*truth reference\*\* and a \*\*transfer veto\*\*' }
Check 'states only the reference is blocked' { $secF -match 'only the reference needs the capture' }
Check 'states the veto needs no capture' { $secF -match 'needs no ground truth and no new capture' }

Write-Output 'C. the M164 contract is stated correctly (admissibility, not quality)'
Check 'veto is an admissibility gate'    { $secF -match 'Its contract is admissibility, not quality' }
Check 'fires on blur'                    { $secF -match 'fire on planted blur' }
Check 'fires on sharpening'              { $secF -match 'on planted sharpening' }
Check 'fires on resampling'              { $secF -match 'on resampling' }
Check 'fires on blur composed with gain' { $secF -match 'blur composed with gain' }
Check 'gives the scalar-invariance reason' { $secF -match 'common \*scalar\* transfer is exactly what\s*the retired statistics were proved invariant to' }
Check 'must not fire on identity'        { $secF -match 'must not fire on identity' }
Check 'names the fires-on-everything failure' { $secF -match 'a veto that fires on everything blocks the program permanently' }
Check 'weights the sharpening direction' { $secF -match 'A veto that catches blur but not sharpening is half a veto' }
Check 'cites the bounded-below-by-zero burn' { $secF -match 'error was bounded below by zero' }

Write-Output 'D. M10 = three gaps, checked against OWNER-ACTIONS itself'
Check 'section says three gaps not one'  { $secF -match 'M10 is three gaps, not one' }
Check 'section quotes the old heading'   { $secF -match 'This is the whole of M10' }
Check 'OWNER no longer contains it'      { -not ($own -match 'This is the whole of M10') } 'source-side'
Check 'OWNER states one of three'        { $own -match 'One of three things M10 needs' } 'source-side'
Check 'section names the depth-product gap' { $secF -match 'a depth product that does not yet exist' }
Check 'section names the void instrument gap' { $secF -match 'the void instrument itself, now lane \*\*M163\*\*' }

Write-Output 'E. the M10 bar did NOT move — checked against OWNER-ACTIONS'
Check 'section quotes the band'          { $secF.Contains('[10.014357, 10.516727] deg') }
Check 'OWNER still has that band'        { $own.Contains('[10.014357, 10.516727] deg') } 'source-side'
Check 'section quotes the burn label'    { $secF -match 'BURNED — DEVELOPMENT ONLY' }
Check 'OWNER still has the burn label'   { $own -match 'BURNED — DEVELOPMENT ONLY' } 'source-side'
# The section claims two named controls exist to catch the bar being relaxed.
# That claim is only worth anything if the controls are really there.
Check 'NC22 really exists'               { $ncOwnRaw -match "NC22 widen the admissible angle band" } 'source-side'
Check 'NC23 really exists'               { $ncOwnRaw -match "NC23 un-burn the burned tilted-ruler stacks" } 'source-side'

Write-Output 'F. the uncertainty-repair warning is preserved'
Check 'inert instrument looks better behaved' { $secF -match 'looks better behaved than a correct one' }
Check 'noisier means the repair worked'  { $secF -match 'that is\s*the repair working' }
Check 'cannot-conclude beats false PASS' { $secF -match 'cannot conclude\* is worth more here than\s*a broken one that says PASS' }
# M161 is the source of the M10 void. Check the claim against M161, not STATUS.
Check 'M161 really voids M10'            { $m161 -match 'M10' -and $m161 -match 'INSTRUMENT VOID' } 'source-side'

Write-Output 'G. the Zerene finding, checked against M157'
Check 'section says purchase != gate'    { $secF -match 'must not be recorded as\s*closing the \*\*common-linear-input\*\* gate' }
Check 'section marks it NOT FOUND'       { $secF -match '\*\*\[NOT FOUND\]\*\*' }
Check 'M157 really rules NOT FOUND'      { $m157 -match '\*\*\[NOT FOUND\]\*\* Neither statement is explicitly attached to' } 'source-side'
Check 'M157 really verifies input-images' { $m157 -match 'exporting adjusted \*\*input images\*\*' } 'source-side'
Check 'section records the research-agent loss risk' { $secF -match 'which cannot\s*write files' }
Check 'OWNER email is conditional on answer 3' { $own -match 'provided\*\s+answer 3 confirms native-size 16-bit linear output' } 'source-side'

Write-Output 'H. the spiral, and the scoreboard that did not move'
Check 'section states fifteen sub-agents' { $secF -match 'spawned \*\*fifteen\*\* distinct' }
Check 'forfeit is explicitly acceptable' { $secF -match 'with forfeit explicitly acceptable' }
Check 'admission rule is the deliverable' { $secF -match 'the \*\*admission rule\*\* is the deliverable' }
Check 'records 23 of 23 rejections'      { $secF -match 'rejected 23 of 23 attempts' }
Check 'names the never-admits pattern'   { $secF -match 'indistinguishable from a broken instrument' }
Check 'scoreboard still zero of seven'   { $secF -match 'Zero of seven\s*gating axes have \*\*passed\*\*' }
Check 'does not claim an axis was scored' { -not ($secF -match 'first axis scored|axis is now scored|one of seven scored') }
Check 'distinguishes passed from scored' { $secF -match 'zero of\s*seven passed, exactly one scored, and the one that scored failed' }
Check 'owns the loose shorthand'         { $secF -match 'Writing "zero scored"\s*was convenient shorthand' }
Check 'quotes M8 as the only read score' { $secF -match 'the only axis in the program with a produced-and-read score' }
Check 'M8 numbers intact in section'     { $secF.Contains('M8-R `1.030569%`') -and $secF.Contains('M8-O `1.326144%`') }
Check 'scorecard really says only-score' { $scard -match 'the only axis in the program with a produced-and-read score' } 'source-side'
Check 'scorecard still FAILs M8'         { $scard -match '\*\*FAIL\*\* — M8-R `1\.030569%`' } 'source-side'

Write-Output 'I. the two lanes that landed, checked against their commits'
Check 'section records M160 commit'      { $secF -match '\(`513ea3fe`' }
Check 'M160 commit really exists'        { (git -C $root --no-pager log -1 --format='%h' 513ea3fe 2>$null) -eq '513ea3fe' } 'source-side'
Check 'section records the gate set'     { $secF -match 'exactly M1, M2, M3, M8, M9,\s*M10, M11' }
Check 'section records DISCLOSURE MISS'  { $secF -match '`DISCLOSURE MISS`' }
Check 'scorecard really has that verdict' { $scard -match 'DISCLOSURE MISS' } 'source-side'
Check 'section says no bar moved'        { $secF -match 'No bar moved and no\s*FAIL was erased' }
Check 'section records M161 commit'      { $secF -match '\(`47d67a9f`' }
Check 'M161 commit really exists'        { (git -C $root --no-pager log -1 --format='%h' 47d67a9f 2>$null) -eq '47d67a9f' } 'source-side'
Check 'section states the M3 bar'        { $secF.Contains('max_e max(h_e,v_e) <= 0.05') }
Check 'M3 report really states that bar' { (Flat $M3).Contains('max_e max(h_e,v_e) <= 0.05') } 'source-side'
Check 'section says M3 TIGHTENS'         { $secF -match '\*\*tightens\*\* the\s*scorecard rather than relaxing it' }
Check 'section says M3 is BLOCKED'       { $secF -match "M3's\s*verdict is BLOCKED" }

Write-Output 'J. M161 corrected my critical-path claim and the correction is recorded'
Check 'records the stack-vs-session fix' { $secF -match 'one\s*inversion stack cannot alone unblock M1, M2 and M9; one coordinated session can capture' }
Check 'states the owner-facing consequence' { $secF -match 'must say \*session\*, not \*stack\*' }
# Population assertion: presence checks are satisfied by any duplicate, so also
# pin how many times the scoreboard is asserted across the whole file.
Check 'no accidental second 2.9.53 body' { ([regex]::Matches($statusRaw, [regex]::Escape('The blocked half and the unblocked half'))).Count -eq 1 }

Write-Output ''
Write-Output "RESULT: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
