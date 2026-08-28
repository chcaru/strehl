# Verify that a claimed number is actually banked in a NAMED committed file.
#
# WHY THIS EXISTS: the orchestrator previously prescribed "git grep -F <value>
# across HEAD and report the hit count". That instrument is BLIND. Measured:
# three numbers INVENTED on the spot and never published anywhere scored 332,
# 46 and 46 hits corpus-wide, against 792/1618/439 for real published findings
# -- same order of magnitude. `git grep -F` substring-matches short decimals
# against hundreds of float CSVs, so "12/12 banked" proved nothing. Any lane
# that certified its banking with the unscoped grep must be re-checked here.
# Corpus facts 1962-1963.
#
# THE FIX, and it is two independent changes:
#   1. SCOPE  -- search one named file, not the whole tree.
#   2. BOUND  -- require a digit boundary, so 0.9137 does not match 10.91372.
#
# Usage:
#   verify_banked.ps1 -File docs/research/X.md -Values 0.534,6.76 [-Controls 8675309]
#
# Commissioned before use: with -File docs/research/BUILD-DEFECT.md, the three
# real values (its exhibit SHA256, 459736, 16039) read BANKED 3/3 and four
# invented controls read NOT-BANKED 4/4. A run whose controls do not all read
# NOT-BANKED is reporting on a broken instrument and must be discarded.
param(
  [Parameter(Mandatory = $true)][string]$File,
  [Parameter(Mandatory = $true)][string[]]$Values,
  [string[]]$Controls = @('8675309', '0.9137', '2.7715')
)
$ErrorActionPreference = 'Stop'
trap { Write-Host $_.Exception.Message; exit 1 }

$blob = (git show "HEAD:$File" 2>$null) -join "`n"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($blob)) {
  throw "REFUSING: '$File' is not readable at HEAD -- cannot certify banking against a file that is not committed"
}

# `powershell -File script.ps1 -Values a,b,c` binds ONE string containing commas,
# not a 3-element array. That silently turned a 3-of-3 pass into a 0-of-1 fail
# during commissioning. Normalise both invocation styles.
$Values = @($Values | ForEach-Object { $_ -split ',' } | Where-Object { $_ -ne '' })
$Controls = @($Controls | ForEach-Object { $_ -split ',' } | Where-Object { $_ -ne '' })
if ($Values.Count -eq 0) { throw "REFUSING: no values to check" }

function Test-Token([string]$hay, [string]$needle) {
  # Digit boundaries on both sides: a longer number must not satisfy a shorter claim.
  return $hay -match ("(?<![0-9])" + [regex]::Escape($needle) + "(?![0-9])")
}

# Commission the instrument on THIS run's data before trusting its verdicts.
$badControl = @()
foreach ($c in $Controls) {
  if (Test-Token $blob $c) { $badControl += $c }
}
if ($badControl.Count -gt 0) {
  throw ("REFUSING: control value(s) " + ($badControl -join ', ') +
         " were FOUND in $File. A control that hits means this file genuinely contains it" +
         " or the matcher is broken; either way the verdicts below are not trustworthy." +
         " Choose different controls and re-run.")
}

$banked = 0
$missing = @()
foreach ($v in $Values) {
  if (Test-Token $blob $v) { $banked++; "  BANKED      $v" }
  else { $missing += $v; "  NOT-BANKED  $v" }
}

"controls clean : {0}/{0} read NOT-BANKED" -f $Controls.Count
"banked         : {0} of {1}" -f $banked, $Values.Count
if ($missing.Count -gt 0) {
  "NOT BANKED     : {0}" -f ($missing -join ', ')
  exit 2
}
"ALL VALUES BANKED in $File"
exit 0
