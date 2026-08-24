# 08-sidecar-audit.ps1 -- re-runnable evidence for report section 4.10.
#
# Prompted by the 10:30 shared-state hazard notice: `strehl align` and
# `strehl stack` both default their warp sidecar to <stackdir>\warpmap.txt,
# inside the read-only capture library, with seven agents live in the tree.
# The notice asks whether any published number consumed a foreign sidecar.
#
# This does not re-render anything. Every render in this milestone wrote its
# own `alignment:` provenance line into a committed log, so the audit is a
# read over evidence captured at the time rather than a fresh measurement.
# That is the point: the logs were written before the hazard was known, so
# they cannot have been curated in response to it.
#
# Reads only committed logs under data\. Writes nothing outside this directory.
#
#   powershell -ExecutionPolicy Bypass -File 08-sidecar-audit.ps1

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $PSScriptRoot 'data'

if (-not (Test-Path $dataDir)) {
    throw "missing $dataDir -- run 01-render.ps1 first"
}

$rows = @()
foreach ($log in (Get-ChildItem (Join-Path $dataDir '*.log') | Sort-Object Name)) {
    $align  = (Select-String -Path $log.FullName -Pattern 'alignment\s*:' | Select-Object -First 1).Line
    $frames = (Select-String -Path $log.FullName -Pattern 'frames\s*:'    | Select-Object -First 1).Line

    if (-not $align) { $align = 'NO ALIGNMENT LINE' }
    $align = $align.Trim()

    # Which directory did this render read frames from? A path under D:\ is a
    # shared capture directory and therefore exposed to the hazard; a path
    # under C:\ is an isolated copy this milestone made for itself (section 4.6).
    $src = if ($frames -match 'from\s+(.+)$') { $Matches[1].Trim() } else { '?' }
    $shared = $src -like 'D:*'

    # Three provenance classes, in decreasing order of trust:
    #   solved   -- no sidecar was consumed at all
    #   rejected -- a sidecar was found, refused, and re-solved
    #   sidecar  -- a sidecar was consumed; only safe if this script's caller
    #               can show it was written by the same bracket in the same run
    $class =
        if     ($align -match 'sidecar rejected') { 'rejected' }
        elseif ($align -match 'ON \(solved\)')    { 'solved'   }
        elseif ($align -match 'ON \(sidecar\)')   { 'sidecar'  }
        elseif ($align -match 'OFF')              { 'off'      }
        else                                      { 'unknown'  }

    $rows += [pscustomobject]@{
        Render    = $log.BaseName
        Source    = $src
        Shared    = $shared
        Class     = $class
        Alignment = $align
    }
}

$rows | Format-Table Render, Class, Shared, Source -AutoSize

Write-Output ''
Write-Output '=== provenance summary ==='
$rows | Group-Object Class | Sort-Object Name |
    ForEach-Object { '{0,-9} {1}' -f $_.Name, $_.Count }

Write-Output ''
Write-Output '=== renders that CONSUMED a sidecar while reading a SHARED directory ==='
Write-Output '(this is the only class the hazard can contaminate)'
$exposed = $rows | Where-Object { $_.Class -eq 'sidecar' -and $_.Shared }
if ($exposed) {
    $exposed | ForEach-Object { '  ' + $_.Render + '  ' + $_.Alignment }
    Write-Output ''
    Write-Output 'Each of the above must be shown to have consumed a sidecar written'
    Write-Output 'by an earlier render of the SAME bracket in the SAME script. See'
    Write-Output 'section 4.10: v2-auto-299 rejected a foreign 60-frame map and rewrote'
    Write-Output 'the file at 299 frames, and v3/v4 then consumed that map.'
} else {
    Write-Output '  (none)'
}

Write-Output ''
Write-Output '=== refusals: the sidecar guard firing, with both digests ==='
Write-Output '(positive control for the notice claim that stale maps are silent)'
$rows | Where-Object { $_.Class -eq 'rejected' } |
    ForEach-Object { '  ' + $_.Render + '  ' + $_.Alignment }

Write-Output ''
Write-Output '=== reference-frame determinism ==='
Write-Output '(if the reference frame is a function of frame count alone, it cannot'
Write-Output ' drift under a fixed bracket, which narrows the hazard to the resampler)'
foreach ($r in $rows) {
    $log = Join-Path $dataDir ($r.Render + '.log')
    $f = (Select-String -Path $log -Pattern 'frames\s*:\s*(\d+)' | Select-Object -First 1)
    $a = (Select-String -Path $log -Pattern 'reference frame (\d+)' | Select-Object -First 1)
    if ($f -and $a) {
        $n = [int]$f.Matches[0].Groups[1].Value
        $ref = [int]$a.Matches[0].Groups[1].Value
        $expect = [math]::Floor($n / 2)
        $ok = if ($ref -eq $expect) { 'floor(n/2)' } else { 'DEVIATES' }
        '  {0,-22} n={1,-4} ref={2,-4} {3}' -f $r.Render, $n, $ref, $ok
    }
}
