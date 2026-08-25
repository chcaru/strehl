# M87 -- does `2>&1 | Out-String` preserve a nonzero exit code?
#
# Tonight's entire verification suite reads $LASTEXITCODE after
# `python <verifier> 2>&1 | Out-String`, and its PASS criterion is code 0.
# That is the direction the truncation trap manufactures: a real failure
# would be read as a pass.  The orchestrator states Out-String is safe
# "by construction" because it must drain the stream, but they had already
# been wrong once about this mechanism (a count framing that does not
# survive measurement), so the claim is measured here rather than inherited.
#
# Design notes:
#
#   * PRE-CLEAR.  $LASTEXITCODE retains the previous command's value, so an
#     arm that fails to set it reads stale rather than 0.  Without the
#     pre-clear every arm inherits the preceding arm's 1 and the trap is
#     invisible -- a false negative.  Each arm is preceded by `cmd /c exit 0`
#     and the pre-clear is itself asserted.
#
#   * POSITIVE CONTROL.  If no arm reproduces the trap, an all-safe result
#     means "not reproduced here", not "my shape is safe".  The `-First`
#     arms are the commissioning: the run is INCONCLUSIVE unless at least
#     one of them reads 0.
#
#   * VOLUME LADDER.  The trap is a race, not a count, so the arms are run
#     across output sizes bracketing real verifier output (~10-200 lines).
#
# The emitter is generated into $env:TEMP on purpose: a helper .py under
# src/ would land in verify_s32's script audit and move P124's denominator
# for a file that measures nothing about any image.  Passing it via
# `python -c` was tried first and failed -- PowerShell mangles the embedded
# quotes when splatting a multi-line program into a native argument.

param([int[]]$Sizes = @(10, 200, 5000))

$ErrorActionPreference = 'Stop'

$emit = Join-Path $env:TEMP 'm87_exitcode_emit.py'
@(
    'import sys'
    'n = int(sys.argv[1])'
    'pad = "x" * 60'
    'for i in range(n):'
    '    print("noise line %d %s" % (i, pad))'
    'sys.exit(1)'
) -join "`r`n" | Set-Content -Path $emit -Encoding ascii

# commission the emitter itself: it must really exit 1
cmd /c exit 0
& python $emit 1 > $null 2>&1
if ($LASTEXITCODE -ne 1) { throw "emitter does not exit 1 (read $LASTEXITCODE)" }

function Reset-Code {
    param([string]$Arm)
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "PRE-CLEAR FAILED before arm '$Arm'" }
}

$rows = @()

foreach ($n in $Sizes) {

    Reset-Code "capture-first/$n"
    $o = & python $emit $n 2>&1
    $rows += [pscustomobject]@{ n = $n; arm = 'capture-first'; code = $LASTEXITCODE; corrupt = $false }

    Reset-Code "Out-String/$n"
    $o = & python $emit $n 2>&1 | Out-String
    $rows += [pscustomobject]@{ n = $n; arm = 'Out-String'; code = $LASTEXITCODE; corrupt = $false }

    Reset-Code "Out-String -Width/$n"
    $o = & python $emit $n 2>&1 | Out-String -Width 140
    $rows += [pscustomobject]@{ n = $n; arm = 'Out-String -Width'; code = $LASTEXITCODE; corrupt = $false }

    Reset-Code "Select-Object -Last 3/$n"
    $o = & python $emit $n 2>&1 | Select-Object -Last 3
    $rows += [pscustomobject]@{ n = $n; arm = 'Select-Object -Last 3'; code = $LASTEXITCODE; corrupt = $false }

    Reset-Code "Select-Object -First 3/$n"
    $o = & python $emit $n 2>&1 | Select-Object -First 3
    $rows += [pscustomobject]@{ n = $n; arm = 'Select-Object -First 3'; code = $LASTEXITCODE; corrupt = $true }

    Reset-Code "Select-String|-First 3/$n"
    $o = & python $emit $n 2>&1 | Select-String 'noise' | Select-Object -First 3
    $rows += [pscustomobject]@{ n = $n; arm = 'Select-String |-First 3'; code = $LASTEXITCODE; corrupt = $true }
}

# ---- also test the exact shape tonight's gates used --------------------
foreach ($n in $Sizes) {
    Reset-Code "GATE-SHAPE/$n"
    $out = & python $emit $n 2>&1 | Out-String
    $c = $LASTEXITCODE
    $null = ($out -split "`r?`n" | Where-Object { $_ -match 'noise' } | Select-Object -Last 1)
    $rows += [pscustomobject]@{ n = $n; arm = 'GATE SHAPE (tonight)'; code = $c; corrupt = $false }
}

$rows | Format-Table -AutoSize | Out-String -Width 120 | Write-Output

# The TRUE code is 1 (the emitter is commissioned above).  A trap arm is
# "corrupted" when it reports anything other than 1 -- NOT specifically 0.
# The first draft of this probe registered `expect = 0`, which encoded the
# orchestrator's reported VALUE rather than the property under test, and on
# this host the trap reports -1.  The gate correctly refused to certify, but
# the expectation was inherited rather than derived.
$TRUE_CODE = 1
$trapArms = @($rows | Where-Object { $_.corrupt })
$trapHit  = @($trapArms | Where-Object { $_.code -ne $TRUE_CODE })
$safeArms = @($rows | Where-Object { -not $_.corrupt })
$safeBad  = @($safeArms | Where-Object { $_.code -ne $TRUE_CODE })

$vals = ($trapHit | ForEach-Object { $_.code } | Sort-Object -Unique) -join ', '
Write-Output "true exit code of the emitter: $TRUE_CODE"
Write-Output "trap reproduced in $($trapHit.Count) of $($trapArms.Count) -First arms; corrupted value(s) observed: $vals"
Write-Output "safe-shape arms reporting the true code: $($safeArms.Count - $safeBad.Count) of $($safeArms.Count)"
Write-Output "PSVersion: $($PSVersionTable.PSVersion)"

$out = [pscustomobject]@{
    ps_version      = "$($PSVersionTable.PSVersion)"
    true_code       = $TRUE_CODE
    sizes           = $Sizes
    trap_arms       = $trapArms.Count
    trap_hit        = $trapHit.Count
    corrupt_values  = @($trapHit | ForEach-Object { $_.code } | Sort-Object -Unique)
    safe_arms       = $safeArms.Count
    safe_ok         = $safeArms.Count - $safeBad.Count
    rows            = $rows
}
$dest = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\exitcode-probe.json'
$out | ConvertTo-Json -Depth 5 | Set-Content -Path $dest -Encoding utf8
Write-Output "wrote $dest"

if ($trapHit.Count -eq 0) {
    Write-Output 'VERDICT: INCONCLUSIVE -- the positive control never fired, so this run cannot distinguish "safe" from "not reproduced".'
    exit 2
}
if ($safeBad.Count -gt 0) {
    Write-Output 'VERDICT: RED -- a shape tonight''s gates rely on lost the exit code:'
    $safeBad | ForEach-Object { Write-Output "  n=$($_.n) $($_.arm) read $($_.code), expected $TRUE_CODE" }
    exit 1
}
Write-Output 'VERDICT: GREEN -- every shape tonight''s gates used reported the true code, on a run where the trap demonstrably fires.'
exit 0


