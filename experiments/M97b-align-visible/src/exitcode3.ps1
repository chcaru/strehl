$ErrorActionPreference = "Continue"

# $LASTEXITCODE is NOT reset by cmdlets. If truncation stops a native command
# before its exit code is recorded, the variable keeps its PREVIOUS value.
# So every arm must be seeded with a KNOWN, WRONG value first, or a stale read
# is indistinguishable from a correct one. My first two probes failed this.

$c = 'for /L %i in (1,1,20000) do @echo LINE%i'

function Seed($v) { cmd /c "exit $v" | Out-Null }

"=== arms that FAIL (true code 1). Seeded to 0 -> a stale read shows 0. ==="
Seed 0; cmd /c "$c & exit 1" | Out-Null
"  seed0  no pipeline                -> $LASTEXITCODE   (expect 1)"
Seed 0; cmd /c "$c & exit 1" | Select-Object -First 3 | Out-Null
"  seed0  | -First 3   (TRUNCATES)   -> $LASTEXITCODE   (0 here = TRAP CONFIRMED)"
Seed 0; cmd /c "$c & exit 1" | Select-String LINE | Select-Object -First 3 | Out-Null
"  seed0  | Select-String | -First 3 -> $LASTEXITCODE   (0 here = TRAP CONFIRMED)"
Seed 0; cmd /c "$c & exit 1" | Select-Object -Last 3 | Out-Null
"  seed0  | -Last 3                  -> $LASTEXITCODE   (expect 1)"
""
"=== converse: arms that SUCCEED (true code 0), seeded to 7 ==="
Seed 7; cmd /c "$c & exit 0" | Out-Null
"  seed7  no pipeline                -> $LASTEXITCODE   (expect 0)"
Seed 7; cmd /c "$c & exit 0" | Select-Object -First 3 | Out-Null
"  seed7  | -First 3   (TRUNCATES)   -> $LASTEXITCODE   (7 here = STALE CONFIRMED)"
""
"=== probe validity check: does Seed actually move the variable? ==="
Seed 0; "  after Seed 0 -> $LASTEXITCODE"
Seed 7; "  after Seed 7 -> $LASTEXITCODE"
"PS $($PSVersionTable.PSVersion)"
