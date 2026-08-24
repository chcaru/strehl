# Rule out the producer being a cmd builtin. A real .exe writing to a pipe
# buffers differently, and a SLOW producer guarantees the -First short-circuit
# lands while the process is still running -- which is the stated mechanism.
$ErrorActionPreference = "Continue"
$py = "C:\dev\strehl-out\M97\producer.py"
$REPS = 5

function Preclear {
    cmd /c "exit 0" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "PRECLEAR FAILED - probe is not connected" }
}

function Cell($label, $n, $delay, $shape) {
    $codes = @()
    for ($i = 0; $i -lt $REPS; $i++) {
        Preclear
        switch ($shape) {
            "first" { python $py $n $delay | Select-Object -First 3 | Out-Null }
            "last"  { python $py $n $delay | Select-Object -Last 3  | Out-Null }
            "none"  { python $py $n $delay | Out-Null }
        }
        $codes += $LASTEXITCODE
    }
    $u = ($codes | Sort-Object -Unique) -join ","
    $v = if ($u -eq "1") { "safe " } elseif ($u -eq "0") { "TRAP " } else { "RACE!" }
    "{0,-34} {1} reads [{2}]" -f $label, $v, ($codes -join " ")
}

"python producer, true exit code 1, $REPS reps, pre-cleared to 0 each rep"
""
Cell "200 lines, no delay, -First 3"      200   0     "first"
Cell "20000 lines, no delay, -First 3"    20000 0     "first"
Cell "200 lines, 10ms/line, -First 3"     200   0.01  "first"
Cell "200 lines, 10ms/line, no filter"    200   0.01  "none"
Cell "200 lines, 10ms/line, -Last 3"      200   0.01  "last"
""
"PS $($PSVersionTable.PSVersion)   python $(python --version 2>&1)"
