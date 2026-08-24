$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Record = Get-Content -Raw (Join-Path $Here "binary.json") | ConvertFrom-Json
$Binary = $Record.binary
$Gates = @("0", "0.25", "0.5", "1", "2", "4", "8", "16", "24", "32", "40", "48", "64", "96", "128")
$Rows = @(
    @{ Stack = "bee-1"; Directory = "bee-1-cpl" },
    @{ Stack = "bee-2"; Directory = "bee-2-cpl" },
    @{ Stack = "bee-3"; Directory = "bee-3-cpl" }
)

Push-Location $Repo
try {
    & git diff --quiet $Record.commit HEAD -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source differs from binary commit" }
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) { throw "runtime Rust source has uncommitted changes" }
    if ((Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant() -ne $Record.sha256) {
        throw "private binary hash differs from binary.json"
    }
    foreach ($Row in $Rows) {
        $Stack = $Row.Stack
        $InputDir = "D:\personal\macro\$($Row.Directory)"
        if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
            throw "missing input directory $InputDir"
        }
        $Invocation = "& '$Binary' stack '$InputDir' --gate $($Gates -join ' ')"
        $Started = [DateTime]::UtcNow.ToString("o")
        $Saved = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(& $Binary stack $InputDir --gate $Gates 2>&1 | ForEach-Object { $_.ToString() })
        $Code = $LASTEXITCODE
        $ErrorActionPreference = $Saved
        $Finished = [DateTime]::UtcNow.ToString("o")
        $Lines = @(
            "commit=$($Record.commit)",
            "binary=$Binary",
            "sha256=$($Record.sha256)",
            "STACK=$Stack",
            "DIRECTORY=$($Row.Directory)",
            "INVOCATION=$Invocation",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "bee-ladder-$Stack.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) { throw "$Stack ladder exited $Code" }
    }
} finally {
    Pop-Location
}
