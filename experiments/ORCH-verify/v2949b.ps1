param([string]$StatusPath = 'C:\dev\blog\death-of-software\projects\strehl\docs\STATUS.md')
$ErrorActionPreference = 'Stop'
$root = 'C:\dev\blog\death-of-software\projects\strehl'
$pass = 0; $fail = 0
function Chk($n, $c) { if ($c) { $script:pass++; "  PASS  $n" } else { $script:fail++; "  FAIL  $n" } }
function Flat($p) { ((Get-Content $p | ForEach-Object { $_ -replace '^\s*>\s?', '' }) -join ' ') -replace '\s+', ' ' }

$st  = Flat $StatusPath
$oa  = Flat "$root\docs\OWNER-ACTIONS.md"
$sc  = Flat "$root\docs\proposals\2026-09-sota-scorecard.md"
$pl  = Flat "$root\docs\proposals\2026-08-sota-path.md"

Write-Output '=== A. arithmetic re-derived from scratch ==='
Chk 'census sums to 1233'        ((221+399+511+102) -eq 1233)
Chk 'scored flat tiles = 138'    ((55+83+0) -eq 138)
Chk 'total scored = 388'         ((138+250) -eq 388)
Chk 'theta = 10.259461685 deg'   ([Math]::Round([Math]::Atan(1.81/10.0)*180/[Math]::PI,9) -eq 10.259461685)
$m0 = 0.181
Chk 'band low  = 10.014357'      ([Math]::Round([Math]::Atan($m0/1.025)*180/[Math]::PI,6) -eq 10.014357)
Chk 'band high = 10.516727'      ([Math]::Round([Math]::Atan($m0/0.975)*180/[Math]::PI,6) -eq 10.516727)
Chk 'one-sided doubling'         ([Math]::Round(0.027243*2,6) -eq 0.054486)
Chk 'tol at 100mm ~ 0.44mm'      ([Math]::Round(($m0-$m0/1.025)*100,2) -eq 0.44)
Chk 'tol at 500mm ~ 2.32mm'      ([Math]::Round(($m0/0.975-$m0)*500,2) -eq 2.32)
Chk 'max>=mean identity'         ([Math]::Max(0.0,0.054486) -ge (0.0+0.054486)/2)

Write-Output '=== B. every quotation checked at ITS OWN source file ==='
Chk 'OWNER-ACTIONS: "That was false"'         ($oa.Contains('That was false'))
Chk 'plan: "Helicon if obtainable"'           ($pl.Contains('Helicon if obtainable'))
Chk 'scorecard: M11 step 7 wording'           ($sc.Contains('the fastest mode that passes all quality gates'))
Chk 'scorecard: real rule-4 annotation'       ($sc.Contains('Narrowing rule 4 unlocks nothing today'))
Chk 'scorecard: "That claim is withdrawn."'   ($sc.Contains('That claim is withdrawn.'))
Chk 'scorecard: false headline preserved'     ($sc.Contains('Same money, same shooting, four more axes.'))
Chk 'scorecard: M146 audit cited'             ($sc.Contains('M146-unlock-audit.md'))
Chk 'rule 4 still UNRATIFIED'                 ($sc.Contains('UNRATIFIED'))
$curv = Flat "$root\docs\research\M-PHASE0-CURV.md"
$lca  = Flat "$root\docs\research\M-PHASE0-LCA.md"
Chk 'CURV frame counts 120/85/65'             (($curv -match '\b120\b') -and ($curv -match '\b85\b') -and ($curv -match '\b65\b'))
Chk 'LCA names f/11 primary ruler'            ($lca.Contains('primary ruler'))
Chk 'README rise/run quote verbatim'          (((Get-Content 'D:\personal\macro\requests\8-tilted-planar\README.md' -Raw) -replace '\s+',' ').Contains('10cm run against 1.81cm rise'))

Write-Output '=== C. STATUS quotes match the sources exactly ==='
Chk 'STATUS uses the REAL annotation'         ($st.Contains('*"Narrowing rule 4 unlocks nothing today"*'))
Chk 'STATUS repeats step-7 wording exactly'   ($st.Contains('the fastest mode that passes all quality gates'))
Chk 'STATUS cites M146 for the audit'         ($st.Contains('M146-unlock-audit.md'))
Chk 'fabricated phrase kept ONLY as confession' (
      ($st.Contains('acquired quotation marks')) -and
      ($st.IndexOf('it changes nothing measurable today') -gt $st.IndexOf('I had carried a paraphrase')))

Write-Output '=== D. the section says what it must ==='
Chk '2.9.49 heading present'                  ($st.Contains('### 2.9.49 A false table in my own pre-registered document'))
Chk 'admits the reader was me'                ($st.Contains('the careful reader was me'))
Chk 'true payoff stated both rows'            ($st.Contains('`2 -> 2` and `4 -> 4`, **no change at all**'))
Chk 'three errors, not two'                   ($st.Contains('Three wrong conclusions'))
Chk 'M3 capture-sufficient stated'            ($st.Contains('No new M3 photons are required'))
Chk 'tautological null explained'             ($st.Contains('A null that reads zero by construction'))
Chk 'open question flagged open'              ($st.Contains('decisive open question and it is still open'))
Chk 'burn frame-count evidence given'         ($st.Contains('exactly the frame counts in the holdout'))
Chk 'longer ruler not laboratory'             ($st.Contains('a longer ruler, not a laboratory'))
Chk 'position still 0 of 12 (pinned to 2.9.49)' ($st.Contains('**Unchanged: `0 of 12`.** Four instruments got more trustworthy'))
Chk 'six-clause structural question raised'   ($st.Contains('three of those clauses rest on instruments the plan says already exist'))
Chk 'not immune disclaimer'                   ($st.Contains('naming it is not the same as being immune to'))

Write-Output '=== E. M154 defects 5 and 6 corrected ==='
Chk 'defect5: "says only" gone'               (-not $st.Contains('the ruler record says only'))
Chk 'defect5: derivation acknowledged'        ($st.Contains('`1.81 cm` rise'))
Chk 'defect6: "no derivation" gone'           (-not $st.Contains('with no derivation and no uncertainty'))
Chk 'defect6: interval language present'      ($st.Contains('therefore no interval'))

Write-Output '=== F. referenced commits exist ==='
Push-Location $root
foreach ($c in @('74b599c5','4b79b6dc','975dc147','6915fe44','5ab2ddd6','d4f574c6','68ea3b95')) {
  $null = & git cat-file -e "$c^{commit}" 2>&1
  Chk "commit $c exists" ($LASTEXITCODE -eq 0)
}
Pop-Location

Write-Output ''
Write-Output "RESULT: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
