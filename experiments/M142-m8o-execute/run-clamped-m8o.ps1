[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Mode,

    [Parameter(Mandatory)]
    [string]$SourceCommit,

    [string]$Capture = "All"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$Protocol = "M136 clamped-Catmull-Rom representable-domain M8-O v1"
$VerifierProtocol = "M136 independent verifier v1"
$SourceCommit = $SourceCommit.ToLowerInvariant()
$RequiredCommit = "248178b921f98ec1f13ea4c07d30fa68ace787a0"
$RequiredVerifierCommit = "636d3f57"
$RequiredVerifierSha256 = "CAC0E96943DAB44CA1E5FC3B6A2FD8315868290509EE2632861B48157A012401"
$RequiredVerifierCommissionSha256 = "35777789168C5751EFD8584393A314BE5EA4A827636D621A0CDDA494B65B191F"

$Experiment = [IO.Path]::GetFullPath($PSScriptRoot)
$Repo = [IO.Path]::GetFullPath((Join-Path $Experiment "..\.."))
$Out = [IO.Path]::GetFullPath((Join-Path $Experiment "out"))
$M136 = [IO.Path]::GetFullPath((Join-Path $Experiment "..\M136-m8o-bar"))
$Preregistration = Join-Path $M136 "clamped-m8o-preregistration.json"
$Verifier = Join-Path $M136 "verifier_m136.py"
$VerifierCommission = Join-Path $M136 "verifier-commission.json"
$Checker = Join-Path $Experiment "checker_m136.py"
$Fixture = Join-Path $Experiment "fixture_m136.py"
$Hook = Join-Path $Experiment "m8_trace_v3.rs"
$Patcher = Join-Path $Experiment "patch_snapshot_m142.py"
$Runner = [IO.Path]::GetFullPath($PSCommandPath)
$SourceSnapshot = Join-Path $Out "source-snapshot"
$PatchedSnapshot = Join-Path $Out "patched-snapshot"
$SourceManifest = Join-Path $Out "source-manifest.json"
$SourcePatch = Join-Path $Out "source-patch.json"
$BuildTarget = Join-Path $PatchedSnapshot "target-m136"
$TestTarget = Join-Path $PatchedSnapshot "target-m136-tests"
$Binary = Join-Path $BuildTarget "release\strehl.exe"
$BuildLog = Join-Path $Out "build.log"
$BuildReceipt = Join-Path $Out "build-receipt.json"
$TestReceipt = Join-Path $Out "test-receipt.json"
$CommissionRoot = Join-Path $Out "commission"
$FixtureRoot = Join-Path $CommissionRoot "fixtures"
$CheckerCommissionRoot = Join-Path $CommissionRoot "checker"
$CheckerCommission = Join-Path $CheckerCommissionRoot "commissioning.json"
$CheckerCommissionEvidence = Join-Path $CheckerCommissionRoot "violation-evidence.json"
$VerifierCommissionRecheck = Join-Path $CommissionRoot "verifier-recheck.json"
$InstrumentFreeze = Join-Path $Out "instrument-freeze.json"
$VerifierManifest = Join-Path $Out "verifier-manifest.json"
$VerifierReport = Join-Path $Out "verifier-report.json"
$VerifierRun = Join-Path $Out "verifier-run.json"
$Summary = Join-Path $Out "summary.json"

$CaptureSpecs = @(
    [ordered]@{
        name = "flat-et1s"
        trace_key = "0"
        input = "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl"
        map = "experiments\M134-kernel-frontier\out\maps\flat-et1s.clamped.warpmap.txt"
        map_sha256 = "C817271C015FB2703CE802AC53B9925E17953574D1D39D10D23597DEDAB5E6F2"
    },
    [ordered]@{
        name = "flat-et2.5s"
        trace_key = "1"
        input = "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et2.5s-sw4-cpl"
        map = "experiments\M134-kernel-frontier\out\maps\flat-et2.5s.clamped.warpmap.txt"
        map_sha256 = "0035A701259E5AAA6F61910C7F79B2E1A30BBDEF09A827C258C6919E55ED467F"
    },
    [ordered]@{
        name = "flat-et6s"
        trace_key = "2"
        input = "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et6s-sw4-cpl"
        map = "experiments\M134-kernel-frontier\out\maps\flat-et6s.clamped.warpmap.txt"
        map_sha256 = "6D855863804B27506003F5ECE4967AA6136A19EDEF33B2CE8E3A567B0FD4D767"
    }
)

function Get-TraceStatePath {
    param([Parameter(Mandatory)]$Spec)
    return Join-Path $Out ([string]$Spec.trace_key)
}

function Assert-TracePathBudgets {
    # Python cannot reopen ordinary Win32 paths at or above MAX_PATH on hosts
    # without long-path support.  Use a full completed-block name here so a
    # too-deep checkout fails before commissioning or target evidence exists.
    $hex = "0" * 64
    $block = "m8-trace-v3-p1-f00000000-$hex-s00-$hex.m8site"
    $roots = @()
    foreach ($work in @("c", "v")) {
        foreach ($case in @("", "rd", "ri", "gd", "gi", "xd", "xi", "c")) {
            $relative = if ($case) {
                "$work\$case\s\blocks"
            }
            else {
                "$work\s\blocks"
            }
            $roots += Join-Path $Out $relative
        }
    }
    $roots += @(
        $CaptureSpecs |
            ForEach-Object {
                Join-Path (Get-TraceStatePath -Spec $_) "blocks"
            }
    )
    foreach ($root in $roots) {
        $candidate = Join-Path $root $block
        if ($candidate.Length -ge 260) {
            throw (
                "Trace path would exceed the portable Windows limit " +
                "($($candidate.Length) characters): $candidate"
            )
        }
    }
}

function Assert-NoReparsePoint {
    param([Parameter(Mandatory)][string]$Path)
    $cursor = [IO.Path]::GetFullPath($Path)
    while (-not (Test-Path -LiteralPath $cursor)) {
        $parent = Split-Path -Parent $cursor
        if (-not $parent -or $parent -eq $cursor) {
            throw "Could not find an existing ancestor for $Path"
        }
        $cursor = $parent
    }
    while ($cursor) {
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing output through reparse point: $cursor"
        }
        $parent = Split-Path -Parent $cursor
        if (-not $parent -or $parent -eq $cursor) {
            break
        }
        $cursor = $parent
    }
}

function Assert-UnderOutput {
    param(
        [Parameter(Mandatory)][string]$Path,
        [switch]$AllowRoot
    )
    $full = [IO.Path]::GetFullPath($Path)
    $root = $Out.TrimEnd([IO.Path]::DirectorySeparatorChar)
    if ($AllowRoot -and $full.Equals($root, [StringComparison]::OrdinalIgnoreCase)) {
        Assert-NoReparsePoint -Path $full
        return $full
    }
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing an output path outside M142/out: $full"
    }
    Assert-NoReparsePoint -Path $full
    return $full
}

function Reset-OutputPath {
    param(
        [Parameter(Mandatory)][string]$Path,
        [switch]$AllowRoot
    )
    $full = Assert-UnderOutput -Path $Path -AllowRoot:$AllowRoot
    if (Test-Path -LiteralPath $full) {
        Remove-Item -LiteralPath $full -Recurse -Force
    }
}

function Write-Utf8 {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Text,
        [switch]$Replace
    )
    $full = Assert-UnderOutput -Path $Path
    $parent = Split-Path -Parent $full
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    if ((Test-Path -LiteralPath $full) -and -not $Replace) {
        throw "Refusing to overwrite evidence: $full"
    }
    $temporary = "$full.new"
    if (Test-Path -LiteralPath $temporary) {
        throw "Ambiguous leftover evidence staging file: $temporary"
    }
    [IO.File]::WriteAllText($temporary, $Text, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $full
}

function Write-Json {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)]$Value,
        [switch]$Replace
    )
    $json = ConvertTo-Json -InputObject $Value -Depth 40
    Write-Utf8 -Path $Path -Text ($json + "`n") -Replace:$Replace
}

function Get-Sha256 {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file is absent: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-FrozenFile {
    param([Parameter(Mandatory)][string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    return [ordered]@{
        path = $resolved
        sha256 = Get-Sha256 $resolved
    }
}

function Assert-FrozenFile {
    param(
        [Parameter(Mandatory)]$Reference,
        [Parameter(Mandatory)][string]$Label
    )
    $path = [string]$Reference.path
    $expected = [string]$Reference.sha256
    $actual = Get-Sha256 $path
    if ($actual -ne $expected) {
        throw "$Label changed: expected $expected, observed $actual"
    }
}

function Assert-FrozenReferenceAt {
    param(
        [Parameter(Mandatory)]$Reference,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][string]$Label
    )
    Assert-FrozenFile -Reference $Reference -Label $Label
    $actual = (Resolve-Path -LiteralPath ([string]$Reference.path)).Path
    $expected = (Resolve-Path -LiteralPath $ExpectedPath).Path
    if (-not $actual.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label names $actual instead of $expected"
    }
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][int[]]$AllowedExitCodes,
        [string]$Log
    )
    # Windows PowerShell 5.1 wraps a native process's stderr records as
    # non-terminating ErrorRecords.  With the script-wide Stop preference those
    # would otherwise abort before LASTEXITCODE is read, collapsing verifier
    # exits 2 and 3.  Capture both streams under Continue, then restore the
    # caller's preference before interpreting the authenticated numeric exit.
    $priorErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $lines = @(& $File @Arguments 2>&1 | ForEach-Object { $_.ToString() })
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $priorErrorActionPreference
    }
    $text = ($lines -join "`n")
    if ($Log) {
        if (-not $text) {
            $text = "(command produced no output)"
        }
        Write-Utf8 -Path $Log -Text ($text + "`n")
    }
    if ($AllowedExitCodes -notcontains $code) {
        if ($text) {
            $tail = @($lines | Select-Object -Last 80) -join "`n"
            Write-Host $tail
        }
        throw "$File exited $code; expected one of $($AllowedExitCodes -join ', ')"
    }
    return [pscustomobject]@{
        ExitCode = $code
        Text = $text
        Command = @($File) + $Arguments
    }
}

function Get-CommandText {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $result = Invoke-Logged -File $File -Arguments $Arguments -AllowedExitCodes @(0)
    return $result.Text.Trim()
}

function Clear-PrefixedEnvironment {
    param([Parameter(Mandatory)][string[]]$Prefixes)
    foreach ($item in @(Get-ChildItem Env:)) {
        foreach ($prefix in $Prefixes) {
            if ($item.Name.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath "Env:$($item.Name)" -ErrorAction SilentlyContinue
                break
            }
        }
    }
}

function Get-InputFingerprint {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][ValidateSet("before-render", "after-census")]
        [string]$Phase,
        [Parameter(Mandatory)][string]$Output
    )
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
    $prefixLength = $resolvedRoot.TrimEnd(
        [IO.Path]::DirectorySeparatorChar
    ).Length + 1
    $entries = @(
        Get-ChildItem -LiteralPath $resolvedRoot -Force -Recurse
    )
    foreach ($entry in $entries) {
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Input fingerprint refuses reparse point: $($entry.FullName)"
        }
    }
    $files = @(
        $entries |
            Where-Object { -not $_.PSIsContainer } |
            Sort-Object FullName
    )
    $rows = @()
    [int64]$total = 0
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($prefixLength).Replace("\", "/")
        $rows += [ordered]@{
            path = $relative
            bytes = [int64]$file.Length
            last_write_utc_ticks = [int64]$file.LastWriteTimeUtc.Ticks
            sha256 = Get-Sha256 $file.FullName
        }
        $total += [int64]$file.Length
    }
    $document = [ordered]@{
        schema = "m136-input-fingerprint-v1"
        schema_version = 1
        phase = $Phase
        root = $resolvedRoot
        file_count = $rows.Count
        total_bytes = $total
        files = $rows
    }
    Write-Json -Path $Output -Value $document
    return $document
}

function Assert-FingerprintMatch {
    param(
        [Parameter(Mandatory)]$Before,
        [Parameter(Mandatory)]$After,
        [Parameter(Mandatory)][string]$CaptureName
    )
    if (
        [int]$Before.file_count -ne [int]$After.file_count -or
        [int64]$Before.total_bytes -ne [int64]$After.total_bytes -or
        [string]$Before.root -ne [string]$After.root
    ) {
        throw "$CaptureName input inventory changed during the census"
    }
    $left = ConvertTo-Json -InputObject $Before.files -Depth 8 -Compress
    $right = ConvertTo-Json -InputObject $After.files -Depth 8 -Compress
    if ($left -cne $right) {
        throw "$CaptureName input paths, timestamps, sizes, or hashes changed"
    }
}

function Assert-Prerequisites {
    Assert-TracePathBudgets
    if ($Mode -notin @("Prepare", "Commission", "Freeze", "Census", "Verify", "Summarize")) {
        throw "Unknown runner mode: $Mode"
    }
    if ($Capture -notin @("flat-et1s", "flat-et2.5s", "flat-et6s", "All")) {
        throw "Unknown registered capture: $Capture"
    }
    if ($SourceCommit -notmatch "^[0-9a-f]{40}$") {
        throw "SourceCommit must contain exactly 40 hexadecimal digits"
    }
    foreach ($path in @(
        $Preregistration,
        $Verifier,
        $VerifierCommission,
        $Checker,
        $Fixture,
        $Hook,
        $Patcher,
        $Runner
    )) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required instrument file is absent: $path"
        }
    }
    if ($SourceCommit -ne $RequiredCommit) {
        throw "Source commit $SourceCommit differs from preregistered candidate $RequiredCommit"
    }
    if ((Get-Sha256 $Verifier) -cne $RequiredVerifierSha256) {
        throw "M136 verifier differs from final commit $RequiredVerifierCommit"
    }
    if ((Get-Sha256 $VerifierCommission) -cne $RequiredVerifierCommissionSha256) {
        throw "M136 commissioning report differs from final commit $RequiredVerifierCommit"
    }
    $resolvedCommit = Get-CommandText -File "git" -Arguments @(
        "-C", $Repo, "rev-parse", "$SourceCommit`^{commit}"
    )
    if ($resolvedCommit.ToLowerInvariant() -ne $SourceCommit) {
        throw "git resolved $SourceCommit to unexpected commit $resolvedCommit"
    }
}

function Assert-SharedCratesClean {
    $crateStatus = Get-CommandText -File "git" -Arguments @(
        "-C", $Repo, "status", "--porcelain", "--", "crates/"
    )
    if ($crateStatus) {
        throw "Shared crates/ is not clean; refusing private-candidate preparation"
    }
}

function Copy-RegisteredMaps {
    foreach ($spec in $CaptureSpecs) {
        $source = [IO.Path]::GetFullPath((Join-Path $Repo $spec.map))
        if ((Get-Sha256 $source) -ne $spec.map_sha256) {
            throw "$($spec.name) registered warp-map hash changed"
        }
        $captureRoot = Join-Path $Out "captures\$($spec.name)"
        New-Item -ItemType Directory -Path $captureRoot -Force | Out-Null
        $destination = Join-Path $captureRoot "map.warpmap.txt"
        if (Test-Path -LiteralPath $destination) {
            throw "Refusing to overwrite copied warp map: $destination"
        }
        Copy-Item -LiteralPath $source -Destination $destination
        if ((Get-Sha256 $destination) -ne $spec.map_sha256) {
            throw "$($spec.name) copied warp map differs from its registered source"
        }
    }
}

function Invoke-CandidateBuild {
    $cargo = (Get-Command cargo -CommandType Application).Source
    $rustc = (Get-Command rustc -CommandType Application).Source
    $sourceManifestHash = Get-Sha256 $SourceManifest
    $epoch = Get-CommandText -File "git" -Arguments @(
        "-C", $Repo, "show", "-s", "--format=%ct", $SourceCommit
    )
    if ($epoch -notmatch "^\d+$") {
        throw "Could not obtain SOURCE_DATE_EPOCH for $SourceCommit"
    }
    $buildId = "m136-$($SourceCommit.Substring(0, 12))-$($sourceManifestHash.Substring(0, 12).ToLowerInvariant())"

    Clear-PrefixedEnvironment -Prefixes @("CARGO", "RUST", "STREHL_")
    $env:CARGO_BUILD_JOBS = "4"
    $env:CARGO_INCREMENTAL = "0"
    $env:RUSTC = $rustc
    $env:RUSTFLAGS = ""
    $env:SOURCE_DATE_EPOCH = $epoch
    $env:STREHL_BUILD_ID = $buildId

    $arguments = @(
        "build",
        "--release",
        "--locked",
        "--offline",
        "-p",
        "strehl-cli",
        "-j",
        "4",
        "--manifest-path",
        (Join-Path $PatchedSnapshot "Cargo.toml"),
        "--target-dir",
        $BuildTarget
    )
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $build = Invoke-Logged -File $cargo -Arguments $arguments -AllowedExitCodes @(0) -Log $BuildLog
    $completed = (Get-Date).ToUniversalTime().ToString("o")
    if (-not (Test-Path -LiteralPath $Binary -PathType Leaf)) {
        throw "Candidate build did not produce $Binary"
    }
    $receipt = [ordered]@{
        schema = "m136-build-receipt-v1"
        schema_version = 1
        protocol = $Protocol
        source_commit = $SourceCommit
        source_root = $PatchedSnapshot
        source_manifest = Get-FrozenFile $SourceManifest
        source_patch = Get-FrozenFile $SourcePatch
        candidate_binary = Get-FrozenFile $Binary
        cargo = Get-FrozenFile $cargo
        rustc = Get-FrozenFile $rustc
        build_log = Get-FrozenFile $BuildLog
        environment = [ordered]@{
            CARGO_BUILD_JOBS = "4"
            CARGO_INCREMENTAL = "0"
            RUSTC = $rustc
            RUSTFLAGS = ""
            SOURCE_DATE_EPOCH = $epoch
            STREHL_BUILD_ID = $buildId
        }
        command = @($cargo) + $arguments
        started_utc = $started
        completed_utc = $completed
        exit_code = $build.ExitCode
        cargo_version = Get-CommandText -File $cargo -Arguments @("--version", "--verbose")
        rustc_version = Get-CommandText -File $rustc -Arguments @("-vV")
    }
    Write-Json -Path $BuildReceipt -Value $receipt
}

function Invoke-CandidateTests {
    $cargo = (Get-Command cargo -CommandType Application).Source
    Clear-PrefixedEnvironment -Prefixes @("STREHL_")
    foreach ($name in @(
        "RAYON_NUM_THREADS",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS"
    )) {
        Set-Item -LiteralPath "Env:$name" -Value "1"
    }
    $commands = @(
        [ordered]@{
            name = "strehl-bin"
            arguments = @(
                "test", "--locked", "--offline", "-p", "strehl-cli", "--bin", "strehl",
                "--manifest-path", (Join-Path $PatchedSnapshot "Cargo.toml"),
                "--target-dir", $TestTarget
            )
            log = Join-Path $Out "test-strehl-bin.log"
        },
        [ordered]@{
            name = "byte-freeze"
            arguments = @(
                "test", "--locked", "--offline", "-p", "strehl-cli",
                "--test", "byte-freeze",
                "--manifest-path", (Join-Path $PatchedSnapshot "Cargo.toml"),
                "--target-dir", $TestTarget,
                "--", "--nocapture"
            )
            log = Join-Path $Out "test-byte-freeze.log"
        }
    )
    $rows = @()
    foreach ($command in $commands) {
        $started = (Get-Date).ToUniversalTime().ToString("o")
        $result = Invoke-Logged -File $cargo -Arguments $command.arguments -AllowedExitCodes @(0) -Log $command.log
        $rows += [ordered]@{
            name = $command.name
            command = @($cargo) + $command.arguments
            started_utc = $started
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
            exit_code = $result.ExitCode
            log = Get-FrozenFile $command.log
        }
    }
    Write-Json -Path $TestReceipt -Value ([ordered]@{
        schema = "m142-m136-test-receipt-v1"
        schema_version = 1
        protocol = $Protocol
        status = "PASS"
        source_commit = $SourceCommit
        candidate_binary = Get-FrozenFile $Binary
        tests = $rows
    })
}

function Prepare {
    Assert-Prerequisites
    Assert-SharedCratesClean
    if (
        (Test-Path -LiteralPath $InstrumentFreeze) -or
        (Test-Path -LiteralPath $VerifierManifest) -or
        (Test-Path -LiteralPath $VerifierReport) -or
        (Test-Path -LiteralPath $Summary)
    ) {
        throw "Measured or frozen evidence already exists; Prepare will not erase it"
    }
    foreach ($spec in $CaptureSpecs) {
        $captureRoot = Join-Path $Out "captures\$($spec.name)"
        foreach ($evidence in @(
            "output.tiff",
            "checker-state",
            "input-before.json",
            "input-after.json",
            "render-provenance.json",
            "capture-status.json"
        )) {
            if (Test-Path -LiteralPath (Join-Path $captureRoot $evidence)) {
                throw "Target evidence exists; Prepare will not erase $captureRoot"
            }
        }
        $traceState = Get-TraceStatePath -Spec $spec
        if (Test-Path -LiteralPath $traceState) {
            throw "Target trace evidence exists; Prepare will not erase $traceState"
        }
    }
    foreach ($work in @((Join-Path $Out "c"), (Join-Path $Out "v"))) {
        if (Test-Path -LiteralPath $work) {
            throw "Commissioning or verification work exists; Prepare will not erase $work"
        }
    }
    Reset-OutputPath -Path $Out -AllowRoot
    New-Item -ItemType Directory -Path $Out -Force | Out-Null
    New-Item -ItemType Directory -Path $SourceSnapshot -Force | Out-Null

    $archive = Join-Path $Out "source-snapshot.tar"
    Invoke-Logged -File "git" -Arguments @(
        "-c", "core.autocrlf=false",
        "-C", $Repo,
        "archive",
        "--format=tar",
        "--output=$archive",
        $SourceCommit
    ) -AllowedExitCodes @(0) | Out-Null
    Invoke-Logged -File "tar" -Arguments @(
        "-xf", $archive, "-C", $SourceSnapshot
    ) -AllowedExitCodes @(0) | Out-Null
    Remove-Item -LiteralPath $archive -Force

    Invoke-Logged -File "python" -Arguments @(
        "-B",
        $Patcher,
        "--source", $SourceSnapshot,
        "--destination", $PatchedSnapshot,
        "--hook", $Hook,
        "--record", $SourcePatch,
        "--source-manifest", $SourceManifest,
        "--source-commit", $SourceCommit
    ) -AllowedExitCodes @(0) -Log (Join-Path $Out "patch.log") | Out-Null

    $align = [IO.File]::ReadAllText(
        (Join-Path $PatchedSnapshot "crates\strehl-core\src\align.rs")
    )
    if (
        $align.IndexOf("sample_clamped_catmull_rom", [StringComparison]::Ordinal) -lt 0 -or
        $align.IndexOf("value.clamp(lo, hi)", [StringComparison]::Ordinal) -lt 0
    ) {
        throw "Private snapshot does not contain the exact zero-margin clamp"
    }
    $warpmap = [IO.File]::ReadAllText(
        (Join-Path $PatchedSnapshot "crates\strehl-core\src\warpmap.rs")
    )
    if ($warpmap.IndexOf('"clamped-catmull"', [StringComparison]::Ordinal) -lt 0) {
        throw "Private snapshot does not expose clamped-catmull"
    }
    $merge = [IO.File]::ReadAllText(
        (Join-Path $PatchedSnapshot "crates\strehl-cli\src\merge_cmd.rs")
    )
    if ($merge.IndexOf("cover: Cover::Crop", [StringComparison]::Ordinal) -lt 0) {
        throw "Private snapshot does not contain the post-M130 Crop path"
    }
    Copy-RegisteredMaps
    Invoke-CandidateBuild
    Invoke-CandidateTests
}

function Commission {
    if (Test-Path -LiteralPath $InstrumentFreeze) {
        throw "Instrument is already frozen; refusing to replace its commissioning evidence"
    }
    foreach ($path in @($Binary, $BuildReceipt, $TestReceipt, $VerifierCommission)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Commissioning prerequisite is absent: $path"
        }
    }
    if (Test-Path -LiteralPath $CommissionRoot) {
        throw (
            "Commissioning evidence already exists at $CommissionRoot; " +
            "rerun Prepare to create a fresh pre-target instrument"
        )
    }
    New-Item -ItemType Directory -Path $CommissionRoot -Force | Out-Null

    Invoke-Logged -File "python" -Arguments @(
        "-B",
        (Join-Path $Repo "experiments\ORCH-drift-check\prior_art.py"),
        "clamped", "catmull", "m8-o", "projected", "output", "hull"
    ) -AllowedExitCodes @(0) -Log (Join-Path $CommissionRoot "prior-art.txt") | Out-Null

    Invoke-Logged -File "python" -Arguments @(
        "-B", $Fixture, "commission",
        "--preregistration", $Preregistration,
        "--output", $FixtureRoot
    ) -AllowedExitCodes @(0) -Log (Join-Path $CommissionRoot "fixture.log") | Out-Null
    Invoke-Logged -File "python" -Arguments @(
        "-B", $Checker, "commission",
        "--fixtures", $FixtureRoot,
        "--output", $CheckerCommissionRoot
    ) -AllowedExitCodes @(0) -Log (Join-Path $CommissionRoot "checker.log") | Out-Null

    $primary = Get-Content -LiteralPath $CheckerCommission -Raw | ConvertFrom-Json
    if (
        $primary.status -ne "PASS" -or
        [int]$primary.direction_controls.green.passed -ne 6 -or
        [int]$primary.direction_controls.red.passed -ne 6 -or
        [int]$primary.fail_closed.passed -ne 7
    ) {
        throw "Primary checker commissioning did not pass every frozen control"
    }

    # M136's trace block names are deliberately content-addressed and long.
    # Keep its commissioning work at a one-component path so Python can reopen
    # the files even when Windows long-path support is disabled.
    $verifierWork = Join-Path $Out "c"
    Invoke-Logged -File "python" -Arguments @(
        "-B", $Verifier, "commission",
        "--preregistration", $Preregistration,
        "--report", $VerifierCommissionRecheck,
        "--work-dir", $verifierWork
    ) -AllowedExitCodes @(0) -Log (Join-Path $CommissionRoot "verifier.log") | Out-Null
    if (
        (Get-Sha256 $VerifierCommissionRecheck) -ne
        (Get-Sha256 $VerifierCommission)
    ) {
        throw "Fresh independent commissioning differs from M136's frozen report"
    }
}

function Freeze {
    foreach ($path in @(
        $SourceManifest,
        $SourcePatch,
        $BuildReceipt,
        $TestReceipt,
        $Binary,
        (Join-Path $FixtureRoot "manifest.json"),
        $CheckerCommission,
        $CheckerCommissionEvidence,
        $VerifierCommission,
        $VerifierCommissionRecheck
    )) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Freeze prerequisite is absent: $path"
        }
    }
    if (Test-Path -LiteralPath $InstrumentFreeze) {
        throw "Instrument freeze already exists; rerun Prepare and Commission to refreeze"
    }
    foreach ($spec in $CaptureSpecs) {
        $captureRoot = Join-Path $Out "captures\$($spec.name)"
        foreach ($forbidden in @(
            (Join-Path $captureRoot "output.tiff"),
            (Get-TraceStatePath -Spec $spec),
            (Join-Path $captureRoot "checker-state"),
            (Join-Path $captureRoot "input-before.json"),
            (Join-Path $captureRoot "input-after.json")
        )) {
            if (Test-Path -LiteralPath $forbidden) {
                throw "Target evidence exists before instrument freeze: $forbidden"
            }
        }
    }

    $pythonVersion = Get-CommandText -File "python" -Arguments @("--version")
    $numpyVersion = Get-CommandText -File "python" -Arguments @(
        "-c", "import numpy; print(numpy.__version__)"
    )
    $tifffileVersion = Get-CommandText -File "python" -Arguments @(
        "-c", "import tifffile; print(tifffile.__version__)"
    )
    $freeze = [ordered]@{
        schema = "m136-instrument-freeze-v1"
        schema_version = 1
        protocol = $Protocol
        status = "FROZEN_PRE_TARGET"
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        source_commit = $SourceCommit
        preregistration = Get-FrozenFile $Preregistration
        source_snapshot = [ordered]@{
            root = $PatchedSnapshot
            manifest = Get-FrozenFile $SourceManifest
            patch = Get-FrozenFile $SourcePatch
        }
        build_receipt = Get-FrozenFile $BuildReceipt
        candidate_binary = Get-FrozenFile $Binary
        instruments = [ordered]@{
            checker = Get-FrozenFile $Checker
            fixture = Get-FrozenFile $Fixture
            hook = Get-FrozenFile $Hook
            runner = Get-FrozenFile $Runner
            verifier = Get-FrozenFile $Verifier
        }
        commissioning = [ordered]@{
            verifier_report = Get-FrozenFile $VerifierCommission
            fixture_manifest = Get-FrozenFile (Join-Path $FixtureRoot "manifest.json")
            checker_report = Get-FrozenFile $CheckerCommission
            checker_violation_evidence = Get-FrozenFile $CheckerCommissionEvidence
        }
        versions = [ordered]@{
            python = $pythonVersion
            numpy = $numpyVersion
            tifffile = $tifffileVersion
            powershell = $PSVersionTable.PSVersion.ToString()
        }
        tests = [ordered]@{
            receipt = Get-FrozenFile $TestReceipt
        }
    }
    Write-Json -Path $InstrumentFreeze -Value $freeze
    foreach ($reference in @(
        $freeze.preregistration,
        $freeze.source_snapshot.manifest,
        $freeze.source_snapshot.patch,
        $freeze.build_receipt,
        $freeze.candidate_binary,
        $freeze.instruments.checker,
        $freeze.instruments.fixture,
        $freeze.instruments.hook,
        $freeze.instruments.runner,
        $freeze.instruments.verifier,
        $freeze.commissioning.verifier_report,
        $freeze.commissioning.fixture_manifest,
        $freeze.commissioning.checker_report,
        $freeze.commissioning.checker_violation_evidence,
        $freeze.tests.receipt
    )) {
        Assert-FrozenFile -Reference $reference -Label $reference.path
    }
    Write-Host "FROZEN_PRE_TARGET $((Get-Sha256 $InstrumentFreeze))"
}

function Get-RenderEnvironment {
    param(
        [Parameter(Mandatory)][string]$CaptureName,
        [Parameter(Mandatory)][string]$Map,
        [Parameter(Mandatory)][string]$TraceState,
        [Parameter(Mandatory)][string]$FreezeHash
    )
    return [ordered]@{
        MKL_NUM_THREADS = "1"
        NUMEXPR_NUM_THREADS = "1"
        OMP_NUM_THREADS = "1"
        OPENBLAS_NUM_THREADS = "1"
        RAYON_NUM_THREADS = "4"
        STREHL_DEFECT = "off"
        STREHL_FULLRES_GATHER = "1"
        STREHL_M8_CAPTURE = $CaptureName
        STREHL_M8_CHECKER = $Checker
        STREHL_M8_FREEZE_SHA256 = $FreezeHash
        STREHL_M8_TRACE_DIR = $TraceState
        STREHL_PYRAMID_WORKERS = "1"
        STREHL_WARPMAP = $Map
    }
}

function Set-RenderEnvironment {
    param([Parameter(Mandatory)]$Environment)
    Clear-PrefixedEnvironment -Prefixes @("STREHL_")
    foreach ($entry in $Environment.GetEnumerator()) {
        Set-Item -LiteralPath "Env:$($entry.Key)" -Value ([string]$entry.Value)
    }
}

function Assert-InstrumentFrozen {
    $freezeHash = Get-Sha256 $InstrumentFreeze
    $freeze = Get-Content -LiteralPath $InstrumentFreeze -Raw | ConvertFrom-Json
    if (
        $freeze.schema -ne "m136-instrument-freeze-v1" -or
        $freeze.status -ne "FROZEN_PRE_TARGET" -or
        $freeze.source_commit -ne $SourceCommit
    ) {
        throw "Instrument freeze identity is invalid"
    }
    foreach ($reference in @(
        $freeze.preregistration,
        $freeze.source_snapshot.manifest,
        $freeze.source_snapshot.patch,
        $freeze.build_receipt,
        $freeze.candidate_binary,
        $freeze.instruments.checker,
        $freeze.instruments.fixture,
        $freeze.instruments.hook,
        $freeze.instruments.runner,
        $freeze.instruments.verifier,
        $freeze.commissioning.verifier_report,
        $freeze.commissioning.fixture_manifest,
        $freeze.commissioning.checker_report,
        $freeze.commissioning.checker_violation_evidence,
        $freeze.tests.receipt
    )) {
        Assert-FrozenFile -Reference $reference -Label $reference.path
    }
    return [pscustomobject]@{
        Document = $freeze
        Sha256 = $freezeHash
    }
}

function Invoke-CaptureCensus {
    param([Parameter(Mandatory)]$Spec)
    $frozen = Assert-InstrumentFrozen
    $name = [string]$Spec.name
    $input = (Resolve-Path -LiteralPath ([string]$Spec.input)).Path
    $captureRoot = Join-Path $Out "captures\$name"
    $map = Join-Path $captureRoot "map.warpmap.txt"
    # A completed trace-v3 filename is 165 bytes.  The compact one-component
    # state roots keep every registered block path below legacy MAX_PATH, which
    # remains relevant to Python's file APIs on this host.
    $traceState = Get-TraceStatePath -Spec $Spec
    $checkerState = Join-Path $captureRoot "checker-state"
    $tiff = Join-Path $captureRoot "output.tiff"
    $renderLog = Join-Path $captureRoot "render.log"
    $checkerLog = Join-Path $captureRoot "checker.log"
    $beforePath = Join-Path $captureRoot "input-before.json"
    $afterPath = Join-Path $captureRoot "input-after.json"
    $renderProvenance = Join-Path $captureRoot "render-provenance.json"
    $captureStatus = Join-Path $captureRoot "capture-status.json"

    if ((Get-Sha256 $map) -ne $Spec.map_sha256) {
        throw "$name copied warp map differs from the preregistration"
    }
    foreach ($path in @(
        $traceState,
        $checkerState,
        $tiff,
        $renderLog,
        $checkerLog,
        $beforePath,
        $afterPath,
        $renderProvenance,
        $captureStatus
    )) {
        Assert-UnderOutput -Path $path | Out-Null
        if (Test-Path -LiteralPath $path) {
            throw (
                "$name already has census evidence at $path; " +
                "retaining it and refusing a destructive rerun"
            )
        }
    }

    $before = Get-InputFingerprint -Root $input -Phase "before-render" -Output $beforePath
    try {
        $environment = Get-RenderEnvironment -CaptureName $name -Map $map -TraceState $traceState -FreezeHash $frozen.Sha256
        Set-RenderEnvironment -Environment $environment
        $arguments = @(
            "stack",
            $input,
            "--out",
            $tiff,
            "--merge",
            "pyramid",
            "--cover",
            "crop",
            "--resampler",
            "clamped-catmull",
            "--fix-ca",
            "off"
        )
        $started = (Get-Date).ToUniversalTime().ToString("o")
        $render = Invoke-Logged -File $Binary -Arguments $arguments -AllowedExitCodes @(0) -Log $renderLog
        $completed = (Get-Date).ToUniversalTime().ToString("o")
        if (-not (Test-Path -LiteralPath $tiff -PathType Leaf)) {
            throw "$name render omitted its TIFF"
        }
        $renderRecord = [ordered]@{
            schema = "m136-render-provenance-v1"
            schema_version = 1
            protocol = $Protocol
            capture = $name
            source_commit = $SourceCommit
            candidate_binary = Get-FrozenFile $Binary
            input_dir = $input
            input_fingerprint_before = Get-FrozenFile $beforePath
            warpmap = Get-FrozenFile $map
            trace_state = $traceState
            output_tiff = Get-FrozenFile $tiff
            instrument_freeze = Get-FrozenFile $InstrumentFreeze
            environment = $environment
            command = @($Binary) + $arguments
            started_utc = $started
            completed_utc = $completed
            exit_code = $render.ExitCode
        }
        Write-Json -Path $renderProvenance -Value $renderRecord

        $checkerArguments = @(
            "-B",
            $Checker,
            "adjudicate",
            "--capture", $name,
            "--input-dir", $input,
            "--trace-state", $traceState,
            "--warpmap", $map,
            "--tiff", $tiff,
            "--output", $checkerState,
            "--preregistration", $Preregistration,
            "--commissioning-report", $CheckerCommission,
            "--source-commit", $SourceCommit,
            "--candidate-binary", $Binary,
            "--instrument-freeze", $InstrumentFreeze,
            "--green-rule", "same-frame-before-reduction",
            "--chunk-rows", "32"
        )
        $checkerResult = Invoke-Logged -File "python" -Arguments $checkerArguments -AllowedExitCodes @(0, 1) -Log $checkerLog
    }
    finally {
        $after = Get-InputFingerprint -Root $input -Phase "after-census" -Output $afterPath
        Assert-FingerprintMatch -Before $before -After $after -CaptureName $name
    }
    Write-Json -Path $captureStatus -Value ([ordered]@{
        schema = "m142-m136-capture-status-v1"
        schema_version = 1
        protocol = $Protocol
        capture = $name
        status = if ($checkerResult.ExitCode -eq 0) { "PASS" } else { "FAIL" }
        checker_exit_code = $checkerResult.ExitCode
        input_unchanged = $true
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    })
}

function Census {
    $selected = if ($Capture -eq "All") {
        $CaptureSpecs
    }
    else {
        @($CaptureSpecs | Where-Object { $_.name -eq $Capture })
    }
    foreach ($spec in $selected) {
        Invoke-CaptureCensus -Spec $spec
    }
}

function Get-CheckerArtifacts {
    param([Parameter(Mandatory)][string]$CheckerState)
    $paths = [ordered]@{
        meta = "meta.json"
        m8_r = "m8-r.json"
        m8_r_block_manifest = "m8-r-blocks\manifest.json"
        m8_r_violations = "m8-r-violations.npy"
        pre_lower = "pre-saturation-lower.npy"
        pre_upper = "pre-saturation-upper.npy"
        projected_lower = "projected-lower.npy"
        projected_upper = "projected-upper.npy"
        valid_contributors = "valid-contributor-count.npy"
        lower_frame_witness = "lower-frame-witness.npy"
        upper_frame_witness = "upper-frame-witness.npy"
        m8_o = "m8-o-m136.json"
        violations = "m8-o-m136-violations.npy"
        rail_disclosure = "rail-disclosure.json"
        provenance = "provenance.json"
    }
    $result = [ordered]@{}
    foreach ($entry in $paths.GetEnumerator()) {
        $result[$entry.Key] = Get-FrozenFile (Join-Path $CheckerState $entry.Value)
    }
    return $result
}

function New-VerifierManifest {
    $captures = @()
    foreach ($spec in $CaptureSpecs) {
        $captureRoot = Join-Path $Out "captures\$($spec.name)"
        $checkerState = Join-Path $captureRoot "checker-state"
        $captures += [ordered]@{
            name = $spec.name
            input_dir = (Resolve-Path -LiteralPath ([string]$spec.input)).Path
            input_fingerprint_before = Get-FrozenFile (Join-Path $captureRoot "input-before.json")
            input_fingerprint_after = Get-FrozenFile (Join-Path $captureRoot "input-after.json")
            warpmap = Get-FrozenFile (Join-Path $captureRoot "map.warpmap.txt")
            trace_state = Get-TraceStatePath -Spec $spec
            checker_state = $checkerState
            output_tiff = Get-FrozenFile (Join-Path $captureRoot "output.tiff")
            render_provenance = Get-FrozenFile (Join-Path $captureRoot "render-provenance.json")
            checker_artifacts = Get-CheckerArtifacts -CheckerState $checkerState
        }
    }
    return [ordered]@{
        schema = "m136-verifier-input-v1"
        protocol = $VerifierProtocol
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        preregistration = $Preregistration
        commission_report = Get-FrozenFile $VerifierCommission
        source_root = $PatchedSnapshot
        source_commit = $SourceCommit
        source_manifest = Get-FrozenFile $SourceManifest
        source_patch = Get-FrozenFile $SourcePatch
        build_receipt = Get-FrozenFile $BuildReceipt
        binary = Get-FrozenFile $Binary
        instruments = [ordered]@{
            checker = Get-FrozenFile $Checker
            fixture = Get-FrozenFile $Fixture
            hook = Get-FrozenFile $Hook
            runner = Get-FrozenFile $Runner
        }
        checker_fixture_manifest = Get-FrozenFile (Join-Path $FixtureRoot "manifest.json")
        checker_commission_artifacts = [ordered]@{
            report = Get-FrozenFile $CheckerCommission
            violation_evidence = Get-FrozenFile $CheckerCommissionEvidence
        }
        instrument_freeze = Get-FrozenFile $InstrumentFreeze
        captures = $captures
    }
}

function Verify {
    Assert-InstrumentFrozen | Out-Null
    if (Test-Path -LiteralPath $VerifierManifest) {
        throw "Verifier manifest already exists: $VerifierManifest"
    }
    if (Test-Path -LiteralPath $VerifierReport) {
        throw "Verifier report already exists: $VerifierReport"
    }
    if (Test-Path -LiteralPath $VerifierRun) {
        throw "Verifier run receipt already exists: $VerifierRun"
    }
    Write-Json -Path $VerifierManifest -Value (New-VerifierManifest)
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $arguments = @(
        "-B", $Verifier, "verify",
        "--manifest", $VerifierManifest,
        "--report", $VerifierReport,
        "--chunk-rows", "64"
    )
    $result = Invoke-Logged -File "python" -Arguments $arguments -AllowedExitCodes @(0, 1, 2, 3) -Log (Join-Path $Out "verifier.log")
    if (-not (Test-Path -LiteralPath $VerifierReport -PathType Leaf)) {
        throw "Independent verifier exited $($result.ExitCode) without a report"
    }
    Write-Json -Path $VerifierRun -Value ([ordered]@{
        schema = "m142-m136-verifier-run-v1"
        schema_version = 1
        protocol = $VerifierProtocol
        started_utc = $started
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
        command = @("python") + $arguments
        exit_code = $result.ExitCode
        verifier = Get-FrozenFile $Verifier
        manifest = Get-FrozenFile $VerifierManifest
        report = Get-FrozenFile $VerifierReport
        instrument_freeze = Get-FrozenFile $InstrumentFreeze
    })
    return $result.ExitCode
}

function Summarize {
    $frozen = Assert-InstrumentFrozen
    foreach ($path in @($VerifierManifest, $VerifierReport, $VerifierRun)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Independent verification evidence is absent: $path"
        }
    }
    $manifest = Get-Content -LiteralPath $VerifierManifest -Raw | ConvertFrom-Json
    $verifier = Get-Content -LiteralPath $VerifierReport -Raw | ConvertFrom-Json
    $run = Get-Content -LiteralPath $VerifierRun -Raw | ConvertFrom-Json
    if (
        $run.schema -isnot [string] -or
        $run.protocol -isnot [string] -or
        $run.schema -cne "m142-m136-verifier-run-v1" -or
        $run.protocol -cne $VerifierProtocol -or
        (
            $run.exit_code -isnot [int] -and
            $run.exit_code -isnot [long]
        )
    ) {
        throw "Verifier run receipt is invalid"
    }
    $runExitCode = [int64]$run.exit_code
    if ($runExitCode -notin @(0, 1, 2, 3)) {
        throw "Verifier run receipt has a noncanonical exit code"
    }
    Assert-FrozenReferenceAt -Reference $run.verifier -ExpectedPath $Verifier -Label "verifier run instrument"
    Assert-FrozenReferenceAt -Reference $run.manifest -ExpectedPath $VerifierManifest -Label "verifier run manifest"
    Assert-FrozenReferenceAt -Reference $run.report -ExpectedPath $VerifierReport -Label "verifier run report"
    Assert-FrozenReferenceAt -Reference $run.instrument_freeze -ExpectedPath $InstrumentFreeze -Label "verifier run freeze"
    if (
        $verifier.protocol -isnot [string] -or
        $verifier.status -isnot [string] -or
        $verifier.protocol -cne $VerifierProtocol
    ) {
        throw "Independent verifier report names an unexpected protocol"
    }
    if (@("UNMEASURED", "DISAGREEMENT") -ccontains $verifier.status) {
        $expectedExit = if ($verifier.status -ceq "UNMEASURED") { 2 } else { 3 }
        if (
            $runExitCode -ne $expectedExit -or
            -not ($verifier.error -is [string]) -or
            -not $verifier.error
        ) {
            throw "Independent verifier failure report and run receipt disagree"
        }
        Write-Json -Path $Summary -Value ([ordered]@{
            schema = "m142-m136-summary-v1"
            schema_version = 1
            protocol = $Protocol
            status = "UNMEASURED"
            verifier_status = [string]$verifier.status
            error = [string]$verifier.error
            decision = "No score is reported when any commissioning, completeness, independence, arithmetic, Crop, or provenance control fails"
            nonzero_floor = $null
            source_commit = $SourceCommit
            instrument_freeze = Get-FrozenFile $InstrumentFreeze
            verifier_report = Get-FrozenFile $VerifierReport
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
        })
        Write-Host "M8-O UNMEASURED: $($verifier.error)"
        return $expectedExit
    }
    if (
        $verifier.source_commit -isnot [string] -or
        $verifier.source_commit -cne $SourceCommit -or
        @("PASS", "FAIL") -cnotcontains $verifier.status
    ) {
        throw "Independent verifier did not produce a coherent measured verdict"
    }
    $expectedMeasuredExit = if ($verifier.status -ceq "PASS") { 0 } else { 1 }
    if ($runExitCode -ne $expectedMeasuredExit) {
        throw "Independent verifier status and measured exit code disagree"
    }
    Assert-FrozenReferenceAt -Reference $verifier.manifest -ExpectedPath $VerifierManifest -Label "verifier report manifest"
    Assert-FrozenReferenceAt -Reference $verifier.instrument_freeze -ExpectedPath $InstrumentFreeze -Label "verifier report instrument freeze"
    if (
        $manifest.schema -isnot [string] -or
        $manifest.protocol -isnot [string] -or
        $manifest.source_commit -isnot [string] -or
        $manifest.schema -cne "m136-verifier-input-v1" -or
        $manifest.protocol -cne $VerifierProtocol -or
        $manifest.source_commit -cne $SourceCommit
    ) {
        throw "Verifier input manifest identity is invalid"
    }

    $expectedNames = @($CaptureSpecs | ForEach-Object { [string]$_.name } | Sort-Object)
    $observedNames = @($verifier.captures | ForEach-Object { [string]$_.capture } | Sort-Object)
    if (
        $expectedNames.Count -ne $observedNames.Count -or
        @(Compare-Object -ReferenceObject $expectedNames -DifferenceObject $observedNames).Count -ne 0
    ) {
        throw "Verifier report capture set differs from the preregistration"
    }

    $captureRows = @()
    [int64]$sumM8rDenominator = 0
    [int64]$sumM8rViolations = 0
    [int64]$sumM8oDenominator = 0
    [int64]$sumM8oViolations = 0
    foreach ($row in $verifier.captures) {
        if (
            [int64]$row.m8_r.denominator -le 0 -or
            [int64]$row.m8_o.denominator -le 0
        ) {
            throw "$($row.capture) has a non-positive census denominator"
        }
        $captureRoot = Join-Path $Out "captures\$($row.capture)"
        $primaryM8r = Get-Content -LiteralPath (Join-Path $captureRoot "checker-state\m8-r.json") -Raw | ConvertFrom-Json
        $primaryM8o = Get-Content -LiteralPath (Join-Path $captureRoot "checker-state\m8-o-m136.json") -Raw | ConvertFrom-Json
        if (
            [int64]$primaryM8r.denominator -ne [int64]$row.m8_r.denominator -or
            [int64]$primaryM8r.violations -ne [int64]$row.m8_r.violations -or
            [int64]$primaryM8o.denominator -ne [int64]$row.m8_o.denominator -or
            [int64]$primaryM8o.violations -ne [int64]$row.m8_o.violations
        ) {
            throw "$($row.capture) primary and independent counts disagree"
        }
        $manifestCapture = @(
            $manifest.captures | Where-Object { $_.name -eq $row.capture }
        )
        if ($manifestCapture.Count -ne 1) {
            throw "$($row.capture) has no unique verifier-manifest entry"
        }
        $manifestCapture = $manifestCapture[0]
        foreach ($reference in @(
            $manifestCapture.input_fingerprint_before,
            $manifestCapture.input_fingerprint_after,
            $manifestCapture.warpmap,
            $manifestCapture.output_tiff,
            $manifestCapture.render_provenance
        )) {
            Assert-FrozenFile -Reference $reference -Label "$($row.capture) manifest evidence"
        }
        foreach ($property in $manifestCapture.checker_artifacts.PSObject.Properties) {
            Assert-FrozenFile -Reference $property.Value -Label "$($row.capture) checker artifact $($property.Name)"
        }
        $traceState = [string]$manifestCapture.trace_state
        $checkerProvenance = Get-Content -LiteralPath (Join-Path $captureRoot "checker-state\provenance.json") -Raw | ConvertFrom-Json
        $declaredTraces = @($checkerProvenance.trace_sha256.PSObject.Properties)
        $actualTraces = @(Get-ChildItem -LiteralPath (Join-Path $traceState "blocks") -File)
        if ($declaredTraces.Count -ne $actualTraces.Count) {
            throw "$($row.capture) trace inventory changed after verification"
        }
        foreach ($trace in $declaredTraces) {
            $tracePath = Join-Path (Join-Path $traceState "blocks") $trace.Name
            if ((Get-Sha256 $tracePath) -ne [string]$trace.Value) {
                throw "$($row.capture) trace block changed after verification: $($trace.Name)"
            }
        }
        $sumM8rDenominator += [int64]$row.m8_r.denominator
        $sumM8rViolations += [int64]$row.m8_r.violations
        $sumM8oDenominator += [int64]$row.m8_o.denominator
        $sumM8oViolations += [int64]$row.m8_o.violations
        $captureRows += [ordered]@{
            capture = $row.capture
            m8_r_denominator = [int64]$row.m8_r.denominator
            m8_r_violations = [int64]$row.m8_r.violations
            m8_o_denominator = [int64]$row.m8_o.denominator
            m8_o_violations = [int64]$row.m8_o.violations
            m8_o_lower_violations = [int64]$row.m8_o.lower_violations
            m8_o_upper_violations = [int64]$row.m8_o.upper_violations
        }
    }
    if (
        $sumM8rDenominator -ne [int64]$verifier.aggregate.m8_r.denominator -or
        $sumM8rViolations -ne [int64]$verifier.aggregate.m8_r.violations -or
        $sumM8oDenominator -ne [int64]$verifier.aggregate.m8_o.denominator -or
        $sumM8oViolations -ne [int64]$verifier.aggregate.m8_o.violations
    ) {
        throw "Verifier aggregate does not equal the three per-capture censuses"
    }
    $aggregateViolations = [int64]$verifier.aggregate.m8_o.violations
    $m8oVerdict = if (
        $aggregateViolations -eq 0 -and
        @($captureRows | Where-Object { $_.m8_o_violations -ne 0 }).Count -eq 0
    ) {
        "PASS"
    }
    else {
        "FAIL"
    }
    $m8rVerdict = if (
        [int64]$verifier.aggregate.m8_r.violations -eq 0 -and
        @($captureRows | Where-Object { $_.m8_r_violations -ne 0 }).Count -eq 0
    ) {
        "PASS"
    }
    else {
        "FAIL"
    }
    $combinedVerdict = if (
        $m8oVerdict -eq "PASS" -and
        $m8rVerdict -eq "PASS" -and
        [int64]$verifier.crop_reference_identity.violations -eq 0
    ) {
        "PASS"
    }
    else {
        "FAIL"
    }
    if (
        $verifier.status -cne $combinedVerdict -or
        $runExitCode -ne $(if ($combinedVerdict -ceq "PASS") { 0 } else { 1 })
    ) {
        throw "Verifier status disagrees with its frozen combined decision rule"
    }
    $document = [ordered]@{
        schema = "m142-m136-summary-v1"
        schema_version = 1
        protocol = $Protocol
        status = $combinedVerdict
        combined_m8_status = $combinedVerdict
        decision = "PASS iff every capture and aggregate have M8-R V=0 and M8-O V=0; either aggregate V>=1 is FAIL"
        nonzero_floor = $null
        source_commit = $SourceCommit
        instrument_freeze = Get-FrozenFile $InstrumentFreeze
        verifier_report = Get-FrozenFile $VerifierReport
        captures = $captureRows
        aggregate = [ordered]@{
            m8_r = $verifier.aggregate.m8_r
            m8_o = $verifier.aggregate.m8_o
        }
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    Write-Json -Path $Summary -Value $document
    Write-Host (
        "M8 {0}: M8-R aggregate V={1}/{2}; M8-O aggregate V={3}/{4}" -f
        $combinedVerdict,
        $verifier.aggregate.m8_r.violations,
        $verifier.aggregate.m8_r.denominator,
        $verifier.aggregate.m8_o.violations,
        $verifier.aggregate.m8_o.denominator
    )
    return $(if ($combinedVerdict -eq "PASS") { 0 } else { 1 })
}

try {
    Assert-Prerequisites
    switch ($Mode) {
        "Prepare" {
            Prepare
            exit 0
        }
        "Commission" {
            Commission
            exit 0
        }
        "Freeze" {
            Freeze
            exit 0
        }
        "Census" {
            Census
            exit 0
        }
        "Verify" {
            exit (Verify)
        }
        "Summarize" {
            exit (Summarize)
        }
    }
}
catch {
    # Exit 1 is reserved for a successfully measured nonzero census.  Any
    # runner refusal, missing control, malformed evidence, or command failure
    # is UNMEASURED and must remain distinguishable from a measured FAIL.
    [Console]::Error.WriteLine("UNMEASURED: {0}", $_.Exception.Message)
    exit 2
}
