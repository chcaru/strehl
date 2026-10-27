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
# The workspace's egui-wgpu patch is a required path dependency, not a registry
# replacement that Cargo can fetch. Preserve its declared source and notices.
$patchedCrate = Join-Path $repository 'third-party/egui-wgpu'
foreach ($name in @('Cargo.toml', 'LICENSE-APACHE', 'LICENSE-MIT', 'STREHL-PATCH.md', 'README.md')) {
    $file = Get-Item -LiteralPath (Join-Path $patchedCrate $name)
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a non-file or linked patched-crate source: $($file.FullName)"
    }
    $relativeFiles.Add([IO.Path]::GetRelativePath($repository, $file.FullName))
}
foreach ($entry in Get-ChildItem -LiteralPath (Join-Path $patchedCrate 'src') -Recurse -Force) {
    if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a linked patched-crate source: $($entry.FullName)"
    }
    if (!$entry.PSIsContainer -and $entry.Extension -in @('.rs', '.wgsl')) {
        $relativeFiles.Add([IO.Path]::GetRelativePath($repository, $entry.FullName))
    }
}
# These example targets and test includes are outside crates/. Keep their owned
# Rust source and compact saved regression reference with the snapshot.
# Original captures, firmware, and generated image outputs are not copied.
foreach ($relative in @(
    'experiments/rea-a7c2-2026-10-24-c/noise-floor-oracle.rs',
    'experiments/rea-a7c2-2026-10-24-c/matched-display.rs',
    'experiments/rea-a7c2-2026-10-24-c/noise-floor-gather.rs',
    'experiments/rea-a7c2-2026-10-24-c/noise-floor-reconstruction.rs',
    'experiments/rea-a7c2-2026-10-24-d/temporal-finish.rs',
    'experiments/rea-a7c2-2026-10-24-d/normal-cpu-fixture.rs',
    'experiments/rea-a7c2-2026-10-24-d/raw-dark-audit.rs',
    'experiments/rea-a7c2-2026-10-24-i/native-roi/raw-roi-export.rs',
    'experiments/rea-a7c2-2026-10-24-k/native-roi/raw-roi-export.rs',
    'experiments/rea-a7c2-2026-10-24-n/native-roi/raw-roi-export.rs',
    'experiments/rea-a7c2-2026-10-24-q/native-roi/raw-roi-export.rs',
    'experiments/rea-a7c2-2026-10-24-v/component-tests.rs',
    'experiments/rea-a7c2-2026-10-24-v/fixture.rs',
    'experiments/rea-a7c2-2026-10-24-v/cli-tests.rs',
    'experiments/rea-a7c2-2026-10-24-v/override-tests.rs',
    'experiments/rea-a7c2-2026-10-24-v/override-fixture.rs',
    'experiments/M103-halfdrift/data/truth-dense.json'
)) {
    $file = Get-Item -LiteralPath (Join-Path $repository $relative)
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a non-file or linked source: $relative"
    }
    $relativeFiles.Add($relative)
}
$relativeFiles.Add('scripts/rebuild-desktop.ps1')
$relativeFiles.Add('scripts/package-desktop.ps1')
$relativeFiles.Add('scripts/strehl-control.py')
$relativeFiles.Add('docs/desktop-control.md')
$relativeFiles.Add('docs/desktop-build.md')
$relativeFiles.Add('docs/public-release.md')
$relativeFiles.Add('SECURITY.md')
$relativeFiles.Add('docs/desktop-settings-audit.md')
$relativeFiles.Add('docs/temporal-energy.md')
$relativeFiles.Add('docs/sony-focus-metadata.md')
$relativeFiles.Add('docs/research/metadata-continuation-2026-10-25.md')
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
    # Compiled through the desktop dependency; the saved recipe defaults Off.
    experimental_features = @('temporal-energy')
    experimental_defaults = [ordered]@{ temporal_energy = 'off' }
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
$rebuildGuide = $rebuildGuide.Replace('](desktop-control.md)', '](source/docs/desktop-control.md)')
$rebuildGuide = $rebuildGuide.Replace('](temporal-energy.md)', '](source/docs/temporal-energy.md)')
$rebuildGuide = $rebuildGuide.Replace('](raw-decoder-notice.md)', '](source/docs/raw-decoder-notice.md)')
[IO.File]::WriteAllText((Join-Path $package 'REBUILD.md'), $rebuildGuide)
$packageReadme = @'
# Strehl: native metadata and application control

Open **Strehl.exe** for the desktop workspace. Import a bracket, select a capture
on the timeline, and open **Camera metadata**. The native panel contains the AF
grid, exact cell bits and flags, focus progression and optical sample curves.
Selecting a chart point selects its capture. Full details stay inside Strehl.
The panel caches one bracket read; Refresh rereads it. Values remain raw camera
observations, with uncalibrated physical units and measurement freshness.

For control without mouse or keyboard automation, use the supplied
[control helper](source/scripts/strehl-control.py) and follow the
[desktop control guide](source/docs/desktop-control.md). The helper can launch an
isolated headless workspace, read snapshots and metadata, issue revision-checked
commands, export, and request an orderly shutdown. It requires Python 3.9 or later;
Strehl's native `--control` client also works without Python.

The same guide explains [offscreen UI rendering](source/docs/desktop-control.md#check-the-ui-without-opening-a-window):
`--offscreen-screenshot` saves the real native workspace to PNG through egui/wgpu
without opening an operating-system window. `--metadata` includes the bracket
explorer. This path needs a graphics backend and uses a separate output/state
folder; ordinary headless command control does not require a GPU renderer.

See the [desktop guide](source/crates/strehl-ui/README.md) for normal controls and
[Sony metadata guide](source/docs/sony-focus-metadata.md) for formats and limits.
**strehl-cli.exe** exposes the separate engine commands; its HTML metadata export
is optional.

The matching sources, rebuild manifest and scripts are in **source/** and
**strehl-source.zip**. Follow [REBUILD.md](REBUILD.md) and keep the
[decoder notice](RAW-DECODER-NOTICE.md) and license files with redistributed binaries.
'@
[IO.File]::WriteAllText((Join-Path $package 'README.md'), $packageReadme.TrimEnd() + "`n")
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
    files = @('Strehl.exe', 'strehl-cli.exe', 'strehl-source.zip', 'README.md', 'REBUILD.md',
        'RAW-DECODER-NOTICE.md', 'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-LGPL-2.1') | ForEach-Object {
        $path = Join-Path $package $_
        [ordered]@{ path = $_; bytes = (Get-Item -LiteralPath $path).Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $package 'desktop-package.json') -Encoding utf8
Write-Output "Built desktop package at $package"
