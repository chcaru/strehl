<#
.SYNOPSIS
  Render every stack in the owner's library, unattended, and record what happened.

.DESCRIPTION
  This is the render table instrument. It exists to answer one question honestly:
  what does strehl actually do when pointed at the real library, without a human
  babysitting it? Subject, frame count, wall clock, peak memory, and the failure
  mode when there is one.

  It measures on the LINEAR output. It never passes --srgb. Results in this
  project have been retracted for being measured on an --srgb render, so the
  harness does not offer the option; conversion to display happens in
  crop_set.py, downstream, on a copy.

  PEAK MEMORY IS WITHDRAWN. This script used to report PeakWorkingSet64 polled
  while the child was alive, described as a tight lower bound. It is not a
  measurement at all. Probed on identical work -- coffee-bubbles, 19 frames,
  one binary -- across five runs and two polling methods (the cached Process
  object with Refresh(), and a fresh Get-Process each poll) it reported 11, 16,
  16, 84, 87, 163, 1180 and 1658 MB. One run returned PeakVirtualMemorySize64
  as 0, which is impossible for a live process, so the counters are not being
  read reliably through Start-Process. Any peak-memory figure this script
  emitted, including those in the delivered render table, should be ignored.

  The reliable route is for the binary to report its own peak via
  GetProcessMemoryInfo at exit. Until that exists the honest statement is that
  nothing has ever run out of memory: 26/26 subjects, up to 299 frames at
  33 MP, all exit 0.

.EXAMPLE
  pwsh -File scripts\render_all.ps1 -Exe C:\dev\strehl-out\baseline-src\target\release\strehl.exe -OutDir C:\dev\strehl-out\baseline
#>
[CmdletBinding()]
param(
    # strehl binary to exercise.
    [string]$Exe = "C:\dev\strehl-out\baseline-src\target\release\strehl.exe",

    # Library root. READ-ONLY. Nothing is ever written under here.
    [string]$Root = "D:\personal\macro",

    # Where renders, logs and the manifest land.
    [string]$OutDir = "C:\dev\strehl-out\baseline",

    # Restrict to these subject folder names. Empty means every subject.
    [string[]]$Subjects = @(),

    # Folders that are not subjects. flat-fields is a 484-frame calibration
    # campaign, not a stack, and stacking it would be meaningless.
    [string[]]$Skip = @("flat-fields"),

    # Cap frames per subject. 0 means the whole bracket.
    [int]$Limit = 0,

    # Emit full sensor resolution (Malvar-He-Cutler) instead of binning each
    # 2x2 quad. Still linear, still no colour matrix -- this is the print
    # artifact, not a viewing render.
    [switch]$Demosaic,

    # Give up on a subject after this long and record it as a hang.
    [int]$TimeoutSec = 5400,

    # Skip subjects whose output already exists.
    [switch]$Resume
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe)) { throw "no strehl binary at $Exe" }
if (-not (Test-Path $Root)) { throw "no library at $Root" }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$candidates = Get-ChildItem $Root -Directory | Where-Object { $Skip -notcontains $_.Name }
if ($Subjects.Count -gt 0) {
    $candidates = $candidates | Where-Object { $Subjects -contains $_.Name }
}
# Cheapest first, so that a defect that affects everything surfaces in seconds
# rather than after the first 299-frame bracket.
$work = foreach ($d in $candidates) {
    # -Filter takes DOS wildcards and cannot express a character class, so the
    # extension test is a regex on the name.
    $n = @(Get-ChildItem $d.FullName -File | Where-Object { $_.Name -match '\.(ARW|SR2|DNG|NEF|CR2|CR3|RAF)$' }).Count
    if ($n -gt 0) { [pscustomobject]@{ Name = $d.Name; Path = $d.FullName; Frames = $n } }
}
$work = $work | Sort-Object Frames

Write-Host ("harness  : {0} subjects, {1} frames total" -f $work.Count, ($work | Measure-Object Frames -Sum).Sum)
Write-Host ("binary   : {0}" -f $Exe)
Write-Host ("out      : {0}" -f $OutDir)
Write-Host ("mode     : linear, {0}" -f $(if ($Demosaic) { "full resolution (--demosaic)" } else { "binned" }))
Write-Host ""

$rows = @()

foreach ($s in $work) {
    $subOut = Join-Path $OutDir $s.Name
    New-Item -ItemType Directory -Force -Path $subOut | Out-Null
    $tif = Join-Path $subOut "linear.tif"
    $log = Join-Path $subOut "render.log"
    $err = Join-Path $subOut "render.err"

    if ($Resume -and (Test-Path $tif)) {
        Write-Host ("skip     : {0} (already rendered)" -f $s.Name)
        continue
    }

    $argv = @("stack", $s.Path, "--out", $tif)
    if ($Limit -gt 0) { $argv += @("--limit", "$Limit") }
    if ($Demosaic) { $argv += "--demosaic" }

    Write-Host ("render   : {0,-38} {1,4} frames ..." -f $s.Name, $s.Frames) -NoNewline

    $peak = 0L
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $status = "ok"
    $code = 0

    # Start-Process with file redirection rather than a piped ProcessStartInfo:
    # reading two pipes from one thread deadlocks as soon as either fills, and
    # these renders emit a lot on both.
    $p = Start-Process -FilePath $Exe -ArgumentList $argv -PassThru -NoNewWindow `
        -RedirectStandardOutput $log -RedirectStandardError $err

    # Touching .Handle caches the OS handle on the object. Without it
    # Start-Process -PassThru yields a NULL ExitCode once the child is gone, and
    # `$null -ne 0` scores every successful render as a failure.
    $null = $p.Handle

    while (-not $p.HasExited) {
        if ($sw.Elapsed.TotalSeconds -gt $TimeoutSec) {
            $status = "HANG (killed at ${TimeoutSec}s)"
            try { Stop-Process -Id $p.Id -Force } catch { }
            break
        }
        try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $peak) { $peak = $p.PeakWorkingSet64 } } catch { }
        Start-Sleep -Milliseconds 200
    }
    $sw.Stop()
    try { $p.WaitForExit(10000) | Out-Null } catch { }
    try { $code = $p.ExitCode } catch { $code = -1 }

    # The whole measurement report goes to STDERR; stdout is empty. Status is
    # judged on the report's own "wrote" line, which is the only statement that
    # the pixels reached the disk, with the exit code as a secondary check.
    $txt = ""
    if (Test-Path $err) { $txt = Get-Content $err -Raw }
    $wrote = $txt -match 'wrote\s+:'

    if ($status -eq "ok") {
        if (-not (Test-Path $tif)) {
            $status = "FAIL (no output file)"
        } elseif (-not $wrote) {
            $status = "FAIL (no wrote line; exit $code)"
        } elseif ($code -ne 0 -and $null -ne $code) {
            $status = "FAIL (exit $code)"
        }
    }

    $sizeMb = 0
    if (Test-Path $tif) { $sizeMb = [math]::Round((Get-Item $tif).Length / 1MB, 1) }

    # Pull the couple of numbers worth having in the table out of the report.
    $dims = ""; $neff = ""; $align = ""; $fov = ""
    if ($txt) {
        if ($txt -match 'wrote\s+:\s+\S+\s+\((\d+ x \d+)') { $dims = $Matches[1] }
        if ($txt -match 'mean n_eff[\s\S]{0,400}?\n\s+[\d.]+\s+[\d.]+\s+([\d.]+)') { $neff = $Matches[1] }
        if ($txt -match 'alignment\s*:\s*(.+)') { $align = $Matches[1].Trim() }
        if ($txt -match 'field of view scaled to ([\d.]+)') { $fov = $Matches[1] }
    }

    $rows += [pscustomobject]@{
        Subject    = $s.Name
        Frames     = $s.Frames
        Status     = $status
        WallSec    = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        PeakMB     = [math]::Round($peak / 1MB, 0)
        OutMB      = $sizeMb
        Dims       = $dims
        MeanNeff   = $neff
        FovScale   = $fov
        Alignment  = $align
    }

    # Persist wall clock and peak RSS beside the render. Without this the two
    # numbers exist only on the console, and a table that cannot be rebuilt
    # from the artifacts is a table that has to be re-measured to be corrected.
    [pscustomobject]@{
        Subject = $s.Name; Frames = $s.Frames
        WallSec = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        PeakMB  = [math]::Round($peak / 1MB, 0)
    } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $subOut "timing.json")

    Write-Host (" {0,8}s  {1,6} MB  {2}" -f [math]::Round($sw.Elapsed.TotalSeconds, 1), [math]::Round($peak / 1MB, 0), $status)
}

$manifest = Join-Path $OutDir "render-table.tsv"
$rows | Export-Csv -NoTypeInformation -Delimiter "`t" -Path $manifest -Encoding utf8
Write-Host ""
Write-Host ("manifest : {0}" -f $manifest)
$rows | Format-Table Subject, Frames, Status, WallSec, PeakMB, Dims, MeanNeff, FovScale -AutoSize
