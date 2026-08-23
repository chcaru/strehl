# Negative control for the M8 tests.
#
# A test that has never been seen to fail is not evidence. This deliberately
# regresses `crates/strehl-cli/src/stack.rs` one constant at a time, checks that
# the test that is *supposed* to catch that regression goes red, and restores
# from a byte copy afterwards.
#
# Two traps this script exists to avoid, both of which have cost this project
# time before:
#   * `git checkout --` would restore HEAD, not the working tree, and would
#     destroy uncommitted work. Restore from a copy instead.
#   * `Copy-Item` preserves the SOURCE mtime, so cargo sees an unchanged file
#     and skips the rebuild -- giving a false "still red" or false "still
#     green". Every write here is followed by an explicit mtime bump.
#
#   .\negative-control.ps1

$ErrorActionPreference = 'Stop'
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (Resolve-Path (Join-Path $here '..\..')).Path
$src = Join-Path $repo 'crates\strehl-cli\src\stack.rs'
$bak = Join-Path $here 'data\stack.rs.negctl-backup'

function Set-Source {
    param([string]$Text)
    Set-Content -Path $src -Value $Text -NoNewline
    (Get-Item $src).LastWriteTime = Get-Date   # or cargo will skip the rebuild
}

function Test-Names {
    Push-Location $repo
    $out = cargo test --workspace 2>&1 | Out-String
    Pop-Location
    $failed = [regex]::Matches($out, 'test (\S+) \.\.\. FAILED') | ForEach-Object { $_.Groups[1].Value }
    $counts = [regex]::Matches($out, 'test result: \w+\. (\d+) passed; (\d+) failed')
    $passed = ($counts | ForEach-Object { [int]$_.Groups[1].Value } | Measure-Object -Sum).Sum
    [pscustomobject]@{ Failed = $failed; Passed = $passed }
}

$original = Get-Content $src -Raw
Copy-Item $src $bak -Force

# from            -> to                         -> the test that must catch it
$regressions = @(
    @{ From = 'const DECODER_SCRATCH_BYTES: usize = 38_797_312;'
        To  = 'const DECODER_SCRATCH_BYTES: usize = 0;'
        Catch = 'the_m8_model_reproduces_the_measured_full_overlap_peaks'
    },
    @{ From = 'const PROCESS_FLOOR_BYTES: usize = 15_099_494;'
        To  = 'const PROCESS_FLOOR_BYTES: usize = 150_994_944;'
        Catch = 'the_m8_constants_match_the_measurements_they_came_from'
    },
    @{ From = '        (chunks - 1).ilog2() as usize + 1'
        To  = '        chunks.ilog2() as usize + 1'
        Catch = 'reduce_levels_is_ceil_log2'
    },
    @{ From = '            MemoryModel::Buffers => (MEMORY_BUDGET_BYTES / per_worker_bytes).max(1),'
        To  = '            MemoryModel::Buffers => m8_worker_cap(px, per_worker_bytes),'
        Catch = 'the_default_memory_model_is_unchanged_by_m8'
    },
    @{ From = '            MemoryModel::M8 => m8_worker_cap(px, per_worker_bytes),'
        To  = '            MemoryModel::M8 => (MEMORY_BUDGET_BYTES / per_worker_bytes).max(1),'
        Catch = 'the_m8_memory_model_is_opt_in_and_plans_within_the_budget'
    },
    @{ From = '             working set     : {:.0} MB/worker buffers, >= {:.2} GB peak (LOWER BOUND -- buffers \'
        To  = '             working set     : {:.0} MB/worker buffers, {:.2} GB peak (exactly, buffers \'
        Catch = 'describe_reports_both_the_lower_bound_and_the_measured_prediction'
    }
)

Write-Host "`n=== baseline: the suite must be green before any of this means anything ==="
$base = Test-Names
if ($base.Failed.Count -ne 0) {
    Set-Source $original
    throw "baseline is already red: $($base.Failed -join ', ')"
}
Write-Host "  $($base.Passed) tests pass"

$verdicts = @()
try {
    foreach ($r in $regressions) {
        Write-Host "`n=== regress: $($r.To.Trim()) ==="
        if (-not $original.Contains($r.From)) { throw "pattern not found: $($r.From)" }
        Set-Source $original.Replace($r.From, $r.To)
        $res = Test-Names
        $caught = @($res.Failed | Where-Object { $_ -eq $r.Catch -or $_.EndsWith("::$($r.Catch)") }).Count -gt 0
        Write-Host "  failed: $(if ($res.Failed) { $res.Failed -join ', ' } else { '(nothing)' })"
        Write-Host "  expected $($r.Catch) to fail: $(if ($caught) { 'YES' } else { 'NO -- THE TEST IS BLIND' })"
        $verdicts += [pscustomobject]@{
            Regression = $r.To.Trim()
            Expected   = $r.Catch
            Caught     = $caught
            AllFailed  = ($res.Failed -join ' ')
        }
    }
}
finally {
    Write-Host "`n=== restoring from the byte copy (NOT from git) ==="
    Set-Source $original
    if ((Get-Content $src -Raw) -ne (Get-Content $bak -Raw)) { throw 'restore did not round-trip' }
}

$after = Test-Names
Write-Host "  after restore: $($after.Passed) pass, $($after.Failed.Count) fail"
if ($after.Failed.Count -ne 0) { throw "restore left the suite red: $($after.Failed -join ', ')" }
if ($after.Passed -ne $base.Passed) { throw "test count changed: $($base.Passed) -> $($after.Passed)" }

$verdicts | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
$blind = @($verdicts | Where-Object { -not $_.Caught })
if ($blind.Count -gt 0) { throw "$($blind.Count) regression(s) were not caught" }
Write-Host "NEGATIVE CONTROL PASSED: every regression was caught, and the suite is green again."
