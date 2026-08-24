# Extends ORCH's pipeline-shape safety table to the SHORT-CIRCUITING variants of
# the cmdlets it cleared. Facts 1507/1508 clear `Select-String` unqualified, but
# -Quiet and -List are the variants a pass/fail gate would most naturally reach
# for, and both can stop reading early. If either is unsafe, the table as
# written clears an unsafe shape -- a false clear, in the dangerous direction.
#
# Method: adversarial priming, both directions. Prime $LASTEXITCODE to P, run a
# high-volume native command whose true exit is T through the shape, read the
# code. read==T is live; read==P is stale. A shape is only SAFE if it is live in
# BOTH directions -- a stale read that happens to equal the truth proves nothing
# (fact 1508: the stale value is retained verbatim).

$ErrorActionPreference = "Continue"
$EMIT = Join-Path $PSScriptRoot "pipeline_shape_emit.cmd"
if (-not (Test-Path $EMIT)) { Write-Host "HARNESS: emit.cmd missing"; exit 3 }

function Prime([int]$p) {
    & cmd /c exit $p
    if ($LASTEXITCODE -ne $p) {
        Write-Host "HARNESS: priming did not take ($LASTEXITCODE != $p)"
        exit 3
    }
}

# Each shape is a scriptblock that consumes the pipeline. It must NOT read
# $LASTEXITCODE itself; the caller does that immediately afterwards.
$shapes = [ordered]@{
    "Select-Object -First 1"   = { & cmd /c $EMIT $args[0] | Select-Object -First 1 | Out-Null }
    "Select-Object -Last 1"    = { & cmd /c $EMIT $args[0] | Select-Object -Last 1 | Out-Null }
    "Select-String line1"      = { & cmd /c $EMIT $args[0] | Select-String 'line1' | Out-Null }
    "Select-String -Quiet"     = { & cmd /c $EMIT $args[0] | Select-String 'line1' -Quiet | Out-Null }
    "Select-String -List"      = { & cmd /c $EMIT $args[0] | Select-String 'line1' -List | Out-Null }
    "Where-Object"             = { & cmd /c $EMIT $args[0] | Where-Object { $_ -match 'line1' } | Out-Null }
    "ForEach-Object"           = { & cmd /c $EMIT $args[0] | ForEach-Object { $_ } | Out-Null }
    "Out-String -Stream"       = { & cmd /c $EMIT $args[0] | Out-String -Stream | Out-Null }
    "(no pipeline)"            = { $null = & cmd /c $EMIT $args[0] 2>&1 }
}

# direction A: prime SUCCESS, true failure  -> a stale read shows as false GREEN
# direction B: prime FAILURE, true success  -> a stale read shows as false RED
$cases = @(
    @{ Prime = 0; True = 7; Label = "A primed0 true7" },
    @{ Prime = 5; True = 0; Label = "B primed5 true0" }
)

Write-Host ("{0,-24} {1,-18} {2,-18} {3}" -f "shape", $cases[0].Label, $cases[1].Label, "verdict")
Write-Host ("-" * 82)

$unsafe = @()
foreach ($name in $shapes.Keys) {
    $reads = @()
    foreach ($c in $cases) {
        Prime $c.Prime
        $t0 = Get-Date
        & $shapes[$name] $c.True
        $code = $LASTEXITCODE          # immediately after; nothing between
        $ms = [int]((Get-Date) - $t0).TotalMilliseconds
        $reads += [pscustomobject]@{ Code = $code; True = $c.True; Prime = $c.Prime; Ms = $ms }
    }
    $live = ($reads | Where-Object { $_.Code -ne $_.True }).Count -eq 0
    if (-not $live) { $unsafe += $name }
    $cells = $reads | ForEach-Object {
        $mark = if ($_.Code -eq $_.True) { "ok" } elseif ($_.Code -eq $_.Prime) { "STALE" } else { "??" }
        "{0} {1,-5} {2,5}ms" -f $_.Code, $mark, $_.Ms
    }
    Write-Host ("{0,-24} {1,-18} {2,-18} {3}" -f $name, $cells[0], $cells[1],
                $(if ($live) { "SAFE" } else { "UNSAFE" }))
}

Write-Host ""
# Ground truth: the harness is only trustworthy if it REPRODUCES the one shape
# already measured unsafe. A run in which everything looks safe is far more
# likely to be a dead instrument than a refutation of facts 1507/1508.
if ($unsafe -notcontains "Select-Object -First 1") {
    Write-Host "HARNESS DEAD: -First 1 did not reproduce as UNSAFE; no other verdict here is trustworthy"
    exit 3
}
Write-Host ("positive control reproduced: -First 1 is UNSAFE")
Write-Host ("unsafe shapes: " + ($unsafe -join ", "))
exit 0
