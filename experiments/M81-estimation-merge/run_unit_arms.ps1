$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Binary = Join-Path $Here "target-unit\release\strehl.exe"
$BinaryRecord = Get-Content -Raw (Join-Path $Here "unit-binary.json") | ConvertFrom-Json
$Unit = Get-Content -Raw (Join-Path $Here "unit-results.json") | ConvertFrom-Json
$Rows = @(
    @{ Stack = "wrapped-text-1"; Flat = "32,1312,256,256"; Detail = "2208,672,256,256" },
    @{ Stack = "109MSDCF"; Flat = "1440,416,256,256"; Detail = "1952,1056,256,256" },
    @{ Stack = "coffee-bean"; Flat = "32,416,256,256"; Detail = "1312,416,256,256" },
    @{ Stack = "foam"; Flat = "1312,288,256,256"; Detail = "160,1952,256,256" },
    @{ Stack = "bee-1"; Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
)

Push-Location $Repo
try {
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src/main.rs crates/strehl-cli/src/merge_cmd.rs
    if ($LASTEXITCODE -ne 0) {
        throw "owned/runtime Rust source differs from HEAD"
    }
    $Commit = $BinaryRecord.commit
    $Hash = (Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant()
    if ($BinaryRecord.sha256 -ne $Hash) {
        throw "binary hash differs from the frozen binary record"
    }
    foreach ($Row in $Rows) {
        $Stack = $Row.Stack
        $InputDir = "D:\personal\macro\$Stack"
        $Candidate = [double]$Unit.candidate_gate.$Stack
        $CandidateText = $Candidate.ToString("0.000000000", [Globalization.CultureInfo]::InvariantCulture)
        $Invocation = "& '$Binary' stack '$InputDir' --gate 4 $CandidateText --flat-roi $($Row.Flat) --detail-roi $($Row.Detail)"
        $Started = [DateTime]::UtcNow.ToString("o")
        $SavedErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(
            & $Binary stack $InputDir --gate 4 $CandidateText `
                --flat-roi $Row.Flat --detail-roi $Row.Detail 2>&1 |
                ForEach-Object { $_.ToString() }
        )
        $Code = $LASTEXITCODE
        $ErrorActionPreference = $SavedErrorAction
        $Finished = [DateTime]::UtcNow.ToString("o")
        $Lines = @(
            "commit=$Commit",
            "binary=$Binary",
            "sha256=$Hash",
            "STACK=$Stack",
            "CANDIDATE_GATE=$CandidateText",
            "INVOCATION=$Invocation",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "unit-arms-$Stack.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) {
            throw "$Stack paired arms exited $Code"
        }
    }
} finally {
    Pop-Location
}
