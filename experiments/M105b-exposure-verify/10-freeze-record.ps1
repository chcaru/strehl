# 10-freeze-record.ps1 -- emit the complete invocation beside every SHA-256 this
# milestone published.
#
# Requested by the orchestrator (11:27) after M106 spent 1.9 hours attributing a
# "broken freeze" that turned out to be one milestone's --gate spliced onto
# another milestone's baseline: "whenever you record a hash, record the ENTIRE
# invocation next to it -- directory, --limit, and explicitly --gate, even when
# you used the default."
#
# The finding this script encodes: THE TOOL ALREADY EMITS ALL OF IT. `strehl
# stack` prints `gates : 4.00` even when 4.0 is the default, and `frames : N
# from <dir>` which fixes both the directory and the effective --limit. So the
# missing information in the M106 incident was never unrecorded -- it was
# unretained. Milestones committed hashes without committing the tool's own
# report next to them.
#
# That makes the machine-checkable version cheap: parse the committed log, do
# not ask agents to remember. This script is a working sketch of that check.
#
# Reads only committed artefacts under data\. Writes data\10-freeze-record.json.
#
#   powershell -ExecutionPolicy Bypass -File 10-freeze-record.ps1

# Discipline 702: a gate must distinguish TOOL failure from SUBJECT failure, or
# a broken run and a failing run are the same observation. Before this trap,
# both a missing manifest (tool could not run) and an incomplete freeze record
# (subject is defective) exited 1, which is exactly the ambiguity the corpus
# linter had. Exit codes here are:
#
#   0  every freeze record is complete
#   1  SUBJECT failure -- a record lacks directory, frame count or gate
#   2  TOOL failure    -- this script could not run at all
#
trap {
    Write-Output ''
    Write-Output "TOOL FAILURE (exit 2): $($_.Exception.Message)"
    Write-Output 'This is the script failing, NOT a verdict about the freeze records.'
    exit 2
}

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $PSScriptRoot 'data'
$manifest = Join-Path $dataDir '01-render.json'

if (-not (Test-Path $manifest)) { throw "missing $manifest -- run 01-render.ps1 first" }

$renders = Get-Content $manifest -Raw | ConvertFrom-Json
$records = @()
$incomplete = @()

foreach ($r in $renders) {
    $log = Join-Path $dataDir ($r.name + '.log')
    if (-not (Test-Path $log)) { $incomplete += "$($r.name): no log"; continue }
    $text = Get-Content $log

    function Field($pattern) {
        $m = $text | Select-String -Pattern $pattern | Select-Object -First 1
        if ($m) { $m.Matches[0].Groups[1].Value.Trim() } else { $null }
    }

    # `gates : 4.00` is printed unconditionally, so the default is on the record
    # rather than implied. This is the field whose absence cost M106 1.9 hours.
    $gate   = Field '^gates\s+:\s+(.+?)\s*(\(|$)'
    $frames = Field '^frames\s+:\s+(\d+)\s+from'
    $dir    = Field '^frames\s+:\s+\d+\s+from\s+(.+)$'
    $align  = Field '^alignment\s+:\s+(.+)$'

    # A freeze record is only complete if every field that can move the output
    # is present. Missing any one of them is what makes a hash unreproducible.
    $missing = @()
    if (-not $gate)   { $missing += 'gate' }
    if (-not $frames) { $missing += 'frames' }
    if (-not $dir)    { $missing += 'dir' }
    if ($missing.Count -gt 0) { $incomplete += "$($r.name): missing $($missing -join ',')" }

    $records += [pscustomobject]@{
        name       = $r.name
        sha256     = $r.sha256
        exit       = $r.exit
        dir        = $dir
        frames     = $frames
        gate       = $gate
        extra_args = $r.args
        invocation = "strehl stack `"$dir`" --out <tif> $($r.args)".Trim()
        alignment  = $align
    }
}

$records | Select-Object name, frames, gate, sha256 |
    Format-Table -AutoSize | Out-String -Width 200 | Write-Output

Write-Output ''
Write-Output '=== completeness of each freeze record ==='
if ($incomplete.Count -eq 0) {
    Write-Output "  all $($records.Count) records carry dir, frame count and gate"
    Write-Output '  (gate is present because the binary prints it even at the default)'
} else {
    $incomplete | ForEach-Object { '  INCOMPLETE ' + $_ }
}

Write-Output ''
Write-Output '=== distinct invocations behind these hashes ==='
$records | Group-Object gate, frames | Sort-Object Name |
    ForEach-Object { '  gate={0}  n={1} render(s)' -f $_.Name, $_.Count }

$outFile = Join-Path $dataDir '10-freeze-record.json'
$records | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 $outFile
Write-Output ''
Write-Output "wrote $outFile"

# ---------------------------------------------------------------------------
# Second pass: the manifest above covers only the first render batch. Later
# batches (v3, v5c, v6*) were logged but their hashes were asserted in the
# report's prose without being retained in any committed data file -- which is
# precisely the M106 failure mode, in this milestone's own artefacts. Close it
# by hashing every surviving render and joining it to its log.
# ---------------------------------------------------------------------------
Write-Output ''
Write-Output '=== full freeze record: every surviving render, hashed from disk ==='
$renderDir = 'C:\dev\strehl-out\M105'
$full = @()
foreach ($log in (Get-ChildItem (Join-Path $dataDir '*.log') | Sort-Object Name)) {
    $name = $log.BaseName
    if ($name -like '0*-*') { continue }   # analysis logs, not renders
    $tif = Join-Path $renderDir "$name.tif"
    $text = Get-Content $log.FullName

    function LogField($pattern) {
        $m = $text | Select-String -Pattern $pattern | Select-Object -First 1
        if ($m) { $m.Matches[0].Groups[1].Value.Trim() } else { $null }
    }

    $full += [pscustomobject]@{
        name      = $name
        sha256    = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash } else { 'RENDER NOT RETAINED' }
        dir       = LogField '^frames\s+:\s+\d+\s+from\s+(.+)$'
        frames    = LogField '^frames\s+:\s+(\d+)\s+from'
        gate      = LogField '^gates\s+:\s+(.+?)\s*(\(|$)'
        alignment = LogField '^alignment\s+:\s+(.+)$'
    }
}

$full | Select-Object name, frames, gate, dir, sha256 |
    Format-Table -AutoSize | Out-String -Width 260 | Write-Output

$fullFile = Join-Path $dataDir '10-all-render-hashes.json'
$full | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 $fullFile
Write-Output "wrote $fullFile"

# Renders that agree byte-for-byte across DIFFERENT source directories are the
# strongest available evidence against sidecar contamination: an isolated copy
# no other agent knew about cannot have been perturbed by a shared sidecar.
Write-Output ''
Write-Output '=== identical bytes across DIFFERENT source directories ==='
$full | Where-Object { $_.sha256 -ne 'RENDER NOT RETAINED' } |
    Group-Object sha256 | Where-Object { ($_.Group.dir | Sort-Object -Unique).Count -gt 1 } |
    ForEach-Object {
        '  ' + $_.Name.Substring(0,16) + '...'
        $_.Group | ForEach-Object { '      {0,-20} {1,-4} {2}' -f $_.name, $_.frames, $_.dir }
        $_.Group | ForEach-Object { '      {0,-20} {1}' -f '', $_.alignment }
    }

if ($incomplete.Count -gt 0) {
    Write-Output ''
    Write-Output 'SUBJECT FAILURE (exit 1): a freeze record is incomplete.'
    exit 1
}
exit 0
