[CmdletBinding()]
param(
    [ValidateSet("All", "Summarize")]
    [string]$Mode = "All",
    [string]$CaptureRoot = "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Experiment = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Experiment "..\..")).Path
$Out = Join-Path $Experiment "out"
$Checker = Join-Path $Experiment "checker.py"
$Summary = Join-Path $Experiment "results.json"
$FixtureTarget = Join-Path $Out "fixture-target"
$InstrumentedTarget = Join-Path $Out "instrumented-target"
$Snapshot = Join-Path $Out "source-snapshot"
$Strehl = Join-Path $InstrumentedTarget "release\strehl.exe"

$Captures = @(
    [pscustomobject]@{ Name = "flat-et1s"; Directory = "flat-et1s-sw4-cpl"; Frames = 60 },
    [pscustomobject]@{ Name = "flat-et2.5s"; Directory = "flat-et2.5s-sw4-cpl"; Frames = 61 },
    [pscustomobject]@{ Name = "flat-et6s"; Directory = "flat-et6s-sw4-cpl"; Frames = 65 }
)

function Reset-OutputPath {
    param([Parameter(Mandatory)][string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = [IO.Path]::GetFullPath($Out) + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the experiment output: $full"
    }
    Remove-Item -LiteralPath $full -Recurse -Force -ErrorAction SilentlyContinue
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$Log
    )
    if ($Log) {
        & $File @Arguments *> $Log
    }
    else {
        & $File @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        if ($Log -and (Test-Path $Log)) {
            Get-Content -LiteralPath $Log -Tail 80
        }
        throw "$File failed with exit code $LASTEXITCODE"
    }
}

function Get-CaptureFingerprint {
    param([Parameter(Mandatory)][string]$Path)
    $files = @(Get-ChildItem -LiteralPath $Path -Force -Recurse -File | Sort-Object FullName)
    $text = ($files | ForEach-Object {
        "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)|$($_.Attributes)"
    }) -join "`n"
    $bytes = [Text.Encoding]::UTF8.GetBytes($text)
    [pscustomobject]@{
        path = $Path
        files = $files.Count
        bytes = ($files | Measure-Object Length -Sum).Sum
        metadata_sha256 = [Convert]::ToHexString(
            [Security.Cryptography.SHA256]::HashData($bytes)
        )
    }
}

function Write-InputSnapshot {
    param([Parameter(Mandatory)][string]$Path)
    $rows = foreach ($capture in $Captures) {
        Get-CaptureFingerprint (Join-Path $CaptureRoot $capture.Directory)
    }
    [pscustomobject]@{
        captured_utc = (Get-Date).ToUniversalTime().ToString("o")
        method = "Get-ChildItem -Force -Recurse; SHA-256(path|length|mtime_utc_ticks|attributes)"
        captures = @($rows)
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Invoke-Commissioning {
    $commission = Join-Path $Out "commission"
    Reset-OutputPath $commission
    $blocks = Join-Path $commission "blocks"
    New-Item -ItemType Directory -Force -Path $blocks | Out-Null
    $fixture = Join-Path $FixtureTarget "release\m8-overshoot-fixture.exe"
    Invoke-Checked $fixture @("commission", $blocks)
    foreach ($block in Get-ChildItem -LiteralPath $blocks -Filter "*.m8site" -File) {
        $state = Join-Path $commission $block.BaseName
        Invoke-Checked "python" @(
            "-B", $Checker, "consume", "--block", $block.FullName,
            "--state", $state, "--capture", $block.BaseName
        )
        Invoke-Checked "python" @("-B", $Checker, "finalize-r", "--state", $state)
    }
    Invoke-Checked "python" @(
        "-B", $Checker, "commission-assert", "--root", $commission
    ) (Join-Path $commission "commission.txt")
}

function New-InstrumentedBuild {
    Reset-OutputPath $Snapshot
    New-Item -ItemType Directory -Force -Path $Snapshot | Out-Null
    Copy-Item -LiteralPath @(
        (Join-Path $Repo "Cargo.toml"),
        (Join-Path $Repo "Cargo.lock"),
        (Join-Path $Repo "rust-toolchain.toml")
    ) -Destination $Snapshot
    Copy-Item -LiteralPath (Join-Path $Repo "crates") -Destination $Snapshot -Recurse
    Invoke-Checked "python" @(
        "-B", (Join-Path $Experiment "inject_trace.py"), $Snapshot,
        "--hook", (Join-Path $Experiment "m8_trace.rs"),
        "--record", (Join-Path $Out "source-instrumentation.json")
    )
    $env:RUSTFLAGS = "--cfg m8_overshoot_trace_20260903_v2"
    Invoke-Checked "cargo" @(
        "build", "--release", "-p", "strehl-cli", "-j", "8",
        "--manifest-path", (Join-Path $Snapshot "Cargo.toml"),
        "--target-dir", $InstrumentedTarget
    )
}

function New-WarpMap {
    param(
        [Parameter(Mandatory)][string]$Input,
        [Parameter(Mandatory)][string]$Map,
        [int]$Reference = -1
    )
    Remove-Item Env:STREHL_M8_TRACE_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_M8_CHECKER -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_M8_CAPTURE -ErrorAction SilentlyContinue
    $arguments = @("align", $Input, "--out", $Map, "--resampler", "catmull-rom")
    if ($Reference -ge 0) {
        $arguments += @("--reference", "$Reference")
    }
    Invoke-Checked $Strehl $arguments ($Map -replace "\.warpmap\.txt$", "-align.log")
}

function Invoke-M8Stack {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Input,
        [Parameter(Mandatory)][string]$Map,
        [Parameter(Mandatory)][ValidateSet("scale", "crop")][string]$Cover,
        [switch]$DisableCa
    )
    $state = Join-Path $Out "$Name-state"
    $tiff = Join-Path $Out "$Name-v2.tiff"
    $log = Join-Path $Out "$Name-stack-v2.log"
    Reset-OutputPath $state
    Reset-OutputPath $tiff
    Reset-OutputPath $log
    $env:STREHL_M8_TRACE_DIR = $state
    $env:STREHL_M8_CHECKER = $Checker
    $env:STREHL_M8_CAPTURE = $Name
    $env:STREHL_WARPMAP = $Map
    $env:STREHL_DEFECT = "off"
    $env:STREHL_PYRAMID_WORKERS = "1"
    $arguments = @(
        "stack", $Input, "--out", $tiff, "--merge", "pyramid", "--cover", $Cover
    )
    if ($DisableCa) {
        $arguments += @("--fix-ca", "off")
    }
    Invoke-Checked $Strehl $arguments $log
    Invoke-Checked "python" @("-B", $Checker, "finalize-r", "--state", $state)
    if ($Cover -eq "scale") {
        Invoke-Checked "python" @(
            "-B", $Checker, "final", "--state", $state, "--tiff", $tiff
        )
    }
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$env:CARGO_BUILD_JOBS = "8"
$env:RAYON_NUM_THREADS = "8"
$env:PYTHONIOENCODING = "utf-8"

if ($Mode -eq "All") {
    foreach ($capture in $Captures) {
        $path = Join-Path $CaptureRoot $capture.Directory
        if (-not (Test-Path -LiteralPath $path -PathType Container)) {
            throw "Missing registered development capture: $path"
        }
        $arws = @(Get-ChildItem -LiteralPath $path -Filter "*.ARW" -File)
        if ($arws.Count -ne $capture.Frames) {
            throw "${path}: expected $($capture.Frames) ARWs, found $($arws.Count)"
        }
    }
    Write-InputSnapshot (Join-Path $Out "inputs-before.json")

    Invoke-Checked "cargo" @(
        "build", "--release", "-j", "8",
        "--manifest-path", (Join-Path $Experiment "Cargo.toml"),
        "--target-dir", $FixtureTarget
    )
    Invoke-Commissioning
    New-InstrumentedBuild
    Invoke-Checked "python" @("-B", $Checker, "independence") (
        Join-Path $Out "independence-audit.json"
    )

    $identityInput = Join-Path $Out "identity-input"
    Reset-OutputPath $identityInput
    New-Item -ItemType Directory -Force -Path $identityInput | Out-Null
    $oneSecond = Join-Path $CaptureRoot $Captures[0].Directory
    $identityRaw = Get-ChildItem -LiteralPath $oneSecond -Filter "*.ARW" -File |
        Sort-Object Name | Select-Object -First 1
    if ($null -eq $identityRaw) {
        throw "No identity RAW found in $oneSecond"
    }
    Copy-Item -LiteralPath $identityRaw.FullName -Destination $identityInput
    $identityMap = Join-Path $Out "identity.warpmap.txt"
    New-WarpMap $identityInput $identityMap 0
    Invoke-M8Stack "identity" $identityInput $identityMap "crop" -DisableCa

    foreach ($capture in $Captures) {
        $input = Join-Path $CaptureRoot $capture.Directory
        $map = Join-Path $Out "$($capture.Name).warpmap.txt"
        New-WarpMap $input $map
        Invoke-M8Stack $capture.Name $input $map "scale"
    }

    Write-InputSnapshot (Join-Path $Out "inputs-after.json")
}

Invoke-Checked "python" @(
    "-B", (Join-Path $Experiment "summarize.py"),
    "--out-root", $Out, "--output", $Summary
)
