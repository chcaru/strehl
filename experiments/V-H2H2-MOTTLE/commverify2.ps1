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
$base = & python -u verify12.py 2>&1 | ForEach-Object { "$_" }
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
$expectSurvive = @(7, 8)
$caught = 0; $survived = 0; $bad = @()
Write-Host "`nplants"
for ($i = 0; $i -lt 14; $i++) {
  $out = & python -u verify12.py --plant $i 2>&1 | ForEach-Object { "$_" }
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
    $survived++
    if ($expectSurvive -contains $i) {
      Write-Host ("  gap     [{0,2}] {1,-22} -> declared uncovered" -f $i, $name) -ForegroundColor Yellow
    } else {
      Write-Host ("  MISSED  [{0,2}] {1}" -f $i, $name) -ForegroundColor Red
      $bad += "$i $name"
    }
  }
}
Write-Host ""
Write-Host ("14 plants: {0} caught by a new failure, {1} survived inside a declared gap, {2} unaccounted" -f $caught, $survived, $bad.Count)
if ($bad.Count -gt 0) {
  Write-Host ("RED -- " + ($bad -join '; ')) -ForegroundColor Red
  exit 1
}
Write-Host "GREEN -- every plant is either caught by a new failure or a declared gap" -ForegroundColor Green
