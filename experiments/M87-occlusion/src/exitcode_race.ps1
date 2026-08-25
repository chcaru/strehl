# M87 -- CAUSAL test of the exit-code loss mechanism on Windows PowerShell 5.1.
#
# What the 2x2 (data/exitcode-quota-*.json) already established, 1440 obs:
#   * quota is NECESSARY in BOTH engines -- -First 51 over 50 objects and
#     -Last 3 lose the code 0/40 times in all four hosts.
#   * quota is SUFFICIENT on PowerShell 7.6.5 -- 720/720 observations agree
#     with the strict model, in-process AND as a child.
#   * quota is NOT sufficient on Windows PowerShell 5.1.26100.9168 -- 6 of 9
#     arms lose the code only 50-100% of the time, in-process AND as a child.
#   * the ENGINE is the whole variable; process style contributes nothing.
#
# So the only thing left unexplained is the 5.1 variation.  The race
# hypothesis says the code is lost iff StopUpstreamCommandsException lands
# while the native process is STILL RUNNING; if the process has already
# exited, 5.1 has already harvested its code and the short-circuit cannot
# take it away.
#
# That hypothesis makes a manipulable prediction, because "still running" is
# something I can control directly: make the emitter SLEEP after its last
# line but before it exits.  A sleeping process is still running, so the
# short-circuit must land inside it.
#
# REGISTERED PREDICTIONS, written before the data exist:
#   P1  On 5.1, loss rate rises with sleep and reaches 100% at 300 ms, for
#       BOTH 5-line and 50-line output.  (5 lines / sleep 0 sits at 60.0%
#       pooled today, so this is a large registered move, not a nudge.)
#   P2  On 7.6.5, sleep changes nothing: 100% at every sleep.
#   P3  NEGATIVE CONTROL, must hold in both engines and at every sleep:
#       -First 51 over 50 objects stays 0 lost.  If sleeping makes a
#       NON-quota arm start losing, the manipulation is not selective and
#       nothing else in this script may be believed.
#   P4  NEGATIVE CONTROL: -Last 3 stays 0 lost at every sleep.
#
# If P1 fails -- if sleep does not move the 5.1 rate -- the race model is
# WRONG and the 5.1 variation is something else (scheduler jitter, console
# buffering), and I will report it as unexplained rather than narrate a
# mechanism I did not measure.
#
# No `exit` statement: safe to dot-source.

param(
    [int]$Reps = 60,
    [string]$Label = 'ps51-child'
)

$ErrorActionPreference = 'Stop'

# emitter: print n lines, flush, sleep s seconds, then exit 1
$emit = Join-Path $env:TEMP 'm87_race_emit.py'
@(
    'import sys, time'
    'n = int(sys.argv[1])'
    's = float(sys.argv[2])'
    'for i in range(n):'
    '    print("line %d" % i)'
    'sys.stdout.flush()'
    'if s > 0:'
    '    time.sleep(s)'
    'sys.exit(1)'
) -join "`r`n" | Set-Content -Path $emit -Encoding ascii

cmd /c exit 0
& python $emit 3 0 > $null 2>&1
if ($LASTEXITCODE -ne 1) { throw "emitter does not exit 1 here (read $LASTEXITCODE)" }
cmd /c exit 0
& python $emit 3 0.05 > $null 2>&1
if ($LASTEXITCODE -ne 1) { throw "sleeping emitter does not exit 1 here (read $LASTEXITCODE)" }

$specs = @()
foreach ($s in @(0.0, 0.05, 0.3)) {
    $specs += @{ n = 5;  mode = 'First'; k = 3;  sleep = $s; ctl = $false }
    $specs += @{ n = 50; mode = 'First'; k = 3;  sleep = $s; ctl = $false }
    $specs += @{ n = 50; mode = 'First'; k = 51; sleep = $s; ctl = $true  }
    $specs += @{ n = 50; mode = 'Last';  k = 3;  sleep = $s; ctl = $true  }
}

$TRUE_CODE = 1
$out = @()

foreach ($sp in $specs) {
    $codes = @()
    for ($r = 1; $r -le $Reps; $r++) {
        cmd /c exit 0
        if ($LASTEXITCODE -ne 0) { throw "PRE-CLEAR FAILED ($($sp.n)/$($sp.k)/$($sp.sleep))" }
        if ($sp.mode -eq 'First') {
            $null = & python $emit $sp.n $sp.sleep 2>&1 | Select-Object -First $sp.k
        } else {
            $null = & python $emit $sp.n $sp.sleep 2>&1 | Select-Object -Last $sp.k
        }
        $codes += $LASTEXITCODE
    }
    $lost = @($codes | Where-Object { $_ -ne $TRUE_CODE }).Count
    $out += [pscustomobject]@{
        label    = $Label
        psver    = $PSVersionTable.PSVersion.ToString()
        lines    = $sp.n
        mode     = $sp.mode
        k        = $sp.k
        sleep_s  = $sp.sleep
        is_ctl   = $sp.ctl
        reps     = $Reps
        lost     = $lost
        lost_pct = [math]::Round(100.0 * $lost / $Reps, 2)
        values   = @($codes | Sort-Object -Unique)
    }
}

$out | Format-Table label, psver, lines, mode, k, sleep_s, is_ctl, reps, lost, lost_pct -AutoSize |
    Out-String -Width 160 | Write-Output

$ctlBad = @($out | Where-Object { $_.is_ctl -and $_.lost -ne 0 })
if ($ctlBad.Count -gt 0) {
    Write-Output "NEGATIVE CONTROL BROKEN in $($ctlBad.Count) arm(s) -- P3/P4 failed, believe nothing else here"
} else {
    Write-Output "negative controls held: -First 51 and -Last 3 lost 0/$Reps at every sleep (P3, P4 PASS)"
}

$dest = Join-Path (Split-Path $PSScriptRoot -Parent) "data\exitcode-race-$Label.json"
$out | ConvertTo-Json -Depth 4 | Set-Content -Path $dest -Encoding utf8
Write-Output "wrote $dest"
