# Worker-count sweep for the DEFAULT (pyramid) merge.
#
# WHY THIS EXISTS.  band_workers() in crates/strehl-cli/src/merge_cmd.rs sizes
# the fold pool from a MEMORY budget and deliberately ignores core count, so on
# a 16-core/32-thread box a 33 MP stack still folds 4 frames at a time.  That is
# a correctness decision, not an oversight: float addition is not associative,
# so a host-dependent worker count would make the shipped merge produce
# different BYTES on different machines.  The question this sweep answers is
# what that costs, and it is the one number a reader of the README will want.
#
# STREHL_PYRAMID_WORKERS overrides the pool.  Changing it CHANGES THE OUTPUT
# BYTES (different reduction order), so this is a speed-only experiment and its
# outputs are NOT valid masters -- they are not compared to the shipped one.
#
# Method: two passes in OPPOSITE order (rule 16), per-setting minimum, on a
# 40-frame limit so the whole sweep fits in minutes on a box that is busy.
# Alignment is served from the sidecar in every arm (the cache is already warm
# for --limit 40 from the ladder), so this measures the FOLD, not the solve.

$ErrorActionPreference = 'Stop'
$Exe = 'C:\dev\strehl-out\BUILD-SPEED\cargo-target\release\strehl.exe'
$Dir = 'D:\personal\macro\bee-3-cpl'
$OutRoot = 'C:\dev\strehl-out\BUILD-SPEED\out'
$env:STREHL_CACHE_DIR = 'C:\dev\strehl-out\BUILD-SPEED\warpcache'
$Limit = 40

$settings = @(1, 2, 4, 8)
$passes = @(
    @{ name = 'UP'; order = $settings },
    @{ name = 'DOWN'; order = ($settings[($settings.Count - 1)..0]) }
)

$rows = @()
foreach ($p in $passes) {
    foreach ($w in $p.order) {
        $env:STREHL_PYRAMID_WORKERS = "$w"
        $out = Join-Path $OutRoot "workers-w$w.tif"
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $err = Join-Path $OutRoot "workers-w$w.stderr.txt"
        $proc = Start-Process -FilePath $Exe -NoNewWindow -PassThru -RedirectStandardError $err `
            -RedirectStandardOutput "$err.out" `
            -ArgumentList @('stack', $Dir, '--out', $out, '--limit', "$Limit", '--srgb', '--auto-exposure')
        $null = $proc.Handle
        $proc.WaitForExit()
        $sw.Stop()
        $code = $proc.ExitCode
        $wall = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        $cpu = [math]::Round($proc.TotalProcessorTime.TotalSeconds, 1)
        $peak = [math]::Round($proc.PeakWorkingSet64 / 1GB, 2)
        $txt = Get-Content $err -Raw
        $fold = if ($txt -match 'folded\s+:.*?in\s+([\d.]+)\s+s') { [double]$Matches[1] } else { $null }
        $plan = if ($txt -match 'memory plan\s+:\s+(.+)') { $Matches[1].Trim() } else { '?' }
        $rows += [pscustomobject]@{
            Pass = $p.name; Workers = $w; RC = $code; Wall = $wall; Fold = $fold
            CPUs = $cpu; Threads = [math]::Round($cpu / $wall, 2); PeakGB = $peak; Plan = $plan
        }
        "{0,-4} W={1,-2} rc={2} wall={3,7:N2}s fold={4,7:N1}s cpu={5,7:N1}s thr={6,5:N2} peak={7,5:N2}GB  {8}" -f `
            $p.name, $w, $code, $wall, $fold, $cpu, ([math]::Round($cpu / $wall, 2)), $peak, $plan
    }
}
Remove-Item Env:\STREHL_PYRAMID_WORKERS -ErrorAction SilentlyContinue

''
'=== per-setting MINIMUM over both passes (rule 16) ==='
$base = $null
foreach ($w in $settings) {
    $g = $rows | Where-Object { $_.Workers -eq $w -and $_.RC -eq 0 }
    if (-not $g) { "W=$w : no successful run"; continue }
    $best = ($g | Measure-Object Wall -Minimum).Minimum
    if ($w -eq 4) { $base = $best }
    $rows2 = $g | Sort-Object Wall | Select-Object -First 1
    "W={0,-2} best wall {1,7:N2}s  fold {2,7:N1}s  threads {3,5:N2}  peak {4,5:N2}GB" -f `
        $w, $best, $rows2.Fold, $rows2.Threads, $rows2.PeakGB
}
if ($base) {
    ''
    "=== speedup against the shipped default (4 workers) ==="
    foreach ($w in $settings) {
        $g = $rows | Where-Object { $_.Workers -eq $w -and $_.RC -eq 0 }
        if ($g) {
            $best = ($g | Measure-Object Wall -Minimum).Minimum
            "W={0,-2} {1,6:N2}x" -f $w, ($base / $best)
        }
    }
}
