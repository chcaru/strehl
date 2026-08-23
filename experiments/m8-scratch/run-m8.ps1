# M8 — decoder scratch. Measurement driver.
#
# Every stage writes CSV under data\ and a log under data\logs\. Nothing here
# writes anywhere except this experiment's own data\ directory; the corpora at
# C:\dev\macro and D:\macro-dark-frames are opened read-only by the decoder.
#
# Run the stages in order. Nothing downstream of a failed stage is worth
# reading. Exact command lines are in README.md.
#
#   .\run-m8.ps1 -Stage selftest         harness controls; run this first
#   .\run-m8.ps1 -Stage null             real-data null and known-size control
#   .\run-m8.ps1 -Stage single           one decode in isolation, x 660
#   .\run-m8.ps1 -Stage seq              retention: N decodes, one live at a time
#   .\run-m8.ps1 -Stage conc             the scratch fit: k concurrent decodes
#   .\run-m8.ps1 -Stage crossinstrument  external poller vs the child's own counters
#   .\run-m8.ps1 -Stage stack            the real stacker, threads and N swept
#   .\run-m8.ps1 -Stage reps             repeats, for the run-to-run uncertainty
#   .\run-m8.ps1 -Stage shape            SYNTHESIS 3.2.1 assertion 1, pinned threads
#   .\run-m8.ps1 -Stage holdout          never fitted; only ever predicted

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('selftest', 'null', 'single', 'seq', 'conc', 'crossinstrument',
        'stack', 'reps', 'shape', 'floor', 'holdout')]
    [string]$Stage
)

$ErrorActionPreference = 'Stop'
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (Resolve-Path (Join-Path $here '..\..')).Path
$exe = Join-Path $here 'target\release\m8-scratch.exe'
$strehl = Join-Path $repo 'target\release\strehl.exe'
$data = Join-Path $here 'data'
$logs = Join-Path $data 'logs'
New-Item -ItemType Directory -Force -Path $data, $logs | Out-Null

$stacks = @{
    '109MSDCF'    = 'C:\dev\macro\test\109MSDCF'      # 22 real frames, f/11,  ISO 160
    'coffee-bean' = 'C:\dev\macro\test\coffee-bean'   # 105 real frames, f/8,  ISO 50
    '119MSDCF'    = 'C:\dev\macro\test\119MSDCF'      # 33 real frames, f/5.6, ISO 50
}
# Real sensor data, same body, same pixel count, much smaller compressed files.
# This is the lever arm that separates "scratch is constant per decode" from
# "scratch tracks file size" without leaving real data for a synthetic corpus.
$darks = @{
    'dark-ISO50'  = 'D:\macro-dark-frames\122MSDCF'
    'dark-ISO200' = 'D:\macro-dark-frames\123MSDCF'
    'dark-hi'     = 'D:\macro-dark-frames\128MSDCF'
}

$STACK_HEADER = '#stack,frames,threads,rep,peak_ws,peak_commit,seconds,chunks,chunk_len,workers,per_worker_model_mb,peak_live'

function Assert-Built {
    param([string]$Path, [string]$What, [string]$Dir)
    if (-not (Test-Path $Path)) {
        Push-Location $Dir
        cargo build --release | Out-Host
        Pop-Location
    }
    if (-not (Test-Path $Path)) { throw "$What is not built at $Path" }
}

# Run a child process and capture the kernel-maintained peaks from outside.
# PeakWorkingSet64 is PeakWorkingSetSize; PeakPagedMemorySize64 is
# PeakPagefileUsage, i.e. peak private commit. Both are maintained by the
# kernel, so the 15 ms poll only has to see the handle before it is closed.
# The `crossinstrument` stage proves this agrees with the child's own reading.
function Invoke-Measured {
    param([string]$Exe, [string[]]$ArgList, [string]$Tag)
    $out = Join-Path $logs "$Tag.out.txt"
    $err = Join-Path $logs "$Tag.err.txt"
    $p = Start-Process -FilePath $Exe -ArgumentList $ArgList -PassThru -NoNewWindow `
        -RedirectStandardOutput $out -RedirectStandardError $err
    $peakWs = 0; $peakCommit = 0
    while (-not $p.HasExited) {
        try {
            $p.Refresh()
            if ($p.PeakWorkingSet64 -gt $peakWs) { $peakWs = $p.PeakWorkingSet64 }
            if ($p.PeakPagedMemorySize64 -gt $peakCommit) { $peakCommit = $p.PeakPagedMemorySize64 }
        }
        catch { }
        Start-Sleep -Milliseconds 15
    }
    try {
        $p.Refresh()
        if ($p.PeakWorkingSet64 -gt $peakWs) { $peakWs = $p.PeakWorkingSet64 }
        if ($p.PeakPagedMemorySize64 -gt $peakCommit) { $peakCommit = $p.PeakPagedMemorySize64 }
    }
    catch { }
    [pscustomobject]@{
        PeakWs     = $peakWs
        PeakCommit = $peakCommit
        Exit       = $p.ExitCode
        Seconds    = ($p.ExitTime - $p.StartTime).TotalSeconds
        Out        = $out
        Err        = $err
    }
}

# One `strehl stack` run at a pinned thread count, appended to $Csv. The plan
# is read back out of the binary's own banner rather than recomputed here, so
# the chunk count in the CSV is what the binary actually did.
function Measure-Stack {
    param(
        [string]$Name, [string]$Dir, [int]$N, [int]$Threads,
        [string]$Csv, [string]$OutTif, [int]$Rep = 0
    )
    $env:RAYON_NUM_THREADS = "$Threads"
    $argList = @('stack', $Dir, '-o', $OutTif)
    if ($N -gt 0) { $argList += @('--limit', "$N") }
    $m = Invoke-Measured -Exe $strehl -Tag "stack-$Name-n$N-t$Threads-r$Rep" -ArgList $argList
    if ($m.Exit -ne 0) { throw "strehl stack failed; see $($m.Err)" }
    $log = Get-Content $m.Err -Raw
    $frames = [regex]::Match($log, 'frames\s+:\s+(\d+)').Groups[1].Value
    $wk = [regex]::Match($log, 'workers\s+:\s+(\d+) chunks of <= (\d+) frames \((\d+) allowed')
    $pw = [regex]::Match($log, 'working set\s+:\s+([\d.]+) MB/worker')
    $pl = [regex]::Match($log, 'in-flight frames:\s+(\d+) peak')
    Add-Content -Path $Csv -Value ("{0},{1},{2},{3},{4},{5},{6:N3},{7},{8},{9},{10},{11}" -f `
            $Name, $frames, $Threads, $Rep, $m.PeakWs, $m.PeakCommit, $m.Seconds, `
            $wk.Groups[1].Value, $wk.Groups[2].Value, $wk.Groups[3].Value, `
            $pw.Groups[1].Value, $pl.Groups[1].Value)
    Write-Host ("  $Name N=$frames t=$Threads rep=$Rep chunks=$($wk.Groups[1].Value) -> ws {0:N0} MiB, {1:N1} s" -f ($m.PeakWs / 1MB), $m.Seconds)
}

Assert-Built -Path $exe -What 'm8-scratch' -Dir $here

switch ($Stage) {

    'selftest' {
        $env:RAYON_NUM_THREADS = '1'
        & $exe selftest 1> (Join-Path $data 'selftest.csv')
        if ($LASTEXITCODE -ne 0) { throw 'selftest FAILED' }
        Write-Host 'selftest passed'
    }

    'null' {
        $csv = Join-Path $data 'null.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        foreach ($t in 1, 32) {
            $env:RAYON_NUM_THREADS = "$t"
            foreach ($name in $stacks.Keys) {
                & $exe null $stacks[$name] --limit 8 |
                Where-Object { $_ -notmatch '^#' -or -not (Test-Path $csv) } |
                Add-Content -Path $csv
            }
        }
        Write-Host "wrote $csv"
    }

    'single' {
        $csv = Join-Path $data 'single.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        $all = $stacks + $darks
        foreach ($t in 1, 4, 32) {
            $env:RAYON_NUM_THREADS = "$t"
            foreach ($name in $all.Keys) {
                Write-Host "single threads=$t $name"
                & $exe single $all[$name] |
                Where-Object { $_ -notmatch '^#' -or -not (Test-Path $csv) } |
                Add-Content -Path $csv
            }
        }
        Write-Host "wrote $csv"
    }

    'seq' {
        $csv = Join-Path $data 'seq.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        foreach ($t in 1, 32) {
            $env:RAYON_NUM_THREADS = "$t"
            foreach ($name in 'coffee-bean', '119MSDCF') {
                Write-Host "seq threads=$t $name"
                & $exe seq $stacks[$name] |
                Where-Object { $_ -notmatch '^#' -or -not (Test-Path $csv) } |
                Add-Content -Path $csv
            }
        }
        Write-Host "wrote $csv"
    }

    'conc' {
        $csv = Join-Path $data 'conc.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value '#kind,k,reps,mode,threads,n_decodes,base_ws,base_commit,kpeak_ws,kpeak_commit,samp_peak_ws,samp_peak_commit,elapsed_secs,mean_file_bytes,alloc_bytes,stack,drv_peak_ws,drv_peak_commit'
        # k = 0 is the null: the same process, same file list, no decode at all.
        $ks = 0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32
        foreach ($t in 1, 32) {
            $env:RAYON_NUM_THREADS = "$t"
            foreach ($name in 'coffee-bean', 'dark-ISO50') {
                $dir = if ($stacks.ContainsKey($name)) { $stacks[$name] } else { $darks[$name] }
                foreach ($k in $ks) {
                    $r = Invoke-Measured -Exe $exe -Tag "conc-t$t-$name-k$k" `
                        -ArgList @('conc', $dir, '--k', "$k", '--reps', '4')
                    if ($r.Exit -ne 0) { throw "conc k=$k failed; see $($r.Err)" }
                    $row = (Get-Content $r.Out | Where-Object { $_ -notmatch '^#' })
                    Add-Content -Path $csv -Value "$row,$name,$($r.PeakWs),$($r.PeakCommit)"
                    Write-Host ("  t=$t $name k=$k -> ws {0:N0} MiB commit {1:N0} MiB" -f ($r.PeakWs / 1MB), ($r.PeakCommit / 1MB))
                }
            }
        }
        # Hold mode: K frames live at once, one decode each, all overlapping on
        # a barrier. Cross-checks the frame-buffer term.
        $env:RAYON_NUM_THREADS = '32'
        foreach ($k in 1, 2, 4, 8, 12, 16, 20, 24, 32) {
            $r = Invoke-Measured -Exe $exe -Tag "conc-hold-k$k" `
                -ArgList @('conc', $stacks['coffee-bean'], '--k', "$k", '--reps', '1', '--hold')
            if ($r.Exit -ne 0) { throw "conc hold k=$k failed" }
            $row = (Get-Content $r.Out | Where-Object { $_ -notmatch '^#' })
            Add-Content -Path $csv -Value "$row,coffee-bean,$($r.PeakWs),$($r.PeakCommit)"
            Write-Host ("  hold k=$k -> ws {0:N0} MiB" -f ($r.PeakWs / 1MB))
        }
        Write-Host "wrote $csv"
    }

    'crossinstrument' {
        # The external poller and the child's own kernel counters must agree.
        # If they do not, every externally measured stacker number is suspect.
        $csv = Join-Path $data 'crossinstrument.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value '#k,child_kpeak_ws,child_kpeak_commit,driver_peak_ws,driver_peak_commit'
        $env:RAYON_NUM_THREADS = '32'
        foreach ($k in 1, 4, 12, 24) {
            $r = Invoke-Measured -Exe $exe -Tag "xi-k$k" `
                -ArgList @('conc', $stacks['coffee-bean'], '--k', "$k", '--reps', '3')
            $row = (Get-Content $r.Out | Where-Object { $_ -notmatch '^#' }) -split ','
            Add-Content -Path $csv -Value "$k,$($row[8]),$($row[9]),$($r.PeakWs),$($r.PeakCommit)"
        }
        Get-Content $csv
    }

    'stack' {
        Assert-Built -Path $strehl -What 'strehl' -Dir $repo
        $csv = Join-Path $data 'stack.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value $STACK_HEADER
        $out = Join-Path $data 'out.tif'
        # Threads swept at fixed N. Live concurrency is min(chunks, threads),
        # so this is the thread axis with the chunk axis held still (fact 22).
        foreach ($t in 1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 24, 32) {
            Measure-Stack -Name 'coffee-bean' -Dir $stacks['coffee-bean'] -N 0 -Threads $t -Csv $csv -OutTif $out
        }
        foreach ($t in 1, 2, 3, 4, 6, 8, 11, 16, 32) {
            Measure-Stack -Name '109MSDCF' -Dir $stacks['109MSDCF'] -N 0 -Threads $t -Csv $csv -OutTif $out
        }
        # N swept at fixed threads: --limit moves the chunk count and the chunk
        # length without moving the thread count.
        foreach ($n in 8, 12, 20, 40, 60) {
            Measure-Stack -Name 'coffee-bean' -Dir $stacks['coffee-bean'] -N $n -Threads 32 -Csv $csv -OutTif $out
            Measure-Stack -Name 'coffee-bean' -Dir $stacks['coffee-bean'] -N $n -Threads 8 -Csv $csv -OutTif $out
        }
        Remove-Item $out -ErrorAction SilentlyContinue
        Write-Host "wrote $csv"
    }

    'reps' {
        # Peak RSS is a scheduling-dependent quantity. Without repeats there is
        # no uncertainty to attach to the per-worker constant, and a slope with
        # no uncertainty is the mistake M2 made.
        Assert-Built -Path $strehl -What 'strehl' -Dir $repo
        $csv = Join-Path $data 'reps.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value $STACK_HEADER
        $out = Join-Path $data 'out-reps.tif'
        $points = @(
            @('109MSDCF', 0, 32), @('109MSDCF', 0, 1), @('109MSDCF', 0, 6),
            @('coffee-bean', 0, 32), @('coffee-bean', 0, 8),
            @('coffee-bean', 40, 32), @('coffee-bean', 60, 32), @('coffee-bean', 20, 32)
        )
        foreach ($rep in 1, 2, 3, 4) {
            foreach ($p in $points) {
                Measure-Stack -Name $p[0] -Dir $stacks[$p[0]] -N $p[1] -Threads $p[2] `
                    -Csv $csv -OutTif $out -Rep $rep
            }
        }
        Remove-Item $out -ErrorAction SilentlyContinue
        Write-Host "wrote $csv"
    }

    'shape' {
        # SYNTHESIS 3.2.1 assertion 1, the machine-independent one: with the
        # thread count PINNED, peak RSS at N = 4 x pool must not exceed peak RSS
        # at N = 2 x pool by more than a small tolerance. Both sides move
        # together with core count, so this tests the code and not the runner.
        Assert-Built -Path $strehl -What 'strehl' -Dir $repo
        $csv = Join-Path $data 'shape.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value $STACK_HEADER
        $out = Join-Path $data 'out-shape.tif'
        foreach ($rep in 1, 2) {
            foreach ($t in 4, 8) {
                foreach ($mult in 2, 3, 4, 8) {
                    $n = $t * $mult
                    if ($n -le 105) {
                        Measure-Stack -Name 'coffee-bean' -Dir $stacks['coffee-bean'] `
                            -N $n -Threads $t -Csv $csv -OutTif $out -Rep $rep
                    }
                }
            }
        }
        Remove-Item $out -ErrorAction SilentlyContinue
        Write-Host "wrote $csv"
    }

    'floor' {
        # The intercept of the sweep fit is the least well constrained term in
        # it, because every fitted point has live >= 1 and most have live >> 1.
        # Measure it directly instead: one thread, one or two frames, so the
        # fold is as small as it can be and whatever is left is prologue,
        # epilogue and runtime.
        Assert-Built -Path $strehl -What 'strehl' -Dir $repo
        $csv = Join-Path $data 'floor.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value $STACK_HEADER
        $out = Join-Path $data 'out-floor.tif'
        foreach ($rep in 1, 2, 3) {
            foreach ($n in 1, 2, 3, 4, 6, 8) {
                Measure-Stack -Name 'coffee-bean' -Dir $stacks['coffee-bean'] -N $n -Threads 1 `
                    -Csv $csv -OutTif $out -Rep $rep
            }
        }
        Remove-Item $out -ErrorAction SilentlyContinue
        Write-Host "wrote $csv"
    }

    'holdout' {
        # Never fitted. 119MSDCF is a third stack, a different aperture, a
        # different ISO and a different frame count, and it is only ever
        # predicted.
        Assert-Built -Path $strehl -What 'strehl' -Dir $repo
        $csv = Join-Path $data 'holdout.csv'
        Remove-Item $csv -ErrorAction SilentlyContinue
        Add-Content -Path $csv -Value $STACK_HEADER
        $out = Join-Path $data 'out-holdout.tif'
        foreach ($rep in 1, 2) {
            foreach ($t in 2, 5, 9, 17, 32) {
                Measure-Stack -Name '119MSDCF' -Dir $stacks['119MSDCF'] -N 0 -Threads $t `
                    -Csv $csv -OutTif $out -Rep $rep
            }
        }
        Remove-Item $out -ErrorAction SilentlyContinue
        Write-Host "wrote $csv"
    }
}
