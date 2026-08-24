# Measure the `$LASTEXITCODE` truncation trap, and the confound that hides it.
#
# M104c-verify reported that `$LASTEXITCODE` can read 0 after a failing command
# when the pipeline truncates with `Select-Object -First N`. My first attempt to
# reproduce it reported all seven arms as 1 and I nearly filed it as
# non-reproducing. That was a false negative from a confound in my own harness:
# `$LASTEXITCODE` retains the PREVIOUS command's value, so against a command
# whose true code is 1, a stale 1 is indistinguishable from a correct read.
#
# This is discipline 706's exact shape -- a control that could never have gone
# red. The pre-clear below is what makes each arm able to fail.
#
# Registered bars:
#   E1  the pre-clear must itself verify, or the arm is discarded
#   E2  `-First` must be shown to FAIL (read 0 on a true-1 command), else this
#       harness has not demonstrated it can detect the trap at all and its
#       "-Last is safe" verdict is worthless
#   E3  every `-Last` arm must read 1
#
# Run:  powershell -File exit_code_trap.ps1
$ErrorActionPreference = "Continue"

$py = Join-Path $env:TEMP "exitprobe_trap.py"
@'
import sys, time
n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for i in range(200):
    print(f"line {i}", flush=True)
    if n: time.sleep(n/1000.0)
sys.exit(1)
'@ | Set-Content -Encoding utf8 $py

$results = @()
function Probe($label, $script, $slow) {
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "E1 FAILED: pre-clear did not take for '$label'" }
    & $script $slow | Out-Null
    $code = $LASTEXITCODE
    $script:results += [pscustomobject]@{ Arm = $label; Code = $code }
    "{0,-42} -> {1}" -f $label, $code
}

"true exit code of the probe command is 1 in every arm below"
""
Probe "fast, no pipeline"    { param($s) python $py $s > $null 2>&1 } 0
Probe "fast, -First 3"       { param($s) python $py $s 2>&1 | Select-Object -First 3 } 0
Probe "fast, -Last 10"       { param($s) python $py $s 2>&1 | Select-Object -Last 10 } 0
Probe "SLOW(5ms), -First 3"  { param($s) python $py $s 2>&1 | Select-Object -First 3 } 5
Probe "SLOW(5ms), -Last 10"  { param($s) python $py $s 2>&1 | Select-Object -Last 10 } 5
Probe "SLOW(5ms), SS|-First 3" { param($s) python $py $s 2>&1 | Select-String "line" | Select-Object -First 3 } 5
Probe "SLOW(5ms), SS|-Last 12" { param($s) python $py $s 2>&1 | Select-String "line" | Select-Object -Last 12 } 5

""
$first = $results | Where-Object { $_.Arm -match '-First' }
$last  = $results | Where-Object { $_.Arm -match '-Last' }
$trapped = @($first | Where-Object { $_.Code -ne 1 })
if ($trapped.Count -eq 0) {
    "E2 FAILED - every -First arm reported the true code 1, so this harness has NOT"
    "           been shown able to detect the trap. Its '-Last is safe' result is"
    "           therefore unearned and must not be quoted."
    exit 2
}
$vals = ($trapped | ForEach-Object { $_.Code } | Sort-Object -Unique) -join ", "
"E2 PASS  $($trapped.Count)/$($first.Count) -First arm(s) MISREPORTED a true code of 1; observed: $vals"
"         NOTE: the corrupted value is host-dependent -- 0 under the agent shell,"
"         -1 under 'powershell -File'. So 'it reads 0' is wrong as a rule: a gate"
"         written as 'if (`$code -ne 0) { fail }' catches -1 but SILENTLY PASSES 0."
"         The only safe rule is that the value is unusable, not that it is 0."
$bad = @($last | Where-Object { $_.Code -ne 1 })
if ($bad.Count -ne 0) { "E3 FAILED - a -Last arm did not read 1"; exit 2 }
"E3 PASS  $($last.Count)/$($last.Count) -Last arms read 1"
""
"RULE: never read `$LASTEXITCODE after a pipeline containing -First."
"      -Last N and Out-String are safe. Capture first, then filter."
exit 0
