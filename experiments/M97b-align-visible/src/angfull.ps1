# M97 -- full angled-ruler comparison on the CORRECTED instrument.
# The first pass of this ran with HALF_WIN=9 / BG_MED=61, both measured wrong
# by angprobe.py, and its treatment numbers are void. Nothing from that run is
# carried forward.
$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = 'utf-8'
$s = "experiments\M97b-align-visible\src\angstraight.py"
$o = "C:\dev\strehl-out\M97"

Write-Host "=== TREATMENT: ALIGNED ==="
python $s measure ALIGNED "$o\angruler-ALIGNED.tif" --json "$o\angF-ALIGNED.json" --overlay "$o\angF-overlay-ALIGNED.png"

Write-Host "=== TREATMENT: ZOOMNULL ==="
python $s measure ZOOMNULL "$o\angruler-ZOOMNULL.tif" --json "$o\angF-ZOOMNULL.json" --overlay "$o\angF-overlay-ZOOMNULL.png"

Write-Host "=== CONTROL placebo: ALIGNED measured again ==="
python $s measure PLACEBO "$o\angruler-ALIGNED.tif" --json "$o\angF-PLACEBO.json"

Write-Host "=== CONTROL translation gain: +3.0 px on ALIGNED ==="
python $s plant "$o\angruler-ALIGNED.tif" --shift 3.0 --json "$o\angF-SHIFT3.json"

Write-Host "=== CONTROL bend response: 2.0 px on ALIGNED ==="
python $s plant "$o\angruler-ALIGNED.tif" --bend 2.0 --json "$o\angF-BENDA2.json"

Write-Host "=== CONTROL bend response: 4.0 px on ALIGNED ==="
python $s plant "$o\angruler-ALIGNED.tif" --bend 4.0 --json "$o\angF-BENDA4.json"

Write-Host "=== CONTROL direction: 4.0 px bend on ZOOMNULL ==="
python $s plant "$o\angruler-ZOOMNULL.tif" --bend 4.0 --json "$o\angF-BENDZ4.json"

Write-Host "=== done ==="
