$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Record = Get-Content -Raw (Join-Path $Here "binary.json") | ConvertFrom-Json
$Plan = Get-Content -Raw (Join-Path $Here "refinement-plan.json") | ConvertFrom-Json
$Binary = $Record.binary
$Rois = @{
    "wrapped-text-1" = @{ Flat = "32,1312,256,256"; Detail = "2208,672,256,256" }
    "wrapped-text-2" = @{ Flat = "32,672,256,256"; Detail = "3104,160,256,256" }
    "109MSDCF" = @{ Flat = "1440,416,256,256"; Detail = "1952,1056,256,256" }
    "coffee-bean" = @{ Flat = "32,416,256,256"; Detail = "1312,416,256,256" }
    "foam" = @{ Flat = "1312,288,256,256"; Detail = "160,1952,256,256" }
    "bee-1" = @{ Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
}

Push-Location $Repo
try {
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source differs from HEAD" }
    if ((Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant() -ne $Record.sha256) {
        throw "private binary hash differs from binary.json"
    }
    foreach ($Entry in $Plan.entries) {
        $Stack = $Entry.stack
        $Request = $Entry.request
        $Iteration = [int]$Entry.iteration
        $Gate = ([double]$Entry.gate).ToString("0.000000000", [Globalization.CultureInfo]::InvariantCulture)
        $Flat = $Rois[$Stack].Flat
        $Detail = $Rois[$Stack].Detail
        $InputDir = "D:\personal\macro\$Stack"
        $Invocation = "& '$Binary' stack '$InputDir' --gate $Gate --flat-roi $Flat --detail-roi $Detail"
        $Started = [DateTime]::UtcNow.ToString("o")
        $Saved = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(
            & $Binary stack $InputDir --gate $Gate --flat-roi $Flat --detail-roi $Detail 2>&1 |
                ForEach-Object { $_.ToString() }
        )
        $Code = $LASTEXITCODE
        $ErrorActionPreference = $Saved
        $Finished = [DateTime]::UtcNow.ToString("o")
        $Lines = @(
            "commit=$($Record.commit)",
            "binary=$Binary",
            "sha256=$($Record.sha256)",
            "STACK=$Stack",
            "REQUEST=$Request",
            "ITERATION=$Iteration",
            "SOLVED_GATE=$Gate",
            "INVOCATION=$Invocation",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "confirm-refine$Iteration-$Stack-$Request.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) { throw "$Stack $Request refinement exited $Code" }
    }
} finally {
    Pop-Location
}
