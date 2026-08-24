# Quota-vs-race boundary, REDONE with literal pipelines after the scriptblock
# indirection was shown to destroy the phenomenon (diagnose_harness.ps1: FORM A/C = 0, FORM B = 1).
# No indirection anywhere below. Every pipeline is written out longhand.

function Preclear {
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "preclear failed" }
}

$dir = 'C:\dev\strehl-out\M107-chroma\verify'
Set-Content -Path "$dir\q50.py" -Value @("import sys", "for i in range(50): print('x'*60)", "sys.exit(1)")
Set-Content -Path "$dir\q5.py"  -Value @("import sys", "for i in range(5): print('x'*60)",  "sys.exit(1)")
$p50 = "$dir\q50.py"
$p5  = "$dir\q5.py"

"true exit code is 1 everywhere; pre-cleared to 0 before each rep; 5 reps"
"literal pipelines only -- no scriptblock indirection"
""
"--- THE BOUNDARY at fixed 50-line volume: quota predicts flip between 50 and 51 ---"

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Select-Object -First 49 | Out-Null; $r += $LASTEXITCODE }
"50 lines | -First 49        -> {0}" -f ($r -join ',')

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Select-Object -First 50 | Out-Null; $r += $LASTEXITCODE }
"50 lines | -First 50 EXACT  -> {0}" -f ($r -join ',')

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Select-Object -First 51 | Out-Null; $r += $LASTEXITCODE }
"50 lines | -First 51        -> {0}" -f ($r -join ',')

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Select-Object -First 99 | Out-Null; $r += $LASTEXITCODE }
"50 lines | -First 99        -> {0}" -f ($r -join ',')

""
"--- VOLUME: race predicted small/fast output is safe ---"

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p5 2>&1 | Select-Object -First 3 | Out-Null; $r += $LASTEXITCODE }
"5 lines  | -First 3         -> {0}" -f ($r -join ',')

""
"--- the shape my own cargo-test gate used ---"

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Select-Object -Last 25 | Out-Null; $r += $LASTEXITCODE }
"50 lines | -Last 25         -> {0}" -f ($r -join ',')

$r = @(); for ($i=0; $i -lt 5; $i++) { Preclear; python $p50 2>&1 | Out-String | Out-Null; $r += $LASTEXITCODE }
"50 lines | Out-String       -> {0}" -f ($r -join ',')
