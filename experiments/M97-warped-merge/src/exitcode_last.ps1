# NOTE: this file is deliberately ASCII-only. Windows PowerShell 5.1 reads a
# .ps1 without a BOM as ANSI, so a non-ASCII character inside a string literal
# is a hard parse error there while running fine on pwsh 7.
#
# M97 -- does the $LASTEXITCODE hazard apply to `Select-Object -Last`, or only
# to `-First`?
#
# ORCH fact 1490 (measured by M87): a truncated pipeline leaves $LASTEXITCODE
# NOT UPDATED, so it retains the previous command's code -- false GREEN when
# primed by success, false RED when primed by failure.
#
# The mechanism ORCH gives is that the pipeline is cut short before the process
# is reaped. If that is the mechanism, then `-Last N` should be SAFE, because
# it cannot know the last N until the stream ends and therefore cannot
# terminate the upstream early. That is a prediction, and this measures it.
#
# Priming is deliberate in both directions, because a plausible-looking code is
# not evidence the read was live.

$ErrorActionPreference = "Continue"
$emit = Join-Path $PSScriptRoot "emit.py"
$LINES = 40000

function Probe {
    param([int]$Prime, [int]$True_, [string]$Mode)

    # Prime $LASTEXITCODE with a known value, untruncated so it is definitely live.
    & python $emit 1 $Prime | Out-Null
    $primed = $LASTEXITCODE

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    switch ($Mode) {
        "first" { & python $emit $LINES $True_ 2>&1 | Select-String 'Error' | Select-Object -First 3 | Out-Null }
        "last"  { & python $emit $LINES $True_ 2>&1 | Select-String 'Error' | Select-Object -Last 3  | Out-Null }
        "none"  { & python $emit $LINES $True_ 2>&1 | Out-Null }
    }
    $read = $LASTEXITCODE
    $sw.Stop()

    $stale = ($read -eq $primed) -and ($primed -ne $True_)
    $verdict = if ($read -eq $True_) { "LIVE" } elseif ($stale) { "STALE" } else { "OTHER($read)" }
    "{0,-6} prime={1} true={2} | primed_read={3} read={4} | {5,-10} {6,6:N2}s" -f `
        $Mode, $Prime, $True_, $primed, $read, $verdict, $sw.Elapsed.TotalSeconds
}

"PowerShell $($PSVersionTable.PSVersion)  lines=$LINES"
""
"CONTROL -- untruncated pipeline must read LIVE in both directions"
Probe -Prime 0 -True_ 1 -Mode "none"
Probe -Prime 1 -True_ 0 -Mode "none"
""
"-First -- ORCH fact 1490 predicts STALE in both directions"
Probe -Prime 0 -True_ 1 -Mode "first"
Probe -Prime 1 -True_ 0 -Mode "first"
""
"-Last -- cannot terminate the upstream early; predicts LIVE"
Probe -Prime 0 -True_ 1 -Mode "last"
Probe -Prime 1 -True_ 0 -Mode "last"
