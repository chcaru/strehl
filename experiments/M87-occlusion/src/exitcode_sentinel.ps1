# M87 -- does the trap COERCE the exit code, or RETAIN the primed value?
#
# ORCH fact 1507: the stale value is retained verbatim, not coerced. My P142
# probes pre-cleared to 0 and PS 7.6.5 read 0, which cannot distinguish
# "coerced to 0" from "my own pre-clear echoing back". PS 5.1 read -1, which is
# neither the pre-clear nor the true code, so that one is NOT stale-retention.
#
# The discriminator is a pre-clear to a value that is neither 0 nor the true
# code. Sentinel 7, emitter true code 1:
#
#   reads 7 -> RETAINED   (the primed value survives; ORCH/M111 model)
#   reads 0 -> COERCED    (the engine writes a zero of its own)
#   reads 1 -> LIVE       (no trap on this shape)
#
# REGISTERED BEFORE THE RUN (2026-08-24, prior to any data existing):
#   R1  -First 3 on 7.6.5 reads 7, not 0. If it reads 0, "corrupts to 0" is a
#       property of the engine after all and fact 1507 is incomplete.
#   R2  -First 3 on 5.1 reads -1, i.e. NEITHER sentinel nor true code, so 5.1
#       is a genuine write and not stale-retention.
#   R3  -Last 3 and Select-String read 1 on both engines (safe shapes).
#   R4  the sentinel is asserted to have taken before every arm, so a missing
#       trap cannot masquerade as a successful read.
#
# Exit-free by design so it can be dot-sourced into the agent shell.

function Invoke-SentinelProbe {
    param([int]$Reps = 10, [int]$Sentinel = 7, [int]$Lines = 50)

    # The trap is about a NATIVE process left unreaped. A PowerShell script
    # block emitter has no process to reap, so every shape reads the true code
    # and the probe would falsely certify -First as safe. Measured: with a
    # script block emitter, first3/last3/selstr all read 1 on 7.6.5.
    $emit = Join-Path $env:TEMP 'm87_sentinel_emit.py'
    @(
        'import sys'
        'n = int(sys.argv[1])'
        'for i in range(n):'
        '    print("line %d" % i)'
        'sys.exit(1)'
    ) -join "`r`n" | Set-Content -Path $emit -Encoding ascii

    cmd /c exit 0
    & python $emit 3 > $null 2>&1
    if ($LASTEXITCODE -ne 1) { throw "emitter does not exit 1 here (read $LASTEXITCODE)" }

    $results = @()
    $shapes = @('first3', 'last3', 'selstr')

    foreach ($k in $shapes) {
        $codes = @()
        for ($r = 0; $r -lt $Reps; $r++) {
            # R4: prime to the sentinel and assert it took.
            cmd /c exit $Sentinel
            if ($LASTEXITCODE -ne $Sentinel) { throw "SENTINEL PRIME FAILED (read $LASTEXITCODE)" }

            switch ($k) {
                'first3' { $null = & python $emit $Lines 2>&1 | Select-Object -First 3 }
                'last3'  { $null = & python $emit $Lines 2>&1 | Select-Object -Last 3 }
                'selstr' { $null = & python $emit $Lines 2>&1 | Select-String 'line' }
            }
            $codes += $LASTEXITCODE
        }
        $verdict = @($codes | Sort-Object -Unique) -join ','
        $results += [pscustomobject]@{
            engine   = $PSVersionTable.PSVersion.ToString()
            shape    = $k
            sentinel = $Sentinel
            truecode = 1
            codes    = $codes
            distinct = $verdict
            reads_sentinel = @($codes | Where-Object { $_ -eq $Sentinel }).Count
            reads_zero     = @($codes | Where-Object { $_ -eq 0 }).Count
            reads_true     = @($codes | Where-Object { $_ -eq 1 }).Count
        }
    }
    $results
}

$out = Invoke-SentinelProbe
$out | ForEach-Object {
    "{0,-8} {1,-8} sentinel={2} true=1  distinct=[{3}]  sent={4} zero={5} true={6}" -f `
        $_.engine, $_.shape, $_.sentinel, $_.distinct, $_.reads_sentinel, $_.reads_zero, $_.reads_true
}
$dest = Join-Path $PSScriptRoot '..\data'
$label = "ps" + $PSVersionTable.PSVersion.Major
$out | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $dest "exitcode-sentinel-$label.json") -Encoding utf8
"wrote exitcode-sentinel-$label.json"
