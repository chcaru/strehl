# V-SPEED timer commissioning.
#
# A timer that cannot see a planted 5 s cannot see a real 5 s. This plants
# exactly 5.0 s inside the timed region of ONE named stage -- on the production
# code path, via runner.py's V_SPEED_PLANT_STAGE / V_SPEED_PLANT_S -- and
# requires that the reported warm median for that stage moves by +5.00 s while
# the OTHER stage in the same run does not move.
#
# It is a 2x2, not a single plant: `strehl` planted / `focus-stack` planted,
# each read against the same unplanted control. A one-sided plant cannot
# distinguish "the timer saw 5 s" from "the timer adds 5 s to everything".
#
# Subject: 109MSDCF (22 frames), the cheap arm, so commissioning costs ~10 min.

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$src = 'D:\personal\macro\109MSDCF'
$subject = '109MSDCF'

Write-Host '--- clock check: perf_counter around a child of known duration ---'
python clockcheck.py
if ($LASTEXITCODE -ne 0) { throw 'CLOCK-CHECK FAILED - refusing to time anything' }

# One develop so focus-stack has input. Not part of the commissioning arms.
$env:V_SPEED_PLANT_STAGE = ''
$env:V_SPEED_PLANT_S = '0'
python runner.py --subject $subject --src $src --rounds 1 --tag commission-prep --only develop
if ($LASTEXITCODE -ne 0) { throw 'develop prep failed' }

Write-Host '--- control: no plant ---'
$env:V_SPEED_PLANT_STAGE = ''
$env:V_SPEED_PLANT_S = '0'
python runner.py --subject $subject --src $src --rounds 4 --tag commission-ctrl --only strehl,focus-stack
if ($LASTEXITCODE -ne 0) { throw 'control run failed' }

Write-Host '--- plant 5.0 s on strehl ---'
$env:V_SPEED_PLANT_STAGE = 'strehl'
$env:V_SPEED_PLANT_S = '5.0'
python runner.py --subject $subject --src $src --rounds 4 --tag commission-plant-strehl --only strehl,focus-stack
if ($LASTEXITCODE -ne 0) { throw 'strehl plant run failed' }

Write-Host '--- plant 5.0 s on focus-stack ---'
$env:V_SPEED_PLANT_STAGE = 'focus-stack'
$env:V_SPEED_PLANT_S = '5.0'
python runner.py --subject $subject --src $src --rounds 4 --tag commission-plant-fs --only strehl,focus-stack
if ($LASTEXITCODE -ne 0) { throw 'focus-stack plant run failed' }

$env:V_SPEED_PLANT_STAGE = ''
$env:V_SPEED_PLANT_S = '0'

Write-Host '--- verdict ---'
python commission_verdict.py
exit $LASTEXITCODE
