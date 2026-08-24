$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Record = Get-Content -Raw (Join-Path $Here "binary.json") | ConvertFrom-Json
$Plan = Get-Content -Raw (Join-Path $Here "bee-refine-plan.json") | ConvertFrom-Json
$Binary = $Record.binary
$Directories = @{ "bee-1" = "bee-1-cpl"; "bee-2" = "bee-2-cpl"; "bee-3" = "bee-3-cpl" }
$Rois = @{
    "bee-1" = @{ Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
    "bee-2" = @{ Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
    "bee-3" = @{ Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
}

Push-Location $Repo
try {
    & git diff --quiet $Record.commit HEAD -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source differs from binary commit" }
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source has uncommitted changes" }
    if ((Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant() -ne $Record.sha256) {
        throw "private binary hash differs from binary.json"
    }
    foreach ($Row in $Plan.entries) {
        $Stack = $Row.stack
        $Request = [string]$Row.request
        $Iteration = [int]$Row.iteration
        $Gate = $Row.gate.ToString("R", [Globalization.CultureInfo]::InvariantCulture)
        $InputDir = "D:\personal\macro\$($Directories[$Stack])"
        $Roi = $Rois[$Stack]
        $Started = [DateTime]::UtcNow.ToString("o")
        $Saved = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(
            & $Binary stack $InputDir --gate $Gate --flat-roi $Roi.Flat --detail-roi $Roi.Detail 2>&1 |
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
            "DIRECTORY=$($Directories[$Stack])",
            "REQUEST=$Request",
            "ITERATION=$Iteration",
            "SOLVED_GATE=$Gate",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "bee-confirm-refine$Iteration-$Stack-$Request.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) { throw "$Stack S=$Request refinement exited $Code" }
    }
} finally {
    Pop-Location
}
