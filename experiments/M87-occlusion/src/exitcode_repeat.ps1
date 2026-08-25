# M87 -- drive exitcode_probe.ps1 repeatedly and aggregate.
#
# One run of the probe cannot support a claim about a RACE.  The orchestrator's
# corrected framing says the exit code is lost only when the short-circuit
# lands while the native process is still running, which predicts that
# identical runs disagree.  A count model predicts they do not.  Repeating the
# probe is therefore the measurement that discriminates the two, and it is the
# only reason this driver exists.
#
# It writes data/exitcode-repeat.json, which verify_s34.py re-derives from.

param([int]$Repeat = 8)

$ErrorActionPreference = 'Stop'

$probe = Join-Path $PSScriptRoot 'exitcode_probe.ps1'
$single = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\exitcode-probe.json'

$runs = @()
for ($i = 1; $i -le $Repeat; $i++) {
    $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $probe 2>&1 | Out-String
    $j = Get-Content $single -Raw | ConvertFrom-Json
    $runs += [pscustomobject]@{
        run            = $i
        trap_arms      = $j.trap_arms
        trap_hit       = $j.trap_hit
        safe_arms      = $j.safe_arms
        safe_ok        = $j.safe_ok
        corrupt_values = @($j.corrupt_values)
    }
}

$hits = @($runs | ForEach-Object { $_.trap_hit })
$vals = @($runs | ForEach-Object { $_.corrupt_values } | Sort-Object -Unique)
$safeBadRuns = @($runs | Where-Object { $_.safe_ok -ne $_.safe_arms }).Count
$armsPerRun = $runs[0].safe_arms

$agg = [pscustomobject]@{
    ps_version           = "$($PSVersionTable.PSVersion)"
    repeats              = $Repeat
    trap_hit_per_run     = $hits
    trap_hit_min         = ($hits | Measure-Object -Minimum).Minimum
    trap_hit_max         = ($hits | Measure-Object -Maximum).Maximum
    trap_arms_per_run    = $runs[0].trap_arms
    nondeterministic     = (($hits | Sort-Object -Unique).Count -gt 1)
    runs_with_a_trap     = @($hits | Where-Object { $_ -gt 0 }).Count
    corrupt_values       = $vals
    safe_arms_per_run    = $armsPerRun
    safe_observations    = $armsPerRun * $Repeat
    safe_ok_total        = ($runs | Measure-Object -Property safe_ok -Sum).Sum
    runs_with_safe_loss  = $safeBadRuns
    runs                 = $runs
}

$dest = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\exitcode-repeat.json'
$agg | ConvertTo-Json -Depth 5 | Set-Content -Path $dest -Encoding utf8

Write-Output "repeats            : $Repeat"
Write-Output "trap_hit per run   : $($hits -join ', ') (of $($runs[0].trap_arms))"
Write-Output "nondeterministic   : $($agg.nondeterministic)"
Write-Output "runs with a trap   : $($agg.runs_with_a_trap) of $Repeat"
Write-Output "corrupted value(s) : $($vals -join ', ')"
Write-Output "safe observations  : $($agg.safe_ok_total) of $($agg.safe_observations) reported the true code"
Write-Output "wrote $dest"

if ($agg.runs_with_a_trap -eq 0) { Write-Output 'VERDICT: INCONCLUSIVE'; exit 2 }
if ($safeBadRuns -gt 0) { Write-Output 'VERDICT: RED'; exit 1 }
Write-Output 'VERDICT: GREEN'
exit 0
