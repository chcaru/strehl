# 13-verify-citations.ps1 -- check every commit hash this report cites against git.
#
# WHY THIS EXISTS. Section 4.14 cited two pre-registration commits. One,
# `7694309`, was real. The other, `dcb9e8d`, WAS INVENTED -- written into the
# report from memory about ten minutes after the commit was made, without
# looking it up. The real hash is `be627db`. It passed corpus_lint, it passed my
# own read of the section, and it would have shipped as a broken citation into a
# corpus whose whole verification model is grep.
#
# PD15's lesson applied to myself: prefer a rule a script can check to a rule an
# agent must recall. So the check is a script.
#
# EXIT CONTRACT (discipline 702 -- tool failure must not look like subject
# failure):
#   0  every cited hash resolves in this repository
#   1  SUBJECT failure: at least one cited hash does not resolve
#   2  TOOL failure: the report or git is unavailable. NOT a verdict.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$report = Join-Path $root 'docs\research\M105b-exposure-ship.md'

trap {
    Write-Output "TOOL FAILURE: $_"
    Write-Output 'This is NOT a verdict on the citations. Nothing was checked.'
    exit 2
}

if (-not (Test-Path $report)) { throw "report not found: $report" }
Push-Location $root

# THE FIRST VERSION OF THIS SCRIPT REPORTED exit 2 (TOOL) FOR A REAL SUBJECT
# FAILURE. Under $ErrorActionPreference='Stop', PowerShell promotes a native
# command's stderr to a TERMINATING error, so `git cat-file` writing
# "fatal: Not a valid object name dcb9e8d" -- which is the exact answer being
# asked for -- tripped the trap. That is discipline 702 inverted BY the gate
# built to honour it, and 01-render.ps1 already documents the same promotion.
# Probing a thing that is EXPECTED to fail must not run under 'Stop'.
$ErrorActionPreference = 'Continue'

$text = Get-Content $report -Raw
# A cited hash is 7-40 hex chars inside backticks. Require at least one digit so
# that ordinary backticked words made only of a-f ("added", "face") are not
# mistaken for hashes -- a false positive here would report a tool failure as a
# subject failure, which is the thing the exit contract exists to prevent.
$hits = [regex]::Matches($text, '`([0-9a-f]{7,40})`') |
    ForEach-Object { $_.Groups[1].Value } |
    Where-Object { $_ -match '[0-9]' } |
    Sort-Object -Unique

$bad = @()
foreach ($h in $hits) {
    & git cat-file -t $h *> $null
    if ($LASTEXITCODE -ne 0) { $bad += $h }
}
Pop-Location

# An unresolvable hash is not always a defect: PD20 and section 4.14(j) QUOTE the
# fabricated hash on purpose, as the specimen this gate exists to catch. So there
# has to be an exception -- and an exception list is exactly how a gate gets
# quietly neutered, so it is constrained three ways: every entry carries a
# written reason, every excused token is printed loudly rather than skipped in
# silence, and an entry that no longer appears in the document is itself an
# error. A stale excuse is how a gate stops checking without anyone noticing.
$excused = @{
    'dcb9e8d'  = 'PD20 / 4.14(j): quoted deliberately as the fabricated citation this gate was built to catch'
    'deadbee1' = '4.14(j) control table: the planted hash of the negative control, never a real object'
    '0000000'  = '4.14(j) control table: the deliberately stale exception used to exercise the stale arm'
}

$stale = @($excused.Keys | Where-Object { $hits -notcontains $_ })
$unexcused = @($bad | Where-Object { -not $excused.ContainsKey($_) })
$excusedHit = @($bad | Where-Object { $excused.ContainsKey($_) })

Write-Output "checked $($hits.Count) distinct backticked hash-like token(s) in"
Write-Output "  $report"
foreach ($h in $hits) {
    $mark = if ($excusedHit -contains $h) { 'UNRESOLVED (excused)' }
            elseif ($bad -contains $h)    { 'UNRESOLVED' }
            else                          { 'ok' }
    Write-Output ("  {0,-42} {1}" -f $h, $mark)
}

foreach ($h in $excusedHit) {
    Write-Output ''
    Write-Output "EXCUSED: $h"
    Write-Output "  reason: $($excused[$h])"
}

if ($stale.Count -gt 0) {
    Write-Output ''
    Write-Output "SUBJECT FAILURE: $($stale.Count) stale exception(s) -- excused but no"
    Write-Output 'longer present in the document. A stale excuse silently narrows the gate:'
    foreach ($h in $stale) { Write-Output "  $h" }
    exit 1
}

if ($unexcused.Count -gt 0) {
    Write-Output ''
    Write-Output "SUBJECT FAILURE: $($unexcused.Count) cited hash(es) do not resolve:"
    foreach ($h in $unexcused) { Write-Output "  $h" }
    exit 1
}
Write-Output ''
Write-Output "OK -- every cited hash resolves ($($excusedHit.Count) excused by name)."
exit 0
