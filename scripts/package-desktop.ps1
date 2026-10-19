[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Destination,
    [string]$TargetDirectory = 'target-ui'
)

# Build the copied source snapshot, so a concurrent editor cannot silently make
# the binary differ from the source distributed beside it. Existing destinations
# are refused; no cleanup or recursive deletion is performed.
$ErrorActionPreference = 'Stop'
$repository = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$package = [IO.Path]::GetFullPath($Destination)
$target = [IO.Path]::GetFullPath($TargetDirectory)
if (Test-Path -LiteralPath $package) { throw 'Choose a new package destination.' }
$source = Join-Path $package 'source'
New-Item -ItemType Directory -Path $source | Out-Null

$relativeFiles = [Collections.Generic.List[string]]::new()
foreach ($name in @('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-LGPL-2.1')) {
    $relativeFiles.Add($name)
}
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $repository 'crates') -File -Recurse -Force) {
    if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a linked source file: $($file.FullName)"
    }
    $relativeFiles.Add([IO.Path]::GetRelativePath($repository, $file.FullName))
}
# Cargo resolves this optional path dependency even with every experimental
# feature disabled. Copy only the owned library sources, never experiment data.
$relativeFiles.Add('experiments/native-gpu-gather/Cargo.toml')
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $repository 'experiments/native-gpu-gather/src') -File -Recurse -Force) {
    $relativeFiles.Add([IO.Path]::GetRelativePath($repository, $file.FullName))
}
$relativeFiles.Add('scripts/rebuild-desktop.ps1')
$relativeFiles.Add('docs/desktop-build.md')
$relativeFiles.Add('docs/public-release.md')
$relativeFiles.Add('SECURITY.md')
$relativeFiles.Add('docs/desktop-settings-audit.md')
$relativeFiles.Add('docs/raw-decoder-notice.md')
foreach ($relative in $relativeFiles) {
    $copy = Join-Path $source $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $copy) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repository $relative) -Destination $copy
}
$entries = @($relativeFiles | Sort-Object | ForEach-Object {
    [ordered]@{ path = $_.Replace('\', '/'); sha256 = (Get-FileHash -LiteralPath (Join-Path $source $_) -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$hash = [Security.Cryptography.SHA256]::Create()
try {
    $manifestHash = [Convert]::ToHexString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes(($entries | ConvertTo-Json -Depth 3 -Compress)))).ToLowerInvariant()
} finally { $hash.Dispose() }
$compiler = (& rustc --version --verbose) -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'Rust is required to build the package.' }
$toolchain = ($compiler -split "`n" | Where-Object { $_.StartsWith('release: ') }).Substring(9)
$manifest = [ordered]@{
    schema = 1
    build_id = "desktop-$($manifestHash.Substring(0, 16))"
    toolchain = $toolchain
    rustc = $compiler
    source_sha256 = $manifestHash
    command = 'cargo build --locked --release -p strehl-cli --bin strehl -p strehl-ui --bin strehl-ui'
    experimental_features = @()
    files = $entries
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $source 'desktop-source.json') -Encoding utf8
& (Join-Path $source 'scripts/rebuild-desktop.ps1') -TargetDirectory $target
if ($LASTEXITCODE -ne 0) { throw 'Package build failed.' }
foreach ($name in @('strehl-ui.exe', 'strehl.exe')) {
    $binary = Join-Path $target "release/$name"
    $arguments = if ($name -eq 'strehl-ui.exe') { @('--engine-worker', '--version') } else { @('--version') }
    # PowerShell does not reliably attach stdout to a GUI-subsystem executable.
    # Explicit pipes also prove that the bundled worker starts without a window.
    $start = [Diagnostics.ProcessStartInfo]::new($binary)
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $arguments) { $start.ArgumentList.Add($argument) }
    $worker = [Diagnostics.Process]::Start($start)
    try {
        $stdout = $worker.StandardOutput.ReadToEndAsync()
        $stderr = $worker.StandardError.ReadToEndAsync()
        if (!$worker.WaitForExit(20000)) { $worker.Kill(); throw "$name version probe timed out" }
        $version = $stdout.GetAwaiter().GetResult()
        if ($worker.ExitCode -ne 0 -or !$version.Contains($manifest.build_id)) {
            throw "The built $name does not identify this source snapshot: $version $($stderr.GetAwaiter().GetResult())"
        }
    } finally {
        $worker.Dispose()
    }
    # Windows filenames are case-insensitive: the desktop owns Strehl.exe,
    # while the separate command-line utility has an explicit suffix.
    $packagedName = if ($name -eq 'strehl-ui.exe') { 'Strehl.exe' } else { 'strehl-cli.exe' }
    Copy-Item -LiteralPath $binary -Destination (Join-Path $package $packagedName)
}
$rebuildGuide = [IO.File]::ReadAllText((Join-Path $source 'docs/desktop-build.md'))
$rebuildGuide = $rebuildGuide.Replace('](public-release.md)', '](source/docs/public-release.md)')
[IO.File]::WriteAllText((Join-Path $package 'REBUILD.md'), $rebuildGuide)
Copy-Item -LiteralPath (Join-Path $source 'LICENSE-MIT') -Destination $package
Copy-Item -LiteralPath (Join-Path $source 'LICENSE-APACHE') -Destination $package
Copy-Item -LiteralPath (Join-Path $source 'LICENSE-LGPL-2.1') -Destination $package
Copy-Item -LiteralPath (Join-Path $source 'docs/raw-decoder-notice.md') -Destination (Join-Path $package 'RAW-DECODER-NOTICE.md')
Compress-Archive -LiteralPath $source -DestinationPath (Join-Path $package 'strehl-source.zip') -CompressionLevel Optimal
$receipt = [ordered]@{
    schema = 1
    build_id = $manifest.build_id
    source_sha256 = $manifestHash
    rustc = $compiler
    files = @('Strehl.exe', 'strehl-cli.exe', 'strehl-source.zip', 'REBUILD.md',
        'RAW-DECODER-NOTICE.md', 'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-LGPL-2.1') | ForEach-Object {
        $path = Join-Path $package $_
        [ordered]@{ path = $_; bytes = (Get-Item -LiteralPath $path).Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $package 'desktop-package.json') -Encoding utf8
Write-Output "Built desktop package at $package"
