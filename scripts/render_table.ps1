<#
.SYNOPSIS
  Rebuild render-table.tsv from the artifacts a render run left on disk.

.DESCRIPTION
  The render table is evidence, so it has to be reconstructible from the
  artifacts rather than only from the console. This reads each subject's
  render.err (the binary writes its whole report to STDERR, not stdout) plus
  the timing.json that render_all.ps1 drops beside it, and rebuilds the table
  without re-rendering anything.

  Status is judged on the report's own "wrote" line, which is the only
  statement that pixels reached the disk, cross-checked against the file
  existing and being non-empty.

.EXAMPLE
  pwsh -File scripts\render_table.ps1 -OutDir C:\dev\strehl-out\baseline
#>
[CmdletBinding()]
param(
    [string]$OutDir = "C:\dev\strehl-out\baseline"
)

$ErrorActionPreference = "Stop"

$rows = foreach ($d in Get-ChildItem $OutDir -Directory | Sort-Object Name) {
    $errFile = Join-Path $d.FullName "render.err"
    $tif = Join-Path $d.FullName "linear.tif"
    $timing = Join-Path $d.FullName "timing.json"
    if (-not (Test-Path $errFile)) { continue }

    $txt = Get-Content $errFile -Raw

    $wall = ""; $peak = ""; $frames = ""
    if (Test-Path $timing) {
        $t = Get-Content $timing -Raw | ConvertFrom-Json
        $wall = $t.WallSec; $peak = $t.PeakMB; $frames = $t.Frames
    }
    if (-not $frames -and $txt -match 'frames\s+:\s+(\d+)') { $frames = [int]$Matches[1] }

    $dims = ""; $neff = ""; $fov = ""; $align = ""; $internal = ""; $rate = ""
    if ($txt -match 'wrote\s+:\s+\S+\s+\((\d+ x \d+)') { $dims = $Matches[1] }
    if ($txt -match 'mean n_eff[\s\S]{0,400}?\n\s+[\d.]+\s+[\d.]+\s+([\d.]+)') { $neff = $Matches[1] }
    if ($txt -match 'field of view scaled to ([\d.]+)') { $fov = $Matches[1] }
    if ($txt -match 'total\s+:\s+([\d.]+) s') { $internal = $Matches[1] }
    if ($txt -match ',\s+([\d.]+) MB/s') { $rate = $Matches[1] }

    # Alignment: the report can emit more than one "alignment" line -- a REFUSED
    # line followed by an OFF line -- and the refusal is the one that matters.
    if ($txt -match 'alignment\s+:\s+REFUSED[^\r\n]*') { $align = "REFUSED - merged unregistered" }
    elseif ($txt -match 'alignment\s+:\s+OFF[^\r\n]*') { $align = "OFF" }
    elseif ($txt -match 'alignment\s+:\s+ON \(([^)]+)\)[^\r\n]*?(\d+) placed / (\d+) refused') {
        $align = "ON ($($Matches[1])) $($Matches[2])/$($Matches[3]) refused"
    }
    elseif ($txt -match 'alignment\s+:\s+([^\r\n]+)') { $align = $Matches[1].Trim() }

    # Did the registration certify itself, or is it unverified?
    $certified = if ($txt -match 'could not certify itself') { "UNVERIFIED" } else { "" }

    $sizeMb = if (Test-Path $tif) { [math]::Round((Get-Item $tif).Length / 1MB, 1) } else { 0 }
    $status = if (-not (Test-Path $tif)) { "FAIL (no output)" }
              elseif ($sizeMb -le 0) { "FAIL (empty output)" }
              elseif ($txt -notmatch 'wrote\s+:') { "FAIL (no wrote line)" }
              else { "ok" }

    [pscustomobject]@{
        Subject = $d.Name; Frames = $frames; Status = $status
        WallSec = $wall; PeakMB = $peak; OutMB = $sizeMb
        InternalSec = $internal; RateMBs = $rate
        Dims = $dims; MeanNeff = $neff; FovScale = $fov
        Alignment = $align; Certified = $certified
    }
}

$rows = $rows | Sort-Object { [int]$_.Frames }
$manifest = Join-Path $OutDir "render-table.tsv"
# Export-Csv on Windows PowerShell writes a UTF-8 BOM, which lands inside the
# first header cell and makes the column unaddressable by name in any reader.
# Write the TSV by hand with a BOM-less encoder so the artifact is machine
# readable.
$cols = @("Subject", "Frames", "Status", "WallSec", "PeakMB", "OutMB",
    "InternalSec", "RateMBs", "Dims", "MeanNeff", "FovScale", "Alignment", "Certified")
$lines = @(($cols -join "`t"))
$lines += $rows | ForEach-Object { $r = $_; ($cols | ForEach-Object { [string]$r.$_ }) -join "`t" }
[System.IO.File]::WriteAllLines($manifest, $lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "manifest : $manifest`n"
$rows | Format-Table Subject, Frames, Status, WallSec, PeakMB, Dims, MeanNeff, FovScale, Alignment, Certified -AutoSize
