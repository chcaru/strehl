# Baseline the desktop's paint and preview benchmarks before Studio 2 changes.
# Read-only on the capture folder. Usage:
#   ./experiments/desktop-studio-2-impl/perf/run-baseline.ps1 -Label baseline -TargetDir target-bench
param(
    [string]$Label = "baseline",
    [string]$TargetDir = "target-bench",
    [string]$Bracket = "D:\personal\macro\insects\bug-3\107MSDCF"
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
Set-Location $root
$out = Join-Path $PSScriptRoot $Label
New-Item -ItemType Directory -Force $out | Out-Null
$env:CARGO_TARGET_DIR = Join-Path $root $TargetDir
$build = git rev-parse --short HEAD
"build $build  started $(Get-Date -Format o)" | Set-Content (Join-Path $out "run.txt")
Get-CimInstance Win32_Processor | Select-Object -ExpandProperty LoadPercentage | ForEach-Object { "cpu load at start: $_ %" } | Add-Content (Join-Path $out "run.txt")

# 1. Full-workspace CPU paint + tessellation, 130 synthetic captures (not GPU frame rate).
cargo test --locked --release -p strehl-ui -- --ignored benchmark_finished_workspace_pointer_sweeps --nocapture *> (Join-Path $out "pointer-sweeps.txt")
"pointer sweeps exit $LASTEXITCODE" | Add-Content (Join-Path $out "run.txt")

# 2. Real-RAW scrub publication through SourceBrowser at 8 ms input cadence.
$env:STREHL_UI_BENCH_SOURCE = $Bracket
$env:STREHL_UI_BENCH_REPORT = Join-Path $out "resident-299.json"
cargo test --locked --release -p strehl-ui -- --ignored benchmark_real_stack_scrub_publication --nocapture *> (Join-Path $out "resident-299.txt")
"resident exit $LASTEXITCODE" | Add-Content (Join-Path $out "run.txt")
"finished $(Get-Date -Format o)" | Add-Content (Join-Path $out "run.txt")
