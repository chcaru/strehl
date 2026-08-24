$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Cargo = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
$Rustc = Join-Path $env:USERPROFILE ".cargo\bin\rustc.exe"
$Target = Join-Path $Here "target-m82"
$Log = Join-Path $Here "build.log"

if (-not (Test-Path $Cargo)) {
    throw "cargo not found at $Cargo"
}
$env:CARGO_TARGET_DIR = $Target
$env:RUSTFLAGS = "--cfg m82_private_build"

Push-Location $Repo
try {
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src Cargo.lock
    if ($LASTEXITCODE -ne 0) {
        throw "runtime Rust source differs from HEAD"
    }
    $Commit = (& git rev-parse HEAD).Trim()
    $Started = [DateTime]::UtcNow.ToString("o")
    $SavedErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Run = @(& $Cargo build --release --locked -p strehl-cli 2>&1 | ForEach-Object { $_.ToString() })
    $Code = $LASTEXITCODE
    $ErrorActionPreference = $SavedErrorAction
    $Finished = [DateTime]::UtcNow.ToString("o")
    $Lines = @(
        "commit=$Commit",
        "cargo=$(& $Cargo --version)",
        "rustc=$(& $Rustc --version)",
        "CARGO_TARGET_DIR=$Target",
        "RUSTFLAGS=$env:RUSTFLAGS",
        "started_utc=$Started"
    ) + $Run + @("exit=$Code", "finished_utc=$Finished")
    [IO.File]::WriteAllLines($Log, $Lines, [Text.UTF8Encoding]::new($false))
    $Lines | ForEach-Object { Write-Host $_ }
    if ($Code -ne 0) {
        throw "cargo build exited $Code"
    }
    if (-not ($Run | Select-String -SimpleMatch "Compiling strehl-cli")) {
        throw "build log has no Compiling strehl-cli line"
    }
    $Binary = Join-Path $Target "release\strehl.exe"
    $Hash = (Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant()
    @{
        commit = $Commit
        binary = $Binary
        sha256 = $Hash
        bytes = (Get-Item $Binary).Length
        cargo = (& $Cargo --version)
        rustc = (& $Rustc --version)
        rustflags = $env:RUSTFLAGS
    } | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 (Join-Path $Here "binary.json")
} finally {
    Pop-Location
}
