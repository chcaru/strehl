# Characterise the one arm that falsified the quota model.
#
# exit_code_trap2.ps1 ran 14 arms, 5 reps. Thirteen matched the pre-registered
# quota prediction (lost iff N <= lines), including both directions of the exact
# boundary, the 5-line volume test and the 5 ms/line timing test. One did not:
#
#     50 lines, -First 3   ->  1, -1, -1, -1, -1     SPLIT
#
# Reading the true 1 on rep 1 is not the stale-value confound: the pre-clear
# sets 0 before every rep and was verified, so a stale read would be 0.
#
# Two hypotheses, and they are distinguishable:
#   H-warm  It is a first-invocation effect (cold pipeline/process path) and
#           disappears once warm. Prediction: rep 1 anomalous, reps 2..M all -1,
#           and the anomaly does NOT recur later in a long run.
#   H-race  There is a genuine residual race at small N, where the producer can
#           occasionally finish and be reaped before Select-Object reaches its
#           quota. Prediction: the 1s recur at random positions throughout a
#           long run, at a rate that FALLS as N rises toward the line count
#           (larger N = later stop = less chance the process is still mid-flight
#           ... or the opposite; either ordering is informative, a flat rate is
#           evidence against H-race).
#
# This matters beyond bookkeeping: if H-race holds, a `-First` pipeline is
# NON-DETERMINISTIC rather than reliably wrong, which is strictly worse for
# anyone tempted to special-case it -- an arm that passes in testing can fail in
# production. Either way the operative rule is unchanged and reinforced.
#
# Run:  powershell -ExecutionPolicy Bypass -File exit_code_trap3.ps1
$ErrorActionPreference = "Continue"

$REPS = 40
$LINES = 50

$py = Join-Path $env:TEMP "exitprobe_trap3.py"
@'
import sys
lines = int(sys.argv[1])
for i in range(lines):
    print(f"line {i}", flush=True)
sys.exit(1)
'@ | Set-Content -Encoding utf8 $py

# Warm the interpreter and the pipeline path once, uncounted, so that rep 1 of
# the counted run is not itself the cold invocation.
python $py 5 > $null 2>&1

"probe emits $LINES lines, exits 1. $REPS reps per arm. pre-clear verified each rep."
"'1' = true code preserved (ANOMALY for N <= lines). '-1'/'0' = corrupted."
""
$summary = @()
foreach ($n in @(1, 2, 3, 5, 10, 25, 49, 50)) {
    $seq = @()
    foreach ($r in 1..$REPS) {
        cmd /c exit 0
        if ($LASTEXITCODE -ne 0) { throw "pre-clear did not take (N=$n rep=$r)" }
        python $py $LINES 2>&1 | Select-Object -First $n | Out-Null
        $seq += $LASTEXITCODE
    }
    $preserved = @($seq | Where-Object { $_ -eq 1 }).Count
    $positions = @()
    for ($i = 0; $i -lt $seq.Count; $i++) { if ($seq[$i] -eq 1) { $positions += ($i + 1) } }
    $summary += [pscustomobject]@{
        N = $n; Preserved = $preserved; Reps = $REPS
        Rate = [math]::Round(100.0 * $preserved / $REPS, 1)
        Positions = ($positions -join ",")
    }
    "{0,-10} preserved {1,2}/{2}  ({3,5}%)  at rep(s): {4}" -f "-First $n", $preserved, $REPS, ([math]::Round(100.0*$preserved/$REPS,1)), ($positions -join ",")
}

""
"=== VERDICT ==="
$anomalous = @($summary | Where-Object { $_.Preserved -gt 0 })
if ($anomalous.Count -eq 0) {
    "No anomaly reproduced in $REPS reps at any N. The single 1 seen in trap2 was a"
    "one-off first-invocation effect: H-warm supported, H-race unsupported. The quota"
    "model stands, with the caveat that a COLD first invocation can preserve the code."
    exit 0
}
$firstOnly = @($anomalous | Where-Object { $_.Positions -eq "1" })
if ($firstOnly.Count -eq $anomalous.Count) {
    "Every anomaly landed on rep 1 and nowhere else => H-warm. The first invocation"
    "after a cold pipeline path preserves the code; every warm one loses it. The quota"
    "model holds for warm invocations, which is every invocation that matters."
    exit 0
}
"Anomalies recur at scattered rep positions, so this is NOT a first-invocation"
"effect => H-race is supported. `-First` is NON-DETERMINISTIC at small N, which is"
"strictly WORSE than being reliably wrong: a -First pipeline can pass a test and"
"then lose the code in production. Rate vs N:"
$summary | ForEach-Object { "    N={0,-3} {1,5}% preserved" -f $_.N, $_.Rate }
"The operative rule is unchanged and reinforced: never read `$LASTEXITCODE after a"
"pipeline containing -First, at any N, warm or cold."
exit 0
