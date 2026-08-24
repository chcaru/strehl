# M97 -- run the angled-ruler straightness instrument over both arms and all
# controls. Sequential on purpose: each run peaks at ~1.5 GB and there is no
# gain from fighting myself for memory.
$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = 'utf-8'
$src = "experiments\M97b-align-visible\src\angstraight.py"
$out = "C:\dev\strehl-out\M97"

Write-Host "=== TREATMENT: ALIGNED ==="
python $src measure ALIGNED "$out\angruler-ALIGNED.tif" --json "$out\angS-ALIGNED.json" --overlay "$out\angS-overlay-ALIGNED.png"

Write-Host "=== TREATMENT: ZOOMNULL ==="
python $src measure ZOOMNULL "$out\angruler-ZOOMNULL.tif" --json "$out\angS-ZOOMNULL.json" --overlay "$out\angS-overlay-ZOOMNULL.png"

Write-Host "=== CONTROL: placebo (ALIGNED measured a second time) ==="
python $src measure PLACEBO "$out\angruler-ALIGNED.tif" --json "$out\angS-PLACEBO.json"

Write-Host "=== CONTROL: bend plant 0.5 px on ALIGNED ==="
python $src plant "$out\angruler-ALIGNED.tif" --bend 0.5 --json "$out\angS-BEND05.json"

Write-Host "=== CONTROL: bend plant 2.0 px on ALIGNED ==="
python $src plant "$out\angruler-ALIGNED.tif" --bend 2.0 --json "$out\angS-BEND20.json"

Write-Host "=== CONTROL: bend plant 2.0 px on ZOOMNULL (direction) ==="
python $src plant "$out\angruler-ZOOMNULL.tif" --bend 2.0 --json "$out\angS-BEND20Z.json"

Write-Host "=== done ==="
