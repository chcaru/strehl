# Is the $LASTEXITCODE truncation trap a RACE, and is it volume-dependent?
#
# Orchestrator measured 200 lines -> 0 (trap) and 20000 lines on stderr -> 1.
# I measured 20000 lines on stdout -> 1, seeded. If more output means less
# exposure, the stated mechanism is not the mechanism.
#
# A race must be NON-DETERMINISTIC. So each cell is run 5 times and I report the
# spread, not one draw. A cell that is 5/5 identical is evidence against a race.

$ErrorActionPreference = "Continue"
$REPS = 5

function Preclear {
    cmd /c "exit 0" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "PRECLEAR FAILED - probe is not connected" }
}

function Cell($n, $redirect, $shape) {
    $codes = @()
    for ($i = 0; $i -lt $REPS; $i++) {
        Preclear
        $prod = "for /L %i in (1,1,$n) do @echo LINE%i"
        if ($redirect) {
            switch ($shape) {
                "first" { cmd /c "$prod & exit 1" 2>&1 | Select-Object -First 3 | Out-Null }
                "last"  { cmd /c "$prod & exit 1" 2>&1 | Select-Object -Last 3  | Out-Null }
            }
        } else {
            switch ($shape) {
                "first" { cmd /c "$prod & exit 1" | Select-Object -First 3 | Out-Null }
                "last"  { cmd /c "$prod & exit 1" | Select-Object -Last 3  | Out-Null }
            }
        }
        $codes += $LASTEXITCODE
    }
    $u = ($codes | Sort-Object -Unique) -join ","
    $verdict = if ($u -eq "1") { "safe   " } elseif ($u -eq "0") { "TRAP   " } else { "RACE!  " }
    "{0,-6} {1,-8} {2,-6} {3} reads [{4}]" -f $n, $(if ($redirect) { "2>&1" } else { "stdout" }), $shape, $verdict, ($codes -join " ")
}

"true exit code is 1 in every cell; $REPS reps each; pre-cleared to 0 before each rep"
"a cell reading [1 1 1 1 1] is SAFE, [0 0 0 0 0] is the TRAP, anything mixed is a RACE"
""
foreach ($n in @(50, 200, 2000, 20000)) {
    Cell $n $false "first"
}
""
foreach ($n in @(50, 200, 2000, 20000)) {
    Cell $n $true "first"
}
""
"-Last control (must never trap, by construction):"
Cell 20000 $false "last"
Cell 20000 $true  "last"
""
"PS $($PSVersionTable.PSVersion)"
