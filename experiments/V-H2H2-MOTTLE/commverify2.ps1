param([string]$Verifier = 'verify12.py', [int]$Plants = 14, [int[]]$Gaps = @(7,8))
# Commission verify12.py. A checker that has only ever been shown to pass is not
# evidence.
#
# The subtlety this script exists to handle: on an earlier run a plant was scored
# "caught" because the run went RED -- but the failing check was a pre-existing
# failure with nothing to do with the plant. A red for the wrong reason is worth
# no more than a green for the wrong reason. So the baseline failure set is
# measured first and every plant must produce a failure that is NOT in it.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Get-Failures($out) {
  $line = ($out | Select-String -Pattern '^RED: ').Line
  if (-not $line) { return @() }
  return (($line -replace '^RED: ', '') -split '  \d+ checks')[0].Split(',').Trim()
}

Write-Host "baseline (no plant)"
$base = & python -u $Verifier 2>&1 | ForEach-Object { "$_" }
$baseFail = Get-Failures $base
$census = (($base | Select-String -Pattern 'NOT COVERED').Line -join ' ').Trim()
Write-Host ("  {0} pre-existing failures; {1}" -f $baseFail.Count, $census)
if ($baseFail.Count -gt 0) {
  Write-Host ("  RED -- fix the baseline before commissioning: " + ($baseFail -join '; ')) -ForegroundColor Red
  exit 1
}

# Indices whose values the verifier does not re-derive. Declaring them here is the
# point: an undeclared survivor is a defect in the checker, a declared one is a
# measured gap in its coverage.
$expectSurvive = $Gaps
$caught = 0; $gap = 0; $bad = @()
Write-Host "`nplants"
for ($i = 0; $i -lt $Plants; $i++) {
  $out = & python -u $Verifier --plant $i 2>&1 | ForEach-Object { "$_" }
  $rc = $LASTEXITCODE
  if ($out -match 'PLANT TARGET OCCURS') {
    Write-Host ("  VOID    [{0,2}] plant target is stale -- control could not be applied" -f $i) -ForegroundColor Red
    $bad += "$i (void)"
    continue
  }
  $name = ($out | Select-String -Pattern '^PLANTED \[\d+\] ([^:]+):').Matches[0].Groups[1].Value
  $new = @(Get-Failures $out | Where-Object { $baseFail -notcontains $_ })
  if ($new.Count -gt 0) {
    $caught++
    Write-Host ("  caught  [{0,2}] {1,-22} -> {2}" -f $i, $name, ($new -join '; '))
  } elseif ($rc -ne 0) {
    Write-Host ("  WRONG   [{0,2}] {1,-22} -> red, but only on pre-existing failures" -f $i, $name) -ForegroundColor Red
    $bad += "$i $name (red for the wrong reason)"
  } else {
    if ($expectSurvive -contains $i) {
      $gap++
      Write-Host ("  gap     [{0,2}] {1,-22} -> declared uncovered" -f $i, $name) -ForegroundColor Yellow
    } else {
      Write-Host ("  MISSED  [{0,2}] {1}" -f $i, $name) -ForegroundColor Red
      $bad += "$i $name"
    }
  }
}
Write-Host ""
# caught + gap + bad must exhaust the plants, so a MISSED can never be read as a
# gap and a plant can never quietly go uncounted
Write-Host ("{4} plants: {0} caught by a new failure, {1} survived inside a declared gap, {2} unaccounted (sum {3})" -f $caught, $gap, $bad.Count, ($caught + $gap + $bad.Count), $Plants)
if (($caught + $gap + $bad.Count) -ne $Plants) {
  Write-Host ("RED -- outcomes sum to {0}, not {1}" -f ($caught + $gap + $bad.Count), $Plants) -ForegroundColor Red
  exit 1
}
if ($bad.Count -gt 0) {
  Write-Host ("RED -- " + ($bad -join '; ')) -ForegroundColor Red
  exit 1
}
Write-Host "GREEN -- every plant is either caught by a new failure or a declared gap" -ForegroundColor Green

