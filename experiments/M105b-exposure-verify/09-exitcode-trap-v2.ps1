# 09-exitcode-trap.ps1 -- does the truncated-pipeline $LASTEXITCODE trap affect
# this milestone's pass/fail gate, and under what condition does it fire?
#
# The orchestrator reports (10:35) that `... | Select-Object -First N` leaves
# $LASTEXITCODE reading 0 after a command that truly exited 1, and asks every
# agent to re-check any pass/fail gate built on such a pipeline.
#
# This milestone has exactly one exit-code read, at 01-render.ps1:26:
#
#     & $Exe @args 2>&1 | Out-File -FilePath $log -Encoding utf8
#     $code = $LASTEXITCODE
#
# FIRST ATTEMPT AND WHY IT IS PRESERVED IN THE REPORT: a 5-line subject was
# used, and the POSITIVE CONTROL DID NOT FIRE -- arm C read the correct code 1.
# That was not a clean bill of health, it was a blind instrument, and the script
# returned INCONCLUSIVE rather than a false all-clear. The reason is that
# `Select-Object -First N` stops the upstream by throwing
# StopUpstreamCommandsException; if the native process has ALREADY EXITED its
# code is recorded and $LASTEXITCODE is correct. The trap needs the process to
# still be RUNNING when the pipe is torn down. It is a RACE, not a property of
# truncation.
#
# So the subject below is deliberately long-running and high-volume.
#
# ARMS
#   A  truth        -- no pipeline; establishes the true exit code
#   C  POSITIVE CONTROL -- big subject, truncated well below the match count
#   D  NEGATIVE CONTROL -- big subject, -First above the match count, so the
#                          pipeline never truncates. Distinguishes "truncation"
#                          from "pipelines in general"; without it a firing
#                          arm C would not identify the cause.
#   E  UNDER TEST   -- 01-render.ps1's exact Out-File pattern, big subject
#   G  race demo    -- SMALL subject, truncated. Shows the trap is conditional.
#
# If arm C does not read 0, this instrument cannot see the trap and the verdict
# on arm E is worthless (disciplines 611, 615, 616).
#
# Writes only into data\. Touches no capture directory and builds nothing.
#
#   powershell -ExecutionPolicy Bypass -File 09-exitcode-trap.ps1

$ErrorActionPreference = 'Continue'
$dataDir = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$bigCmd   = Join-Path $dataDir '09-subject-big.cmd'
$smallCmd = Join-Path $dataDir '09-subject-small.cmd'

# Both subjects exit 1. The only difference is how long they keep the pipe open.
@'
@echo off
for /L %%i in (1,1,200000) do @echo line %%i
exit /b 1
'@ | Set-Content -Encoding ascii $bigCmd

@'
@echo off
echo line1
echo line2
echo line3
echo line4
echo line5
exit /b 1
'@ | Set-Content -Encoding ascii $smallCmd

$truth = 1
$results = [ordered]@{}

# --- ARM A: ground truth, no pipeline. ---
& cmd /c $smallCmd *> $null
$results['A truth (no pipeline)'] = $LASTEXITCODE

# --- ARM C: POSITIVE CONTROL. Big subject, truncated far below match count. ---
$null = & cmd /c $bigCmd 2>$null | Select-String 'line' | Select-Object -First 3
$results['C big + truncated'] = $LASTEXITCODE

# --- ARM D: NEGATIVE CONTROL. Big subject, -First never reached. ---
$null = & cmd /c $bigCmd 2>$null | Select-String 'line' | Select-Object -First 999999
$results['D big + no truncation'] = $LASTEXITCODE

# --- ARM E: THE ARM UNDER TEST. 01-render.ps1's pattern on the big subject. ---
$probe = Join-Path $dataDir '09-probe.log'
& cmd /c $bigCmd 2>&1 | Out-File -FilePath $probe -Encoding utf8
$results['E Out-File (01-render)'] = $LASTEXITCODE

# --- ARM G: small subject, truncated. Demonstrates the race. ---
$null = & cmd /c $smallCmd 2>$null | Select-String 'line' | Select-Object -First 3
$results['G small + truncated'] = $LASTEXITCODE

Remove-Item $probe -ErrorAction SilentlyContinue

Write-Output "PowerShell $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
Write-Output "subject exits 1 in every arm; big = 200000 lines, small = 5 lines"
Write-Output ''
foreach ($k in $results.Keys) {
    $v = $results[$k]
    # The distinction that decides whether the common idiom
    # `if ($code -ne 0) { throw }` is actually fooled:
    #   == truth -> correct
    #   == 0     -> FALSE GREEN, the dangerous case the notice describes
    #   else     -> wrong value, but still non-zero, so a -ne 0 gate still fires
    $verdict =
        if     ($v -eq $truth) { 'correct' }
        elseif ($v -eq 0)      { 'FALSE GREEN -- a -ne 0 gate passes' }
        else                   { "wrong value ($v), but a -ne 0 gate still fires" }
    '{0,-24} $LASTEXITCODE = {1,-3}  {2}' -f $k, $v, $verdict
}
Write-Output ''

if ($results['C big + truncated'] -eq $truth) {
    Write-Output 'POSITIVE CONTROL DID NOT FIRE -- instrument is blind.'
    Write-Output 'VERDICT: INCONCLUSIVE.'
    exit 2
}
if ($results['D big + no truncation'] -ne $truth) {
    Write-Output 'NEGATIVE CONTROL FAILED -- an untruncated pipeline also lost the'
    Write-Output 'code, so truncation is not the cause and arm C is misattributed.'
    Write-Output 'VERDICT: INCONCLUSIVE.'
    exit 2
}

Write-Output 'Positive control FIRED and negative control HELD, so this'
Write-Output 'instrument sees the trap and attributes it to truncation.'
Write-Output ''
if ($results['G small + truncated'] -eq $truth) {
    Write-Output 'REFINEMENT: arm G truncated an identical pipeline over a SHORT'
    Write-Output 'subject and read the code CORRECTLY. The trap therefore requires'
    Write-Output 'the upstream to still be running when the pipe is torn down.'
    Write-Output 'It is a RACE conditioned on output volume and timing, not a'
    Write-Output 'deterministic consequence of -First. That makes it more dangerous'
    Write-Output 'than stated: the same line can pass and fail on different inputs.'
    Write-Output ''
}

$armE = $results['E Out-File (01-render)']
if ($armE -eq $truth) {
    Write-Output "VERDICT: 01-render.ps1's gate is SOUND. Out-File consumes the"
    Write-Output 'entire pipeline, so no short-circuit is ever raised and the'
    Write-Output 'upstream always runs to completion. Confirmed here against the'
    Write-Output 'same subject that defeats arm C. No bar in this report is affected.'
    exit 0
} else {
    Write-Output "VERDICT: 01-render.ps1's gate is COMPROMISED. Every render this"
    Write-Output 'milestone recorded as succeeding must be re-checked.'
    exit 1
}
