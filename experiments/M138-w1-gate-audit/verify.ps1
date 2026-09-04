param(
    [switch]$SelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Results = Join-Path (Split-Path -Parent $Here) "PHASE1-DESIGN\results"
$Out = Join-Path $Here "out"
$Captures = @("flat-on-ruler", "coffee-bubbles", "113MSDCF")
$Rois = @("detail", "flat")

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Get-Intersection {
    param([object[]]$Sets)
    if ($Sets.Count -eq 0) {
        return @()
    }
    $result = @($Sets[0].Values)
    for ($i = 1; $i -lt $Sets.Count; $i++) {
        $lookup = [System.Collections.Generic.HashSet[double]]::new()
        foreach ($value in @($Sets[$i].Values)) {
            [void]$lookup.Add([double]$value)
        }
        $result = @($result | Where-Object { $lookup.Contains([double]$_) })
    }
    return @($result | Sort-Object -Unique)
}

function Test-Series {
    param(
        [double]$Legacy,
        [object[]]$Candidate,
        [object[]]$StoredRatio,
        [object[]]$StoredError,
        [object[]]$Grid,
        [double]$Bar
    )
    Assert-True ($Legacy -gt 0 -and [double]::IsFinite($Legacy)) "invalid legacy width"
    Assert-True ($Candidate.Count -eq $Grid.Count) "candidate/grid length mismatch"
    Assert-True ($StoredRatio.Count -eq $Grid.Count) "ratio/grid length mismatch"
    Assert-True ($StoredError.Count -eq $Grid.Count) "error/grid length mismatch"
    $admissible = [System.Collections.Generic.List[double]]::new()
    for ($i = 0; $i -lt $Grid.Count; $i++) {
        $ratio = [double]$Candidate[$i] / $Legacy
        $error = [math]::Abs($ratio - 1.0)
        Assert-True ([math]::Abs($ratio - [double]$StoredRatio[$i]) -le 1e-12) "stored ratio mismatch"
        Assert-True ([math]::Abs($error - [double]$StoredError[$i]) -le 1e-12) "stored error mismatch"
        if ($i -gt 0) {
            Assert-True ([double]$Candidate[$i] + 1e-12 -ge [double]$Candidate[$i - 1]) "non-monotone candidate width"
        }
        if ($error -le $Bar + 1e-12) {
            $admissible.Add([double]$Grid[$i])
        }
    }
    return @($admissible)
}

if ($SelfTest) {
    $grid = @(0.0, 0.05, 0.10, 0.15, 0.20)
    $candidate = @(1.0, 1.9, 2.0, 2.1, 3.0)
    $ratio = @($candidate | ForEach-Object { [double]$_ / 2.0 })
    $error = @($ratio | ForEach-Object { [math]::Abs([double]$_ - 1.0) })
    [void](Test-Series 2.0 $candidate $ratio $error $grid 0.05)
    $common = Get-Intersection -Sets @(
        [pscustomobject]@{ Values = @(0.05, 0.10, 0.15) }
        [pscustomobject]@{ Values = @(0.10, 0.15, 0.20) }
    )
    Assert-True (
        @($common).Count -eq 2 -and
        [math]::Abs([double]$common[0] - 0.10) -le 1e-12 -and
        [math]::Abs([double]$common[1] - 0.15) -le 1e-12
    ) "overlap null failed: $(@($common) -join ',')"
    $plant = Get-Intersection -Sets @(
        [pscustomobject]@{ Values = @(0.0, 0.05) }
        [pscustomobject]@{ Values = @(0.15, 0.20) }
    )
    Assert-True (@($plant).Count -eq 0) "disjoint plant failed"
    $bad = @($ratio)
    $bad[2] += 0.01
    $fired = $false
    try {
        [void](Test-Series 2.0 $candidate $bad $error $grid 0.05)
    } catch {
        $fired = $true
    }
    Assert-True $fired "corrupted-ratio plant failed to fire"
    Write-Output "PowerShell self-test: overlap=null=GREEN disjoint=plant=RED corrupted-ratio=plant=RED"
    exit 0
}

$run = Get-Content -Raw (Join-Path $Results "run.json") | ConvertFrom-Json
$hashesBefore = [ordered]@{}
foreach ($property in $run.hashes.PSObject.Properties) {
    $path = Join-Path $Results $property.Name
    $got = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    Assert-True ($got -eq [string]$property.Value) "frozen hash mismatch: $($property.Name)"
    $hashesBefore[$property.Name] = $got
}

$manifest = Get-Content -Raw (Join-Path $Results "preregistered-manifest.json") | ConvertFrom-Json
$gate = Get-Content -Raw (Join-Path $Results "gate.json") | ConvertFrom-Json
$grid = @($manifest.analysis.k_grid)
$bar = [double]$gate.bars.width
$sets = [System.Collections.Generic.List[object]]::new()
$rows = [System.Collections.Generic.List[object]]::new()

foreach ($capture in $Captures) {
    $payload = Get-Content -Raw (Join-Path $Results "width-$capture.json") | ConvertFrom-Json
    foreach ($bandRow in $payload.bands) {
        foreach ($roi in $Rois) {
            $values = $bandRow.rois.$roi
            $admissible = @(
                Test-Series ([double]$values.legacy_mean_neff) @($values.candidate_mean_neff) `
                    @($values.ratio) @($values.width_error) $grid $bar
            )
            $sets.Add([pscustomobject]@{ Values = $admissible })
            $rows.Add(
                [pscustomobject]@{
                    capture = $capture
                    band = [int]$bandRow.band
                    roi = $roi
                    admissible = $admissible
                }
            )
        }
    }
}

$global = Get-Intersection -Sets @($sets)
$withAny = @($rows | Where-Object { @($_.admissible).Count -gt 0 }).Count
$withoutAny = @($rows | Where-Object { @($_.admissible).Count -eq 0 }).Count
$coarseWithAny = @($rows | Where-Object { $_.band -ge 4 -and @($_.admissible).Count -gt 0 }).Count
Assert-True ($rows.Count -eq 42) "expected 42 predicates"
Assert-True ($withAny -eq 16) "expected 16 predicates with an admissible k"
Assert-True ($withoutAny -eq 26) "expected 26 predicates without an admissible k"
Assert-True (@($global).Count -eq 0) "global intersection unexpectedly non-empty"
Assert-True ($coarseWithAny -eq 0) "a band 4-6 predicate unexpectedly has an admissible k"
Assert-True (@($gate.width_survivors).Count -eq 0) "gate records a width survivor"
Assert-True (@($gate.metrics.PSObject.Properties).Count -eq 0) "gate unexpectedly contains Pareto metrics"
Assert-True (@($gate.render_provenance.PSObject.Properties).Count -eq 0) "gate unexpectedly rendered candidates"

$hashesAfter = [ordered]@{}
foreach ($property in $run.hashes.PSObject.Properties) {
    $path = Join-Path $Results $property.Name
    $got = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    Assert-True ($got -eq $hashesBefore[$property.Name]) "frozen artifact changed during verification"
    $hashesAfter[$property.Name] = $got
}

$result = [ordered]@{
    status = "PASS"
    predicates = $rows.Count
    with_any_admissible_k = $withAny
    with_no_admissible_k = $withoutAny
    global_intersection = @($global)
    bands_4_through_6_with_any_admissible_k = $coarseWithAny
    pareto_metrics_empty = $true
    frozen_unchanged = $true
    hashes_before = $hashesBefore
    hashes_after = $hashesAfter
}
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$result | ConvertTo-Json -Depth 8 -Compress | Set-Content -Encoding utf8 (Join-Path $Out "independent-check.json")
Write-Output "PowerShell audit: predicates=42 with-any=16 none=26 global=EMPTY coarse-any=0 pareto=NOT_RENDERED"
