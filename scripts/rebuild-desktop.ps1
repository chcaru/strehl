[CmdletBinding()]
param([string]$TargetDirectory = 'target-desktop')

$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $sourceRoot 'desktop-source.json') -Raw | ConvertFrom-Json
$compiler = (& rustc --version --verbose) -join "`n"
if ($LASTEXITCODE -ne 0 -or $compiler -ne $manifest.rustc) {
    throw "Use the Rust toolchain recorded in desktop-source.json ($($manifest.toolchain)); the current compiler differs."
}
foreach ($entry in $manifest.files) {
    $path = Join-Path $sourceRoot $entry.path
    if (!(Test-Path -LiteralPath $path -PathType Leaf) -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "Source manifest mismatch: $($entry.path)"
    }
}
$previousStamp = $env:STREHL_BUILD_ID
$previousFlags = $env:RUSTFLAGS
$previousEncodedFlags = $env:CARGO_ENCODED_RUSTFLAGS
$ambientBuildOverrides = @(Get-ChildItem Env: | Where-Object {
    $_.Name -match '^CARGO_(BUILD_TARGET|BUILD_RUSTFLAGS|TARGET_.*_RUSTFLAGS|PROFILE_RELEASE_.*)$'
})
try {
    $env:STREHL_BUILD_ID = $manifest.build_id
    $env:RUSTFLAGS = ''
    $env:CARGO_ENCODED_RUSTFLAGS = ''
    # Record one recipe, not a recipe silently altered by the caller's profile
    # or target flags. Restore every override when this invocation completes.
    foreach ($override in $ambientBuildOverrides) {
        [Environment]::SetEnvironmentVariable($override.Name, $null, 'Process')
    }
    Push-Location $sourceRoot
    try {
        & cargo build --locked --release -p strehl-cli --bin strehl -p strehl-ui --bin strehl-ui --target-dir $TargetDirectory
        if ($LASTEXITCODE -ne 0) { throw 'The desktop rebuild failed.' }
    } finally { Pop-Location }
} finally {
    $env:STREHL_BUILD_ID = $previousStamp
    $env:RUSTFLAGS = $previousFlags
    $env:CARGO_ENCODED_RUSTFLAGS = $previousEncodedFlags
    foreach ($override in $ambientBuildOverrides) {
        [Environment]::SetEnvironmentVariable($override.Name, $override.Value, 'Process')
    }
}
