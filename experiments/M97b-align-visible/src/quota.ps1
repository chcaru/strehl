# Does the QUOTA rule hold for both producer kinds?
#
# Orchestrator: "-First N loses the exit code whenever N <= objects produced",
# deterministic, 50 lines / -First 50 lost, -First 51 preserved.
# M97 measured a cmd builtin loop preserving at N=3 for 50..20000 lines, 40/40.
# Both cannot be general. This crosses the boundary ladder with both producers.
#
# SEED 9, deliberately: it is neither the true code (1), nor the agent-shell
# corruption (0), nor the -File corruption (-1). Seeding to 0 -- as the ORCH
# harness does -- makes "never set" and "corrupted to 0" the same observation
# in the host where the corruption IS 0.

$ErrorActionPreference = "Continue"
$py = "C:\dev\strehl-out\M97\producer2.py"
$REPS = 5
$LINES = 50

function Preclear {
    cmd /c "exit 9" | Out-Null
    if ($LASTEXITCODE -ne 9) { throw "PRECLEAR FAILED - probe not connected" }
}

function Row($kind, $n) {
    $codes = @()
    for ($i = 0; $i -lt $REPS; $i++) {
        Preclear
        if ($kind -eq "cmd") {
            cmd /c "for /L %i in (1,1,$LINES) do @echo LINE%i & exit 1" | Select-Object -First $n | Out-Null
        } else {
            python $py $LINES 0 1 | Select-Object -First $n | Out-Null
        }
        $codes += $LASTEXITCODE
    }
    $u = ($codes | Sort-Object -Unique) -join ","
    $v = switch ($u) {
        "1"  { "preserved" }
        "-1" { "LOST(-1) " }
        "0"  { "LOST(0)  " }
        "9"  { "NEVER SET" }
        default { "MIXED    " }
    }
    "  {0,-7} {1} lines | -First {2,-4} -> {3} [{4}]" -f $kind, $LINES, $n, $v, ($codes -join " ")
}

"true exit code 1; $LINES lines produced; seed 9; $REPS reps"
"quota rule predicts: LOST for N<=50, preserved for N>=51"
""
foreach ($k in @("cmd", "python")) {
    foreach ($n in @(3, 49, 50, 51, 99)) { Row $k $n }
    ""
}
"host: powershell -File   PS $($PSVersionTable.PSVersion)"
