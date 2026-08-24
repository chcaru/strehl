$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Record = Get-Content -Raw (Join-Path $Here "binary.json") | ConvertFrom-Json
$Solved = Get-Content -Raw (Join-Path $Here "ladder-results.json") | ConvertFrom-Json
$Binary = $Record.binary
$Rows = @(
    @{ Stack = "wrapped-text-1"; Flat = "32,1312,256,256"; Detail = "2208,672,256,256" },
    @{ Stack = "wrapped-text-2"; Flat = "32,672,256,256"; Detail = "3104,160,256,256" },
    @{ Stack = "109MSDCF"; Flat = "1440,416,256,256"; Detail = "1952,1056,256,256" },
    @{ Stack = "coffee-bean"; Flat = "32,416,256,256"; Detail = "1312,416,256,256" },
    @{ Stack = "foam"; Flat = "1312,288,256,256"; Detail = "160,1952,256,256" },
    @{ Stack = "bee-1"; Flat = "2720,1568,256,256"; Detail = "1952,672,256,256" }
)
$Directories = @{ "bee-1" = "bee-1-cpl" }

Push-Location $Repo
try {
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source differs from HEAD" }
    if ((Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant() -ne $Record.sha256) {
        throw "private binary hash differs from binary.json"
    }
    foreach ($Row in $Rows) {
        $Stack = $Row.Stack
        $Gates = @("0.90", "0.70", "0.50") | ForEach-Object {
            [double]$Solved.stacks.$Stack.solves.$_.gate
        }
        $GateText = @($Gates | ForEach-Object {
            $_.ToString("0.000000000", [Globalization.CultureInfo]::InvariantCulture)
        })
        $Directory = if ($Directories.ContainsKey($Stack)) { $Directories[$Stack] } else { $Stack }
        $InputDir = "D:\personal\macro\$Directory"
        $Invocation = "& '$Binary' stack '$InputDir' --gate $($GateText -join ' ') --flat-roi $($Row.Flat) --detail-roi $($Row.Detail)"
        $Started = [DateTime]::UtcNow.ToString("o")
        $Saved = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(
            & $Binary stack $InputDir --gate $GateText --flat-roi $Row.Flat --detail-roi $Row.Detail 2>&1 |
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
            "REQUESTS=0.90,0.70,0.50",
            "SOLVED_GATES=$($GateText -join ',')",
            "INVOCATION=$Invocation",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "confirm-$Stack.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) { throw "$Stack confirmation exited $Code" }
    }
} finally {
    Pop-Location
}
