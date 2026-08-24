# Measure the `$LASTEXITCODE` truncation trap, its mechanism, and the confound
# that hid the mechanism from two independent agents.
#
# HISTORY, because it is the point of this file:
#   M104c-verify reported `$LASTEXITCODE` reading 0 after a failing command when
#   the pipeline truncates with `Select-Object -First N`. My first reproduction
#   reported all seven arms safe -- a false negative, because `$LASTEXITCODE`
#   retains the PREVIOUS command's value and on a true-1 probe a stale 1 is
#   indistinguishable from a correct read. I added the pre-clear and confirmed
#   the trap. I then folded the mechanism as "a race, not a count", on the
#   strength of an M104c arm where 50 lines through `-First 3` reported the true
#   1. That arm was itself un-pre-cleared. It was the same confound, one level
#   up, and it produced a WRONG MECHANISM that I broadcast to seven agents.
#
#   Pre-cleared, the mechanism is not a race and does not depend on volume or
#   timing. It is a QUOTA: `-First N` loses the exit code whenever
#   `N <= the number of objects produced`, and preserves it when N exceeds them.
#
# The original harness could not have discovered this: every `-First` arm used
# N=3 against a fixed 200-line probe, so N <= count held in all of them and the
# quota boundary was never approached. It measured the trap correctly and was
# structurally blind to its cause. That is why the arm table below varies N
# across the boundary and varies the line count by 10x.
#
# Registered bars:
#   E1  the pre-clear must itself verify, or the arm is discarded
#   E2  at least one `-First` arm must be shown to MISREPORT a true-1 command,
#       else this harness has not demonstrated it can detect the trap at all and
#       its "-Last is safe" verdict is unearned. Any wrong value counts, not
#       just 0 -- the corrupted value is host-dependent.
#   E3  every `-Last` / no-pipeline arm must read the true 1
#   E4  MECHANISM. Every arm's outcome must match the quota prediction declared
#       in the table BEFORE the run: lost iff `N <= lines`. A single mismatch
#       falsifies the quota model, and that is a finding, not a bug to paper
#       over. E4 is what makes this harness able to kill its own thesis.
#   E5  DETERMINISM. Each arm must be unanimous across its reps. A split arm
#       means the mechanism has a stochastic component after all, which would
#       partially revive the race theory.
#
# Run:  powershell -ExecutionPolicy Bypass -File exit_code_trap.ps1
$ErrorActionPreference = "Continue"

$REPS = 5

$py = Join-Path $env:TEMP "exitprobe_trap.py"
@'
import sys, time
lines = int(sys.argv[1])
delay = float(sys.argv[2]) / 1000.0
for i in range(lines):
    print(f"line {i}", flush=True)
    if delay: time.sleep(delay)
sys.exit(1)
'@ | Set-Content -Encoding utf8 $py

# Arms. `Pred` is the pre-registered prediction under the quota model and is
# declared here, before any measurement, so E4 cannot be fitted after the fact.
#   LOST      = the exit code is expected to be corrupted
#   PRESERVED = the true code 1 is expected to survive
$arms = @(
    @{ Label = "50 lines, no pipeline";      Lines = 50; Delay = 0; N = 0;  Kind = "none";  Pred = "PRESERVED" }
    @{ Label = "50 lines, -First 3";         Lines = 50; Delay = 0; N = 3;  Kind = "first"; Pred = "LOST" }
    @{ Label = "50 lines, -First 49";        Lines = 50; Delay = 0; N = 49; Kind = "first"; Pred = "LOST" }
    @{ Label = "50 lines, -First 50 (exact)"; Lines = 50; Delay = 0; N = 50; Kind = "first"; Pred = "LOST" }
    @{ Label = "50 lines, -First 51";        Lines = 50; Delay = 0; N = 51; Kind = "first"; Pred = "PRESERVED" }
    @{ Label = "50 lines, -First 99";        Lines = 50; Delay = 0; N = 99; Kind = "first"; Pred = "PRESERVED" }
    # The volume test. If "small output finishes first and reports correctly"
    # were true, this arm would be PRESERVED. The quota model says LOST.
    @{ Label = "5 lines, -First 3";          Lines = 5;  Delay = 0; N = 3;  Kind = "first"; Pred = "LOST" }
    @{ Label = "5 lines, -First 6";          Lines = 5;  Delay = 0; N = 6;  Kind = "first"; Pred = "PRESERVED" }
    # The timing test. Under a race, a 5 ms per-line delay changes everything.
    # Under a quota it changes nothing.
    @{ Label = "50 lines SLOW(5ms), -First 3"; Lines = 50; Delay = 5; N = 3; Kind = "first"; Pred = "LOST" }
    @{ Label = "50 lines SLOW(5ms), -First 99"; Lines = 50; Delay = 5; N = 99; Kind = "first"; Pred = "PRESERVED" }
    @{ Label = "50 lines, SS | -First 3";    Lines = 50; Delay = 0; N = 3;  Kind = "ss";    Pred = "LOST" }
    @{ Label = "50 lines, -Last 3";          Lines = 50; Delay = 0; N = 3;  Kind = "last";  Pred = "PRESERVED" }
    @{ Label = "50 lines, -Last 99";         Lines = 50; Delay = 0; N = 99; Kind = "last";  Pred = "PRESERVED" }
    @{ Label = "50 lines, Out-String";       Lines = 50; Delay = 0; N = 0;  Kind = "outstr"; Pred = "PRESERVED" }
)

function Invoke-Arm($arm) {
    # E1: pre-clear, and verify the pre-clear took. Without this the whole run
    # is worthless -- see the header.
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "E1 FAILED: pre-clear did not take for '$($arm.Label)'" }
    $l = $arm.Lines; $d = $arm.Delay; $n = $arm.N
    switch ($arm.Kind) {
        "none"   { python $py $l $d > $null 2>&1 }
        "first"  { python $py $l $d 2>&1 | Select-Object -First $n | Out-Null }
        "last"   { python $py $l $d 2>&1 | Select-Object -Last $n | Out-Null }
        "ss"     { python $py $l $d 2>&1 | Select-String "line" | Select-Object -First $n | Out-Null }
        "outstr" { python $py $l $d 2>&1 | Out-String | Out-Null }
    }
    return $LASTEXITCODE
}

"true exit code of the probe command is 1 in every arm below; $REPS reps each"
"prediction column was written before the run (quota model: LOST iff N <= lines)"
""
"{0,-32} {1,-10} {2,-14} {3,-10} {4}" -f "ARM", "PRED", "CODES", "OBSERVED", "E4"
$rows = @()
foreach ($arm in $arms) {
    $codes = @(1..$REPS | ForEach-Object { Invoke-Arm $arm })
    $uniq = @($codes | Sort-Object -Unique)
    $unanimous = ($uniq.Count -eq 1)
    $observed = if ($unanimous -and $uniq[0] -eq 1) { "PRESERVED" }
                elseif ($unanimous) { "LOST" }
                else { "SPLIT" }
    $ok = if ($observed -eq $arm.Pred) { "ok" } else { "MISMATCH" }
    $rows += [pscustomobject]@{
        Label = $arm.Label; Pred = $arm.Pred; Observed = $observed
        Codes = ($codes -join ","); Unanimous = $unanimous; Match = ($observed -eq $arm.Pred)
    }
    "{0,-32} {1,-10} {2,-14} {3,-10} {4}" -f $arm.Label, $arm.Pred, ($codes -join ","), $observed, $ok
}
""

$fails = 0

# E2 -- can this harness detect the trap at all?
$firstArms = @($rows | Where-Object { $_.Label -match '-First|SS \|' })
$trapped = @($firstArms | Where-Object { $_.Observed -eq "LOST" })
if ($trapped.Count -eq 0) {
    "E2 FAILED - no -First arm misreported, so this harness has NOT been shown able"
    "           to detect the trap. Its '-Last is safe' result is unearned."
    $fails++
} else {
    $vals = ($trapped | ForEach-Object { ($_.Codes -split ",")[0] } | Sort-Object -Unique) -join ", "
    "E2 PASS  $($trapped.Count)/$($firstArms.Count) -First arm(s) MISREPORTED a true 1; observed: $vals"
    "         The corrupted value is HOST-DEPENDENT: 0 under the agent shell, -1 under"
    "         'powershell -File'. So a gate written 'if (`$code -ne 0) { fail }' catches"
    "         -1 and SILENTLY PASSES 0. The value is unusable; it is not 'zero'."
}

# E3 -- the safe shapes must be safe.
$safeArms = @($rows | Where-Object { $_.Label -match '-Last|no pipeline|Out-String' })
$bad = @($safeArms | Where-Object { $_.Observed -ne "PRESERVED" })
if ($bad.Count -ne 0) {
    "E3 FAILED - a -Last/no-pipeline/Out-String arm did not read the true 1: $(($bad | ForEach-Object { $_.Label }) -join '; ')"
    $fails++
} else {
    "E3 PASS  $($safeArms.Count)/$($safeArms.Count) drain-the-stream arms read the true 1"
}

# E5 -- determinism. Checked before E4 because a SPLIT arm makes E4 unreadable.
$split = @($rows | Where-Object { -not $_.Unanimous })
if ($split.Count -ne 0) {
    "E5 FAILED - $($split.Count) arm(s) were not unanimous across $REPS reps:"
    $split | ForEach-Object { "           $($_.Label): $($_.Codes)" }
    "           A stochastic component would PARTIALLY REVIVE the race theory."
    $fails++
} else {
    "E5 PASS  all $($rows.Count) arms unanimous across $REPS reps -- deterministic"
}

# E4 -- the mechanism itself.
$mismatch = @($rows | Where-Object { -not $_.Match })
if ($mismatch.Count -ne 0) {
    "E4 FAILED - the quota model mispredicted $($mismatch.Count) arm(s):"
    $mismatch | ForEach-Object { "           $($_.Label): predicted $($_.Pred), observed $($_.Observed)" }
    "           This FALSIFIES 'lost iff N <= lines'. Do not patch the prediction to"
    "           match -- report it. The corpus has already carried two wrong"
    "           mechanisms for this defect and a third would be worse than none."
    $fails++
} else {
    "E4 PASS  all $($rows.Count) arms matched the pre-registered quota prediction"
    "         lost iff N <= lines. Confirmed at the EXACT boundary (-First 50 loses,"
    "         -First 51 preserves), on 5-line output (no volume threshold exists),"
    "         and under a 5 ms/line delay (timing is irrelevant -- not a race)."
}

""
if ($fails -ne 0) { "RESULT: $fails bar(s) RED"; exit 2 }
"RESULT: all bars green"
"RULE: never read `$LASTEXITCODE after a pipeline containing -First."
"      -Last N and Out-String are safe. Capture first, then filter:"
"          `$out = & `$exe ... 2>&1; `$code = `$LASTEXITCODE"
"          `$out | Select-Object -First 5; if (`$code -ne 0) { throw }"
exit 0
