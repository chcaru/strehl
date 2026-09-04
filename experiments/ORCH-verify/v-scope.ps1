param([string]$ScorecardPath = 'C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-09-sota-scorecard.md')
$ErrorActionPreference = 'Stop'
$root = 'C:\dev\blog\death-of-software\projects\strehl'
$pass = 0; $fail = 0
function Chk($n, $c) { if ($c) { $script:pass++; "  PASS  $n" } else { $script:fail++; "  FAIL  $n" } }
function Flat($p) { ((Get-Content $p | ForEach-Object { $_ -replace '^\s*>\s?', '' }) -join ' ') -replace '\s+', ' ' }

$sc = Flat $ScorecardPath
$pl = Flat "$root\docs\proposals\2026-08-sota-path.md"

Write-Output '=== A. the owner sentence, quoted from the PLAN itself ==='
Chk 'clause 1 instrument D1'      ($pl.Contains('D1: FRC + slant-edge, licensed Zerene PMax *and* DMap'))
Chk 'clause 2 instrument'         ($pl.Contains('at strictly lower noise'))
Chk 'clause 2 names flat-ROI'     ($pl.Contains('(existing flat-ROI instrument)'))
Chk 'clause 3 hull census'        ($pl.Contains('with zero invented structure (hull census, stamped'))
Chk 'clause 4 halo instrument'    ($pl.Contains('(halo instrument at full reach)'))
Chk 'clause 5 D2/D8/A5/C5'        ($pl.Contains('(D2/D8/A5/C5)'))
Chk 'clause 6 existing harness'   ($pl.Contains('s per frame on CPU (existing harness)'))
Chk 'plan: Helicon if obtainable' ($pl.Contains('Helicon if obtainable'))
Chk 'plan: fork is a comparator'  ($pl.Contains('the fork rebuilt at its best-known build'))
Chk 'plan: Zerene-only purchase'  ($pl.Contains('licence a commercial comparator'))
Chk 'plan: Prosumer $189'         ($pl.Contains('Prosumer ($189)'))
Chk 'plan: Professional $289'     ($pl.Contains('Professional ($289)'))
Chk 'plan: noise quotable now'    ($pl.Contains('Nothing -- quotable now') -or $pl.Contains('Nothing — quotable now'))

Write-Output '=== B. the false text survives ONLY as a quoted withdrawal ==='
$amendIdx = $sc.IndexOf('AMENDMENT — publication scope corrected')
$oldIdx   = $sc.IndexOf('passes every primary bar below against licensed Zerene Stacker')
$oldCount = ([regex]::Matches($sc, [regex]::Escape('passes every primary bar below against licensed Zerene Stacker'))).Count
Chk 'old text occurs exactly once'     ($oldCount -eq 1)
Chk 'old text sits INSIDE the amendment' (($amendIdx -ge 0) -and ($oldIdx -gt $amendIdx))
Chk 'old text marked as previous'      ($sc.Contains('This paragraph previously read'))
Chk 'operative sentence is the new one' ($sc.Contains('satisfies every clause of that sentence against the licensed'))
Chk 'old mandatory-Helicon gone'       (-not $sc.Contains('against licensed Zerene Stacker and Helicon Focus under one common'))

Write-Output '=== C. the amendment says what it must ==='
Chk 'amendment present'                ($sc.Contains('AMENDMENT — publication scope corrected to the owner'))
Chk 'names all seven axes'             ($sc.Contains('**M1** (`D1: FRC + slant-edge`)') -and $sc.Contains('**M11** (*"existing harness"*)'))
Chk 'names the five additions'         ($sc.Contains('**M4, M5, M6, M7 and M12 are named by no clause of it**'))
Chk 'additions not prerequisites'      ($sc.Contains('they are not prerequisites for the owner'))
Chk 'Helicon now optional'             ($sc.Contains('Helicon was never mandatory'))
Chk 'required set = Zerene + fork'     ($sc.Contains('licensed Zerene Stacker plus the fork at its best-known build'))
Chk 'fork omission acknowledged'       ($sc.Contains('M158 finding 9'))
Chk 'M8 FAIL explicitly preserved'     ($sc.Contains('M8 still reads `FAIL`, on M8-R at') -and $sc.Contains('1.030569%'))
Chk 'lowers no bar, stated'            ($sc.Contains('It lowers no bar, retracts no `FAIL`'))
Chk 'verified independently, stated'   ($sc.Contains('rather than accepting the audit'))

Write-Output '=== D. publication rule reconciled ==='
Chk 'pub amendment present'            ($sc.Contains('AMENDMENT — what "required" means here'))
Chk 'seven listed in pub rule'         ($sc.Contains('`M1`, `M2`, `M3`, `M8`, `M9`, `M10`, `M11`'))
Chk 'additions still published'        ($sc.Contains('must still be published'))
Chk 'no suppression of owner sentence' ($sc.Contains('would be reporting this document'))
Chk 'unknown-position sentence kept'   ($sc.Contains('competitive position against Zerene Stacker and Helicon Focus is unknown'))

Write-Output '=== E. audit source exists ==='
Chk 'M158 report on disk'              (Test-Path "$root\docs\research\M158-scorecard-drift.md")
Chk 'M135 report on disk'              (Test-Path "$root\docs\research\M135-detail-instrument.md")

Write-Output ''
Write-Output "RESULT: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
