# THE DECISIVE QUESTION.
#
# The stated consequence is: "this confound produces false negatives only ...
# a truncation artifact cannot invent a nonzero." But the corrupted value on a
# real .exe is -1 (PowerShell KILLS the child), not 0. If a SUCCEEDING command
# also reads -1 through -First, then truncation manufactures a failure from a
# success, and any gate of the form `if ($code -ne 0) { throw }` can be turned
# RED by a purely cosmetic output filter. That is the opposite of the warning.

$ErrorActionPreference = "Continue"
$py = "C:\dev\strehl-out\M97\producer2.py"
$REPS = 5

function Preclear($want) {
    cmd /c "exit $want" | Out-Null
    if ($LASTEXITCODE -ne $want) { throw "PRECLEAR FAILED - probe is not connected" }
}

function Cell($label, $n, $delay, $true_code, $shape, $seed) {
    $codes = @()
    for ($i = 0; $i -lt $REPS; $i++) {
        Preclear $seed
        switch ($shape) {
            "first" { python $py $n $delay $true_code | Select-Object -First 3 | Out-Null }
            "none"  { python $py $n $delay $true_code | Out-Null }
        }
        $codes += $LASTEXITCODE
    }
    "{0,-46} reads [{1}]" -f $label, ($codes -join " ")
}

"pre-clear seeds the variable to a value that is NOT the answer, so a"
"failure-to-set is visible rather than masked."
""
"--- command that SUCCEEDS (true exit code 0), seeded to 9 ---"
Cell "200 lines, exit 0, no filter"        200 0    0 "none"  9
Cell "200 lines, exit 0, -First 3"         200 0    0 "first" 9
Cell "200 lines, exit 0, 10ms/line, -First 3" 200 0.01 0 "first" 9
""
"--- command that FAILS (true exit code 1), seeded to 9 ---"
Cell "200 lines, exit 1, no filter"        200 0    1 "none"  9
Cell "200 lines, exit 1, -First 3"         200 0    1 "first" 9
""
"reading 0  on a SUCCEEDING truncated arm = gate stays green (harmless)"
"reading -1 on a SUCCEEDING truncated arm = TRUNCATION INVENTED A FAILURE"
""
"PS $($PSVersionTable.PSVersion)"
