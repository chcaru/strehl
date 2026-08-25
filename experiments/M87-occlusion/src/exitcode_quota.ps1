# M87 -- is the -First exit-code loss deterministic on quota, or quota-gated
# but racy?  And does the answer depend on the HOST?
#
# The orchestrator has now given two mechanisms:
#   1. "a race, not a count" -- small/fast output finishes first and is safe.
#   2. "deterministic on quota" -- -First N loses the code whenever
#      N <= objects produced, including at 5 lines, with no volume threshold.
#
# My own measurement (12 runs x 6 arms, data/exitcode-repeat.json) is
# consistent with NEITHER as stated: the corrupted-arm count varied 4 to 6 of
# 6 across identical runs, so loss is not deterministic; but the variation was
# concentrated at small n, so it is not simply volume-driven either.
#
# The hypothesis this script tests is that BOTH are partly right:
#   * quota is NECESSARY -- N <= objects is required for Select-Object to
#     throw StopUpstreamCommandsException at all, which is why -First 51 over
#     50 objects is safe;
#   * quota is NOT SUFFICIENT -- the code is only lost if the short-circuit
#     lands while the native process is still running, so a process that has
#     already exited leaves a correct code behind.
#
# If that is right, ORCH's -First 51 boundary datum and my run-to-run
# variation are both real and neither mechanism alone explains the pair.
#
# It also tests the HOST, because our two probes did not share one: mine ran
# under `powershell -NoProfile -File`, theirs in the agent shell.  ORCH
# reports the corrupted value differs by host (0 vs -1), so the loss RATE may
# differ too -- which would make both measurements correct in their own
# context and would fully explain the disagreement.
#
# No `exit` statement anywhere: this script must be safe to dot-source into
# the agent shell so it can be measured in-process as well as in a child.

param(
    [int]$Reps = 40,
    [string]$Label = 'child-host'
)

$ErrorActionPreference = 'Stop'

$emit = Join-Path $env:TEMP 'm87_quota_emit.py'
@(
    'import sys'
    'n = int(sys.argv[1])'
    'for i in range(n):'
    '    print("line %d" % i)'
    'sys.exit(1)'
) -join "`r`n" | Set-Content -Path $emit -Encoding ascii

# commission the emitter in this host before trusting any arm
cmd /c exit 0
& python $emit 3 > $null 2>&1
if ($LASTEXITCODE -ne 1) { throw "emitter does not exit 1 here (read $LASTEXITCODE)" }

# lines, mode, N   -- ORCH's arms first, then mine
$specs = @(
    @{ n = 50;   mode = 'First'; k = 3 }
    @{ n = 50;   mode = 'First'; k = 49 }
    @{ n = 50;   mode = 'First'; k = 50 }
    @{ n = 50;   mode = 'First'; k = 51 }
    @{ n = 5;    mode = 'First'; k = 3 }
    @{ n = 50;   mode = 'Last';  k = 3 }
    @{ n = 10;   mode = 'First'; k = 3 }
    @{ n = 200;  mode = 'First'; k = 3 }
    @{ n = 5000; mode = 'First'; k = 3 }
)

$TRUE_CODE = 1
$out = @()

foreach ($s in $specs) {
    $codes = @()
    for ($r = 1; $r -le $Reps; $r++) {
        cmd /c exit 0
        if ($LASTEXITCODE -ne 0) { throw "PRE-CLEAR FAILED ($($s.n)/$($s.mode)/$($s.k))" }
        if ($s.mode -eq 'First') {
            $null = & python $emit $s.n 2>&1 | Select-Object -First $s.k
        } else {
            $null = & python $emit $s.n 2>&1 | Select-Object -Last $s.k
        }
        $codes += $LASTEXITCODE
    }
    $lost = @($codes | Where-Object { $_ -ne $TRUE_CODE }).Count
    $vals = @($codes | Sort-Object -Unique)
    # quota model: Select-Object -First k short-circuits iff k <= objects
    $quotaPredictsLoss = ($s.mode -eq 'First') -and ($s.k -le $s.n)
    $out += [pscustomobject]@{
        label        = $Label
        lines        = $s.n
        mode         = $s.mode
        k            = $s.k
        reps         = $Reps
        lost         = $lost
        lost_pct     = [math]::Round(100.0 * $lost / $Reps, 1)
        values       = $vals
        quota_pred   = $quotaPredictsLoss
        quota_agrees = ($quotaPredictsLoss -and $lost -eq $Reps) -or
                       ((-not $quotaPredictsLoss) -and $lost -eq 0)
    }
}

$out | Format-Table label, lines, mode, k, reps, lost, lost_pct, quota_pred, quota_agrees -AutoSize |
    Out-String -Width 140 | Write-Output

$disagree = @($out | Where-Object { -not $_.quota_agrees })
Write-Output "host: $Label   PSVersion $($PSVersionTable.PSVersion)"
Write-Output "arms where the strict quota model FAILS: $($disagree.Count) of $($out.Count)"
foreach ($d in $disagree) {
    Write-Output ("  {0} lines, -{1} {2}: quota predicts {3}, observed {4}/{5} lost, values {6}" -f `
        $d.lines, $d.mode, $d.k, $(if ($d.quota_pred) { 'ALWAYS lost' } else { 'never lost' }), `
        $d.lost, $d.reps, ($d.values -join '/'))
}

$dest = Join-Path (Split-Path $PSScriptRoot -Parent) "data\exitcode-quota-$Label.json"
$out | ConvertTo-Json -Depth 4 | Set-Content -Path $dest -Encoding utf8
Write-Output "wrote $dest"
