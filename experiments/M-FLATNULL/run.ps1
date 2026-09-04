[CmdletBinding()]
param(
    [ValidateSet("Prepare", "Run", "Analyze", "All")]
    [string]$Mode = "All",
    [ValidateSet(
        "all",
        "clean-full",
        "middle-full",
        "noisy-full",
        "clean-n60",
        "middle-n60",
        "noisy-n60"
    )]
    [string]$Arm = "all",
    [switch]$Force,
    [string]$CaptureRoot = "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Experiment = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Experiment "..\..")).Path
$Out = Join-Path $Experiment "out"
$SourceCommit = "c88733098ffb512468a830dceb700d831dbc5c7f"
$ToolCommit = "76b3d9cc8b5185735d6c19d4339ce74d29e333e2"
$SourceSnapshot = Join-Path $Out "source-snapshot"
$ToolSnapshot = Join-Path $Out "tool-snapshot"
$FixtureTarget = Join-Path $Out "fixture-target"
$InstrumentedTarget = Join-Path $Out "instrumented-target"
$Strehl = Join-Path $InstrumentedTarget "release\strehl.exe"
$Checker = Join-Path $ToolSnapshot "experiments\M8-overshoot\checker.py"
$Injector = Join-Path $ToolSnapshot "experiments\M8-overshoot\inject_trace.py"
$Hook = Join-Path $ToolSnapshot "experiments\M8-overshoot\m8_trace.rs"
$Analyzer = Join-Path $Experiment "analyze.py"
$CommandLog = Join-Path $Out "commands.log"

$Captures = @(
    [pscustomobject]@{
        Label = "clean"; Directory = "flat-et6s-sw4-cpl"; Frames = 65; Exposure = 6.0
    },
    [pscustomobject]@{
        Label = "middle"; Directory = "flat-et2.5s-sw4-cpl"; Frames = 61; Exposure = 2.5
    },
    [pscustomobject]@{
        Label = "noisy"; Directory = "flat-et1s-sw4-cpl"; Frames = 60; Exposure = 1.0
    }
)

$Arms = @(
    [pscustomobject]@{
        Name = "clean-full"; Capture = "clean"; ExpectedFrames = 65; Limit = 0
    },
    [pscustomobject]@{
        Name = "middle-full"; Capture = "middle"; ExpectedFrames = 61; Limit = 0
    },
    [pscustomobject]@{
        Name = "noisy-full"; Capture = "noisy"; ExpectedFrames = 60; Limit = 0
    },
    [pscustomobject]@{
        Name = "clean-n60"; Capture = "clean"; ExpectedFrames = 60; Limit = 60
    },
    [pscustomobject]@{
        Name = "middle-n60"; Capture = "middle"; ExpectedFrames = 60; Limit = 60
    },
    [pscustomobject]@{
        Name = "noisy-n60"; Capture = "noisy"; ExpectedFrames = 60; Limit = 60
    }
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

function Format-Command {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $rendered = @($File) + @($Arguments) | ForEach-Object {
        if ($_ -match "[\s`"]") {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }
    $rendered -join " "
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$Log
    )
    $line = Format-Command $File $Arguments
    "[$((Get-Date).ToUniversalTime().ToString('o'))] $line" |
        Add-Content -LiteralPath $CommandLog -Encoding utf8
    if ($Log) {
        & $File @Arguments *> $Log
    }
    else {
        & $File @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        if ($Log -and (Test-Path -LiteralPath $Log)) {
            Get-Content -LiteralPath $Log -Tail 100
        }
        throw "$File failed with exit code $LASTEXITCODE"
    }
}

function Clear-StrehlEnvironment {
    Get-ChildItem Env: |
        Where-Object { $_.Name -like "STREHL_*" } |
        ForEach-Object { Remove-Item "Env:$($_.Name)" }
}

function Get-Capture {
    param([Parameter(Mandatory)][string]$Label)
    $capture = $Captures | Where-Object { $_.Label -eq $Label }
    if ($null -eq $capture) {
        throw "Unknown capture label $Label"
    }
    $capture
}

function Assert-Captures {
    if (-not (Test-Path -LiteralPath $CaptureRoot -PathType Container)) {
        throw "Missing read-only capture root: $CaptureRoot"
    }
    foreach ($capture in $Captures) {
        $path = Join-Path $CaptureRoot $capture.Directory
        if (-not (Test-Path -LiteralPath $path -PathType Container)) {
            throw "Missing registered development capture: $path"
        }
        $arws = @(
            Get-ChildItem -LiteralPath $path -Filter "*.ARW" -File |
                Sort-Object Name
        )
        if ($arws.Count -ne $capture.Frames) {
            throw "${path}: expected $($capture.Frames) ARWs, found $($arws.Count)"
        }
    }
}

function Write-InputSnapshot {
    param([Parameter(Mandatory)][string]$Path)
    $captureRows = foreach ($capture in $Captures) {
        $capturePath = Join-Path $CaptureRoot $capture.Directory
        $files = @(
            Get-ChildItem -LiteralPath $capturePath -Force -Recurse -File |
                Sort-Object FullName
        )
        $fileRows = foreach ($file in $files) {
            [pscustomobject]@{
                relative_path = [IO.Path]::GetRelativePath($CaptureRoot, $file.FullName)
                bytes = $file.Length
                mtime_utc_ticks = $file.LastWriteTimeUtc.Ticks
                attributes = $file.Attributes.ToString()
                sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            }
        }
        [pscustomobject]@{
            label = $capture.Label
            path = $capturePath
            expected_arws = $capture.Frames
            files = @($fileRows)
        }
    }
    [pscustomobject]@{
        captured_utc = (Get-Date).ToUniversalTime().ToString("o")
        method = "Get-ChildItem -Force -Recurse; SHA-256 and path/length/mtime/attributes per file"
        captures = @($captureRows)
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Assert-InputsUnchanged {
    $beforePath = Join-Path $Out "inputs-before.json"
    $afterPath = Join-Path $Out "inputs-after.json"
    $before = Get-Content -LiteralPath $beforePath -Raw | ConvertFrom-Json
    $after = Get-Content -LiteralPath $afterPath -Raw | ConvertFrom-Json
    $a = $before.captures | ConvertTo-Json -Depth 8 -Compress
    $b = $after.captures | ConvertTo-Json -Depth 8 -Compress
    if ($a -cne $b) {
        throw "Strictly read-only capture manifest changed during the run"
    }
    [pscustomobject]@{
        unchanged = $true
        before = $before.captured_utc
        after = $after.captured_utc
    } | ConvertTo-Json | Set-Content -LiteralPath (
        Join-Path $Out "input-integrity.json"
    ) -Encoding utf8
}

function Export-Snapshot {
    param(
        [Parameter(Mandatory)][string]$Commit,
        [Parameter(Mandatory)][string]$Destination,
        [Parameter(Mandatory)][string]$ArchiveName,
        [Parameter(Mandatory)][string[]]$Paths
    )
    Reset-OutputPath $Destination
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $tar = Join-Path $Out $ArchiveName
    Reset-OutputPath $tar
    $arguments = @(
        "-c", "core.autocrlf=false", "-C", $Repo, "archive", "--format=tar",
        "--output=$tar", $Commit, "--"
    ) + $Paths
    Invoke-Checked "git" $arguments
    Invoke-Checked "tar" @("-xf", $tar, "-C", $Destination)
    Remove-Item -LiteralPath $tar -Force
}

function Assert-Hash {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Expected
    )
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if ($actual -cne $Expected) {
        throw "$Path hash $actual, expected $Expected"
    }
}

function Invoke-M8Commissioning {
    $commission = Join-Path $Out "commission"
    Reset-OutputPath $commission
    $blocks = Join-Path $commission "blocks"
    New-Item -ItemType Directory -Force -Path $blocks | Out-Null
    $fixture = Join-Path $FixtureTarget "release\m8-overshoot-fixture.exe"
    Invoke-Checked $fixture @("commission", $blocks) (
        Join-Path $commission "fixture.log"
    )
    foreach ($block in Get-ChildItem -LiteralPath $blocks -Filter "*.m8site" -File) {
        $state = Join-Path $commission $block.BaseName
        Invoke-Checked "python" @(
            "-B", $Checker, "consume", "--block", $block.FullName,
            "--state", $state, "--capture", $block.BaseName
        ) (Join-Path $commission "$($block.BaseName)-consume.log")
        Invoke-Checked "python" @(
            "-B", $Checker, "finalize-r", "--state", $state
        ) (Join-Path $commission "$($block.BaseName)-finalize.log")
    }
    Invoke-Checked "python" @(
        "-B", $Checker, "commission-assert", "--root", $commission
    ) (Join-Path $commission "commission.txt")
}

function Write-Provenance {
    $sourceTree = (& git -C $Repo rev-parse "$SourceCommit^{tree}").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Could not resolve source tree"
    }
    $toolTree = (& git -C $Repo rev-parse "$ToolCommit^{tree}").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Could not resolve tool tree"
    }
    $pythonVersions = & python -c (
        "import json,numpy,scipy,tifffile;" +
        "print(json.dumps({'numpy':numpy.__version__,'scipy':scipy.__version__," +
        "'tifffile':tifffile.__version__}))"
    ) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Could not query Python dependency versions"
    }
    $payload = [pscustomobject]@{
        protocol = 1
        prepared_utc = (Get-Date).ToUniversalTime().ToString("o")
        source_commit = $SourceCommit
        source_tree = $sourceTree
        build_id = "c88733098ffb"
        tool_commit = $ToolCommit
        tool_tree = $toolTree
        tool_hashes = [pscustomobject]@{
            checker = (Get-FileHash -LiteralPath $Checker -Algorithm SHA256).Hash
            injector = (Get-FileHash -LiteralPath $Injector -Algorithm SHA256).Hash
            hook = (Get-FileHash -LiteralPath $Hook -Algorithm SHA256).Hash
        }
        instrumented_binary = [pscustomobject]@{
            path = $Strehl
            sha256 = (Get-FileHash -LiteralPath $Strehl -Algorithm SHA256).Hash
            version = ((& $Strehl --version) -join "`n")
        }
        environment = [pscustomobject]@{
            CARGO_BUILD_JOBS = "8"
            RAYON_NUM_THREADS = "8"
            STREHL_DEFECT = "off"
            STREHL_PYRAMID_WORKERS = "1"
            RUSTFLAGS = "--cfg m8_overshoot_trace_20260903_v2"
        }
        merge = [pscustomobject]@{
            backend = "pyramid"
            cover = "scale"
            resampler = "catmull-rom"
            source_defaults = "All omitted flags are fixed by source_commit"
        }
        versions = [pscustomobject]@{
            git = ((& git --version) -join "`n")
            cargo = ((& cargo --version) -join "`n")
            rustc = ((& rustc --version) -join "`n")
            python = ((& python --version) -join "`n")
            numpy = $pythonVersions.numpy
            scipy = $pythonVersions.scipy
            tifffile = $pythonVersions.tifffile
            powershell = $PSVersionTable.PSVersion.ToString()
        }
        timing_policy = [pscustomobject]@{
            throughput_claim = $false
            reason = "Host deliberately shared; deterministic census only"
            valid_preload_percent_max = 15.0
            valid_external_during_percent_max = 10.0
        }
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (
        Join-Path $Out "provenance.json"
    ) -Encoding utf8
}

function Invoke-Prepare {
    $marker = Join-Path $Out "prepared.json"
    if ((Test-Path -LiteralPath $marker) -and -not $Force) {
        Write-Output "Prepare already complete: $marker"
        return
    }
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    Reset-OutputPath $CommandLog
    Clear-StrehlEnvironment
    $env:CARGO_BUILD_JOBS = "8"
    $env:RAYON_NUM_THREADS = "8"
    $env:PYTHONIOENCODING = "utf-8"
    $env:CARGO_TERM_COLOR = "never"
    Assert-Captures
    Write-InputSnapshot (Join-Path $Out "inputs-before.json")

    Export-Snapshot $SourceCommit $SourceSnapshot "source-snapshot.tar" @(
        "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "crates"
    )
    Export-Snapshot $ToolCommit $ToolSnapshot "tool-snapshot.tar" @(
        "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "crates",
        "experiments/M8-overshoot"
    )
    Assert-Hash $Checker "3E6048C25B56B357DC694C32DEE943EAA18AE88B748C9B0FE6B578A9E4251780"
    Assert-Hash $Injector "37B7FCF6246288AC43A95A701FCE82D252ED6F157C8BED1C0A8C7322C7FDFA80"
    Assert-Hash $Hook "D6DB609AC725A89377EAF9B0272E8ED62E69AC12E840F6DD89416B7E044A2E0D"

    Reset-OutputPath $FixtureTarget
    Invoke-Checked "cargo" @(
        "build", "--release", "-j", "8",
        "--manifest-path",
        (Join-Path $ToolSnapshot "experiments\M8-overshoot\Cargo.toml"),
        "--target-dir", $FixtureTarget
    ) (Join-Path $Out "fixture-build.log")
    Invoke-M8Commissioning
    Invoke-Checked "python" @("-B", $Checker, "independence") (
        Join-Path $Out "independence-audit.json"
    )
    Invoke-Checked "python" @(
        "-B", $Analyzer, "commission-usm",
        "--output", (Join-Path $Out "usm-commission.json")
    ) (Join-Path $Out "usm-commission.log")

    Invoke-Checked "python" @(
        "-B", $Injector, $SourceSnapshot, "--hook", $Hook,
        "--record", (Join-Path $Out "source-instrumentation.json")
    ) (Join-Path $Out "source-instrumentation.log")
    Reset-OutputPath $InstrumentedTarget
    $env:STREHL_BUILD_ID = "c88733098ffb"
    $env:RUSTFLAGS = "--cfg m8_overshoot_trace_20260903_v2"
    Invoke-Checked "cargo" @(
        "build", "--release", "-p", "strehl-cli", "-j", "8",
        "--manifest-path", (Join-Path $SourceSnapshot "Cargo.toml"),
        "--target-dir", $InstrumentedTarget
    ) (Join-Path $Out "instrumented-build.log")
    if (-not (Test-Path -LiteralPath $Strehl -PathType Leaf)) {
        throw "Instrumented binary was not built: $Strehl"
    }
    Write-Provenance
    [pscustomobject]@{
        prepared_utc = (Get-Date).ToUniversalTime().ToString("o")
        source_commit = $SourceCommit
        tool_commit = $ToolCommit
        commissioning_passed = $true
    } | ConvertTo-Json | Set-Content -LiteralPath $marker -Encoding utf8
}

function New-WarpMap {
    param(
        [Parameter(Mandatory)][pscustomobject]$ArmRow,
        [Parameter(Mandatory)][string]$CapturePath,
        [Parameter(Mandatory)][string]$Map
    )
    Clear-StrehlEnvironment
    $env:RAYON_NUM_THREADS = "8"
    $arguments = @(
        "align", $CapturePath, "--out", $Map, "--resampler", "catmull-rom"
    )
    if ($ArmRow.Limit -gt 0) {
        $arguments += @("--limit", "$($ArmRow.Limit)")
    }
    Invoke-Checked $Strehl $arguments (
        Join-Path $Out "$($ArmRow.Name)-align.log"
    )
}

function Save-M8Final {
    param(
        [Parameter(Mandatory)][string]$State,
        [Parameter(Mandatory)][string]$Tiff,
        [string]$Label
    )
    $log = if ($Label) {
        Join-Path $Out "$(Split-Path $State -Leaf)-m8-o-$Label.log"
    }
    else {
        Join-Path $Out "$(Split-Path $State -Leaf)-m8-o.log"
    }
    Invoke-Checked "python" @(
        "-B", $Checker, "final", "--state", $State, "--tiff", $Tiff
    ) $log
    if ($Label) {
        Move-Item -LiteralPath (Join-Path $State "m8-o.json") -Destination (
            Join-Path $State "m8-o-$Label.json"
        )
        Move-Item -LiteralPath (
            Join-Path $State "m8-o-violations.npy"
        ) -Destination (Join-Path $State "m8-o-$Label-violations.npy")
    }
}

function Invoke-Arm {
    param([Parameter(Mandatory)][pscustomobject]$ArmRow)
    $complete = Join-Path $Out "$($ArmRow.Name)-complete.json"
    if ((Test-Path -LiteralPath $complete) -and -not $Force) {
        Write-Output "Arm already complete: $($ArmRow.Name)"
        return
    }
    $capture = Get-Capture $ArmRow.Capture
    $capturePath = Join-Path $CaptureRoot $capture.Directory
    $map = Join-Path $Out "$($ArmRow.Name).warpmap.txt"
    $state = Join-Path $Out "$($ArmRow.Name)-state"
    $tiff = Join-Path $Out "$($ArmRow.Name).tiff"
    $paths = @(
        $complete,
        $map,
        (Join-Path $Out "$($ArmRow.Name)-align.log"),
        $state,
        $tiff,
        (Join-Path $Out "$($ArmRow.Name)-stack.log")
    )
    if ($ArmRow.Name -eq "clean-full") {
        $paths += @(
            (Join-Path $Out "clean-full-usm-a0.tiff"),
            (Join-Path $Out "clean-full-usm-a1.tiff"),
            (Join-Path $Out "clean-full-usm-plant.json")
        )
    }
    foreach ($path in $paths) {
        Reset-OutputPath $path
    }

    New-WarpMap $ArmRow $capturePath $map
    Clear-StrehlEnvironment
    $env:RAYON_NUM_THREADS = "8"
    $env:STREHL_M8_TRACE_DIR = $state
    $env:STREHL_M8_CHECKER = $Checker
    $env:STREHL_M8_CAPTURE = $ArmRow.Name
    $env:STREHL_WARPMAP = $map
    $env:STREHL_DEFECT = "off"
    $env:STREHL_PYRAMID_WORKERS = "1"
    $arguments = @(
        "stack", $capturePath, "--out", $tiff, "--merge", "pyramid",
        "--cover", "scale", "--resampler", "catmull-rom"
    )
    if ($ArmRow.Limit -gt 0) {
        $arguments += @("--limit", "$($ArmRow.Limit)")
    }
    Invoke-Checked $Strehl $arguments (
        Join-Path $Out "$($ArmRow.Name)-stack.log"
    )
    Invoke-Checked "python" @(
        "-B", $Checker, "finalize-r", "--state", $state
    ) (Join-Path $Out "$($ArmRow.Name)-m8-r.log")

    if ($ArmRow.Name -eq "clean-full") {
        Save-M8Final $state $tiff "base"
        $zero = Join-Path $Out "clean-full-usm-a0.tiff"
        $planted = Join-Path $Out "clean-full-usm-a1.tiff"
        Invoke-Checked "python" @(
            "-B", $Analyzer, "plant", "--input", $tiff, "--zero", $zero,
            "--output", $planted,
            "--manifest", (Join-Path $Out "clean-full-usm-plant.json")
        ) (Join-Path $Out "clean-full-usm-plant.log")
        Save-M8Final $state $zero "zero"
        Save-M8Final $state $planted "usm"
    }
    else {
        Save-M8Final $state $tiff
    }

    $meta = Get-Content -LiteralPath (Join-Path $state "meta.json") -Raw |
        ConvertFrom-Json
    if ($meta.sites.psobject.Properties.Count -ne 4 * $ArmRow.ExpectedFrames) {
        throw "$($ArmRow.Name): unexpected M8 trace site count"
    }
    [pscustomobject]@{
        name = $ArmRow.Name
        capture = $capture.Label
        exposure_s = $capture.Exposure
        expected_frames = $ArmRow.ExpectedFrames
        limit = if ($ArmRow.Limit -gt 0) { $ArmRow.Limit } else { $null }
        cover = "scale"
        merge = "pyramid"
        resampler = "catmull-rom"
        map_sha256 = (Get-FileHash -LiteralPath $map -Algorithm SHA256).Hash
        tiff_sha256 = (Get-FileHash -LiteralPath $tiff -Algorithm SHA256).Hash
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $complete -Encoding utf8
}

function Test-AllArmsComplete {
    foreach ($armRow in $Arms) {
        if (-not (Test-Path -LiteralPath (
            Join-Path $Out "$($armRow.Name)-complete.json"
        ))) {
            return $false
        }
    }
    return $true
}

function Invoke-Run {
    if (-not (Test-Path -LiteralPath (Join-Path $Out "prepared.json"))) {
        throw "Prepare must pass before any real arm"
    }
    $selected = if ($Arm -eq "all") {
        $Arms
    }
    else {
        @($Arms | Where-Object { $_.Name -eq $Arm })
    }
    foreach ($armRow in $selected) {
        Invoke-Arm $armRow
    }
    if (Test-AllArmsComplete) {
        Write-InputSnapshot (Join-Path $Out "inputs-after.json")
        Assert-InputsUnchanged
    }
}

function Invoke-Analyze {
    if (-not (Test-AllArmsComplete)) {
        throw "All six registered arms must complete before analysis"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Out "inputs-after.json"))) {
        Write-InputSnapshot (Join-Path $Out "inputs-after.json")
    }
    Assert-InputsUnchanged
    Invoke-Checked "python" @(
        "-B", $Analyzer, "summarize", "--out-root", $Out,
        "--output", (Join-Path $Out "results.json")
    ) (Join-Path $Out "summarize.log")
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$env:CARGO_BUILD_JOBS = "8"
$env:RAYON_NUM_THREADS = "8"
$env:PYTHONIOENCODING = "utf-8"
$env:CARGO_TERM_COLOR = "never"

if ($Mode -in @("Prepare", "All")) {
    Invoke-Prepare
}
if ($Mode -in @("Run", "All")) {
    Invoke-Run
}
if ($Mode -in @("Analyze", "All")) {
    Invoke-Analyze
}
