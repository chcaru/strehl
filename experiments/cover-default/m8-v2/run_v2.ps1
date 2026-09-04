[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("PREPARE", "INPUT-MANIFEST", "COMMISSION", "FULL", "VERIFY")]
    [string]$Phase,

    [Parameter(Mandatory)]
    [string]$OutputRoot,

    [string]$SourceCommit,
    [string]$EvidenceCommit,
    [string]$CaptureRoot,
    [string]$SidecarRoot,
    [string]$ExifTool = "exiftool.exe",
    [string]$InputManifestStage,
    [string]$InputManifestFinalPath,
    [string]$RunPlanStage,
    [string]$RunPlanFinalPath,
    [string]$InputManifest,
    [string]$RunPlan,
    [switch]$Identity,
    [ValidateSet("flat-1s", "flat-2p5s", "flat-6s")]
    [string]$Case,
    [ValidateSet("scale", "crop")]
    [string]$ArmMode,
    [switch]$ContinueAfterFlat1s,
    [string]$ArmReceipt
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Experiment = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Experiment "..\..\..")).Path
$ManifestTool = Join-Path $Experiment "manifest_v2.py"
$Checker = Join-Path $Experiment "checker_v2.py"
$Injector = Join-Path $Experiment "inject_trace_v2.py"
$TraceSource = Join-Path $Experiment "trace_v2.rs"
$FixtureSource = Join-Path $Experiment "fixture_v2.rs"
$ProducerTests = Join-Path $Experiment "producer_tests.py"
$ExternalComparator = Join-Path $Repo "experiments\cover-default\slide_external_decode.py"
$SlideSeries = Join-Path $Repo "experiments\cover-default\slide_series.py"
$MacroRoot = [IO.Path]::GetFullPath("D:\personal\macro")
$ExpectedCaptureRoot = [IO.Path]::GetFullPath(
    "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl"
)
$ExpectedSidecarRoot = [IO.Path]::GetFullPath(
    "D:\strehl-out\cover-default-slide-v2\warpmaps"
)
$ThreadVariables = @(
    "CARGO_BUILD_JOBS",
    "RAYON_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS"
)

function Get-FullPath {
    param([Parameter(Mandatory)][string]$Path)
    return [IO.Path]::GetFullPath($Path)
}

function Test-PathWithin {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Root
    )
    $full = Get-FullPath $Path
    $anchor = (Get-FullPath $Root).TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    )
    return $full.Equals($anchor, [StringComparison]::OrdinalIgnoreCase) -or
        $full.StartsWith(
            $anchor + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase
        )
}

function Assert-NoMacroWrite {
    param([Parameter(Mandatory)][string]$Path)
    $full = Get-FullPath $Path
    if (Test-PathWithin $full $MacroRoot) {
        throw "Refusing every write beneath ${MacroRoot}: $full"
    }
    # Reject junction/symlink indirection on every existing ancestor. A path
    # that is lexically outside the capture tree must not resolve back into it.
    $probe = Split-Path -Parent $full
    while ($probe -and (Test-Path -LiteralPath $probe)) {
        $item = Get-Item -LiteralPath $probe -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing output through reparse-point ancestor: $probe"
        }
        $next = Split-Path -Parent $probe
        if (-not $next -or $next -eq $probe) {
            break
        }
        $probe = $next
    }
}

function Assert-PrivateRootForPrepare {
    param([Parameter(Mandatory)][string]$Path)
    $full = Get-FullPath $Path
    Assert-NoMacroWrite $full
    if ($full.Length -gt 64) {
        throw "Private output root exceeds the 64-character M8 path limit: $full"
    }
    if (Test-PathWithin $full $Repo) {
        throw "Private output root must be outside the Git worktree: $full"
    }
    if (Test-Path -LiteralPath $full) {
        throw "Private output root must be absent/new: $full"
    }
    $parent = Split-Path -Parent $full
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Private output parent must already exist: $parent"
    }
    if ([IO.Path]::GetPathRoot($full).TrimEnd("\") -eq $full.TrimEnd("\")) {
        throw "A drive root is not a private experiment output root: $full"
    }
    return $full
}

function Assert-ExistingPrivateRoot {
    param([Parameter(Mandatory)][string]$Path)
    $full = Get-FullPath $Path
    Assert-NoMacroWrite $full
    if ($full.Length -gt 64) {
        throw "Private output root exceeds the 64-character M8 path limit: $full"
    }
    if (Test-PathWithin $full $Repo) {
        throw "Private output root must be outside the Git worktree: $full"
    }
    if (-not (Test-Path -LiteralPath $full -PathType Container)) {
        throw "Private output root does not exist: $full"
    }
    return $full
}

function Assert-NewOutputFile {
    param([Parameter(Mandatory)][string]$Path)
    $full = Get-FullPath $Path
    Assert-NoMacroWrite $full
    if (Test-Path -LiteralPath $full) {
        throw "Refusing to overwrite explicit staging output: $full"
    }
    $parent = Split-Path -Parent $full
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Output parent must already exist: $parent"
    }
    return $full
}

function Set-BaseEnvironment {
    foreach ($item in @(Get-ChildItem Env: | Where-Object Name -Like "STREHL_*")) {
        Remove-Item -LiteralPath "Env:$($item.Name)" -ErrorAction SilentlyContinue
    }
    foreach ($name in $ThreadVariables) {
        [Environment]::SetEnvironmentVariable($name, "8", "Process")
    }
    $env:STREHL_PYRAMID_WORKERS = "1"
    $env:PYTHONIOENCODING = "utf-8"
    foreach ($name in @(
        "RUSTFLAGS",
        "CARGO_ENCODED_RUSTFLAGS",
        "CARGO_TARGET_DIR",
        "CARGO_BUILD_TARGET",
        "RUSTC_WRAPPER",
        "RUSTC_WORKSPACE_WRAPPER",
        "RUSTUP_TOOLCHAIN",
        "SOURCE_DATE_EPOCH",
        "RUST_LOG",
        "RUST_BACKTRACE",
        "RUST_LIB_BACKTRACE"
    )) {
        Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
    foreach ($item in @(Get-ChildItem Env: | Where-Object {
        $_.Name -Like "CARGO_PROFILE_*" -or
        $_.Name -Like "CARGO_TARGET_*_RUSTFLAGS" -or
        $_.Name -Like "SCCACHE_*"
    })) {
        Remove-Item -LiteralPath "Env:$($item.Name)" -ErrorAction SilentlyContinue
    }
    $env:CARGO_INCREMENTAL = "0"
}

function Set-PrivateTemp {
    param([Parameter(Mandatory)][string]$Root)
    $path = Join-Path $Root "temp"
    Assert-NoMacroWrite $path
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        [void][IO.Directory]::CreateDirectory($path)
    }
    $env:TEMP = $path
    $env:TMP = $path
}

function Get-AuditEnvironment {
    $names = @(
        $ThreadVariables +
        @(
            "STREHL_PYRAMID_WORKERS",
            "STREHL_GATE_FLOOR",
            "STREHL_FULLRES_GATHER",
            "STREHL_DEFECT",
            "STREHL_RESTORE",
            "STREHL_ALIGN",
            "STREHL_WARPMAP",
            "STREHL_M8_V2_TRACE_DIR",
            "STREHL_FIX_CA",
            "STREHL_CONFIDENCE_MAP",
            "STREHL_CONFIDENCE_DEBUG",
            "STREHL_GATE_FLOOR_SCALE",
            "STREHL_RESTORE_SIGMA",
            "PYTHONIOENCODING",
            "PATH",
            "PATHEXT",
            "SystemRoot",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "PROCESSOR_ARCHITECTURE",
            "NUMBER_OF_PROCESSORS",
            "COMSPEC",
            "CARGO_HOME",
            "CARGO_INCREMENTAL",
            "RUSTUP_HOME",
            "RUSTUP_TOOLCHAIN"
        )
    )
    $environment = [ordered]@{}
    foreach ($name in $names) {
        $environment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    }
    return $environment
}

function Set-PlannedEnvironment {
    param([Parameter(Mandatory)]$Environment)
    Set-BaseEnvironment
    foreach ($property in $Environment.PSObject.Properties) {
        if ($null -eq $property.Value) {
            Remove-Item -LiteralPath "Env:$($property.Name)" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable(
                $property.Name,
                [string]$property.Value,
                "Process"
            )
        }
    }
    foreach ($name in $ThreadVariables) {
        $raw = [Environment]::GetEnvironmentVariable($name, "Process")
        $value = 0
        if (-not [int]::TryParse($raw, [ref]$value) -or $value -lt 1 -or $value -gt 8) {
            throw "${name} must be a numeric cap in 1..8, got '$raw'"
        }
    }
    if ($env:STREHL_PYRAMID_WORKERS -ne "1") {
        throw "The registered runner requires STREHL_PYRAMID_WORKERS=1"
    }
    if ($env:STREHL_GATE_FLOOR -ne "white") {
        throw "The registered runner requires STREHL_GATE_FLOOR=white"
    }
    if ($env:STREHL_FULLRES_GATHER -ne "on") {
        throw "The registered runner requires STREHL_FULLRES_GATHER=on"
    }
    if ($env:STREHL_DEFECT -ne "off" -or $env:STREHL_RESTORE -ne "off") {
        throw "Defect correction and restoration must both be explicitly off"
    }
    if (Test-Path Env:STREHL_CONFIDENCE_MAP) {
        throw "Confidence-map pass must be omitted"
    }
}

$Python = (Get-Command python -ErrorAction Stop).Source

function Write-AtomicObject {
    param(
        [Parameter(Mandatory)]$Object,
        [Parameter(Mandatory)][string]$Path
    )
    $full = Assert-NewOutputFile $Path
    $json = $Object | ConvertTo-Json -Depth 100
    $json | & $Python -B $ManifestTool atomic-json --output $full
    if ($LASTEXITCODE -ne 0) {
        throw "Atomic JSON write failed: $full"
    }
}

function Get-HashRecord {
    param([Parameter(Mandatory)][string]$Path)
    $full = (Resolve-Path -LiteralPath $Path).Path
    $item = Get-Item -LiteralPath $full -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected a regular non-reparse file: $full"
    }
    return [ordered]@{
        path = $full
        bytes = $item.Length
        sha256 = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
    }
}

function Invoke-Json {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = @(& $Python -B $ManifestTool @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "manifest_v2.py failed:`n$($output -join "`n")"
    }
    try {
        return ($output -join "`n") | ConvertFrom-Json
    }
    catch {
        throw "manifest_v2.py did not return JSON:`n$($output -join "`n")"
    }
}

function New-CommandRecord {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$Path
    )
    $record = [ordered]@{
        schema = "strehl-m8-v2-command"
        version = 1
        file = $File
        arguments = @($Arguments)
        working_directory = (Get-Location).Path
        environment = Get-AuditEnvironment
    }
    Write-AtomicObject $record $Path
    return Get-HashRecord $Path
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$LogPath,
        [switch]$ExpectFailure,
        [int]$ExpectedFailureCode = 1
    )
    $fullLog = Assert-NewOutputFile $LogPath
    $commandPath = "$fullLog.command.json"
    $commandRecord = New-CommandRecord $File $Arguments $commandPath
    $temporary = "$fullLog.partial-$PID"
    if (Test-Path -LiteralPath $temporary) {
        throw "Log staging file already exists: $temporary"
    }
    try {
        & $File @Arguments *> $temporary
        $code = $LASTEXITCODE
        [IO.File]::Move($temporary, $fullLog)
    }
    catch {
        if (Test-Path -LiteralPath $temporary) {
            [IO.File]::Move($temporary, $fullLog)
        }
        throw
    }
    if ($ExpectFailure) {
        if ($code -ne $ExpectedFailureCode) {
            throw "Command expected exit $ExpectedFailureCode, got ${code}: $File $($Arguments -join ' ')"
        }
    }
    elseif ($code -ne 0) {
        $tail = Get-Content -LiteralPath $fullLog -Tail 80
        throw "Command exited ${code}: $File $($Arguments -join ' ')`n$($tail -join "`n")"
    }
    return [ordered]@{
        file = $File
        arguments = @($Arguments)
        exit_code = $code
        command = $commandRecord
        log = Get-HashRecord $fullLog
    }
}

function Get-TreeAudit {
    param([Parameter(Mandatory)][string]$Root)
    return Invoke-Json @("tree-audit", "--root", $Root)
}

function Assert-TreeEqual {
    param(
        [Parameter(Mandatory)]$Expected,
        [Parameter(Mandatory)]$Actual,
        [Parameter(Mandatory)][string]$Label
    )
    if ($Expected.inventory_sha256 -ne $Actual.inventory_sha256) {
        throw "$Label source tree changed: $($Expected.inventory_sha256) != $($Actual.inventory_sha256)"
    }
}

function Get-AllFileRecords {
    param(
        [Parameter(Mandatory)][string]$Root,
        [string[]]$Exclude = @()
    )
    $excluded = @{}
    foreach ($path in $Exclude) {
        $excluded[(Get-FullPath $path).ToLowerInvariant()] = $true
    }
    $records = @()
    foreach ($file in Get-ChildItem -LiteralPath $Root -Force -Recurse -File |
        Sort-Object FullName) {
        if (-not $excluded.ContainsKey($file.FullName.ToLowerInvariant())) {
            $records += Get-HashRecord $file.FullName
        }
    }
    return @($records)
}

function Assert-PreparedBinaries {
    param([Parameter(Mandatory)]$Prepare)
    foreach ($name in @("uninstrumented", "instrumented", "fixture")) {
        $expected = $Prepare.binaries.$name
        $actual = Get-HashRecord $expected.path
        if ($actual.sha256 -ne $expected.sha256 -or $actual.bytes -ne $expected.bytes) {
            throw "Prepared binary '$name' changed"
        }
    }
}

function Get-HostToolRecords {
    $records = [ordered]@{}
    foreach ($name in @("git", "cargo", "rustc", "tar.exe", "powercfg.exe")) {
        $command = Get-Command $name -ErrorAction Stop
        $records[$name] = Get-HashRecord $command.Source
    }
    $records["pwsh"] = Get-HashRecord (Get-Process -Id $PID).Path
    return $records
}

function Assert-HostRuntime {
    param([Parameter(Mandatory)]$Prepare)
    $runtime = Invoke-Json @("runtime-info")
    foreach ($field in @("numpy", "tifffile", "rawpy")) {
        if ([string]$runtime.$field -ne [string]$Prepare.runtime.$field) {
            throw "Runtime package '$field' changed after PREPARE"
        }
    }
    if ([string]$runtime.python.version -ne [string]$Prepare.runtime.python.version -or
        [string]$runtime.python.executable.sha256 -ne
        [string]$Prepare.runtime.python.executable.sha256) {
        throw "Python runtime identity changed after PREPARE"
    }
    if (($runtime.libraw -join ".") -ne ($Prepare.runtime.libraw -join ".")) {
        throw "LibRaw runtime identity changed after PREPARE"
    }
    if ([string]$runtime.os.platform -ne [string]$Prepare.runtime.os.platform) {
        throw "OS identity changed after PREPARE"
    }
    foreach ($property in $Prepare.host_tools.PSObject.Properties) {
        $current = Get-HashRecord $property.Value.path
        if ($current.sha256 -ne $property.Value.sha256) {
            throw "Host tool '$($property.Name)' changed after PREPARE"
        }
    }
    $power = @(& powercfg.exe /getactivescheme 2>&1)
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "powercfg /getactivescheme exited $code"
    }
    if (($power -join "`n").Trim() -ne [string]$Prepare.power_plan_text) {
        throw "Active Windows power plan changed after PREPARE"
    }
}

function Assert-PreparedTrees {
    param([Parameter(Mandatory)]$Prepare)
    $un = Get-TreeAudit $Prepare.snapshots.uninstrumented.path
    $ins = Get-TreeAudit $Prepare.snapshots.instrumented.path
    Assert-TreeEqual $Prepare.snapshots.uninstrumented.post_build $un "uninstrumented"
    Assert-TreeEqual $Prepare.snapshots.instrumented.post_build $ins "instrumented"
    return [ordered]@{
        uninstrumented = $un
        instrumented = $ins
    }
}

function Invoke-ToolAudit {
    param([Parameter(Mandatory)][string]$Commit)
    return Invoke-Json @(
        "tool-audit",
        "--repo", $Repo,
        "--commit", $Commit,
        "--extra", "experiments/cover-default/slide_external_decode.py",
        "--extra", "experiments/cover-default/slide_series.py"
    )
}

function Assert-ReadyForRealArm {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$PlanPath,
        [Parameter(Mandatory)][string]$InputPath,
        [Parameter(Mandatory)][string]$Evidence
    )
    if (-not $Evidence) {
        throw "-EvidenceCommit is mandatory for every identity/full real arm"
    }
    $preparePath = Join-Path $Root "prepare.json"
    $prepare = Get-Content -LiteralPath $preparePath -Raw | ConvertFrom-Json
    [void](Invoke-Json @(
        "validate-plan",
        "--plan", $PlanPath,
        "--prepare", $preparePath,
        "--input", $InputPath,
        "--output-root", $Root
    ))
    [void](Invoke-Json @(
        "committed-files",
        "--repo", $Repo,
        "--commit", $Evidence,
        "--path", $PlanPath,
        "--path", $InputPath
    ))
    [void](Invoke-ToolAudit $prepare.source_commit)
    [void](Invoke-Json @("verify-input", "--input", $InputPath))
    Assert-HostRuntime $prepare
    Assert-PreparedBinaries $prepare
    $trees = Assert-PreparedTrees $prepare
    return [ordered]@{
        prepare_path = $preparePath
        prepare = $prepare
        trees = $trees
        plan = (Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json)
    }
}

function New-ArmLock {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Name
    )
    $path = Join-Path $Root "locks\$Name.lock.json"
    Assert-NoMacroWrite $path
    $stream = [IO.File]::Open(
        $path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::Read
    )
    $payload = [Text.Encoding]::UTF8.GetBytes(
        (([ordered]@{
            schema = "strehl-m8-v2-arm-lock"
            version = 1
            arm = $Name
            runner_pid = $PID
        } | ConvertTo-Json) + "`n")
    )
    $stream.Write($payload, 0, $payload.Length)
    $stream.Flush($true)
    return [ordered]@{ path = $path; stream = $stream }
}

function Assert-RenderLog {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][ValidateSet("scale", "crop")][string]$Mode,
        [AllowNull()][object]$ExpectedCrop,
        [switch]$IdentityArm
    )
    $text = Get-Content -LiteralPath $Path -Raw
    foreach ($required in @(
        "merge backend",
        "pyramid",
        "coverage mode",
        $Mode,
        "CatmullRom",
        "defect map",
        "off"
    )) {
        if ($text.IndexOf($required, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw "Render log does not prove required setting '$required': $Path"
        }
    }
    if ($IdentityArm) {
        if ($text -notmatch "lateral CA\s*: off") {
            throw "Identity render did not prove lateral CA was off: $Path"
        }
    }
    elseif ($text -notmatch "lateral CA\s*: CORRECTING") {
        throw "Full arm did not prove default active lateral CA: $Path"
    }
    if ($text -match "confidence map") {
        throw "A confidence-map pass appeared in a registered render log: $Path"
    }
    $cropPattern = "coverage\s*:\s*CROPPED to the region EVERY frame covers -- " +
        "(\d+) x (\d+) plane px at \((\d+), (\d+)\) of (\d+) x (\d+)"
    $cropMatches = [regex]::Matches(
        $text,
        $cropPattern,
        [Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if ($Mode -eq "crop") {
        $expected = @($ExpectedCrop)
        if ($expected.Count -ne 4) {
            throw "Crop render has no frozen x,y,w,h expectation"
        }
        if ($cropMatches.Count -ne 1) {
            throw "Crop render must report exactly one parseable rectangle: $Path"
        }
        $match = $cropMatches[0]
        $actual = @(
            [int]$match.Groups[3].Value,
            [int]$match.Groups[4].Value,
            [int]$match.Groups[1].Value,
            [int]$match.Groups[2].Value
        )
        for ($index = 0; $index -lt 4; $index++) {
            if ($actual[$index] -ne [int]$expected[$index]) {
                throw "Crop render reported $($actual -join ',') instead of frozen " +
                    "$($expected -join ','): $Path"
            }
        }
        return [ordered]@{
            x = $actual[0]
            y = $actual[1]
            width = $actual[2]
            height = $actual[3]
        }
    }
    if ($cropMatches.Count -ne 0) {
        throw "Scale render unexpectedly reported a Crop rectangle: $Path"
    }
    return $null
}

function Invoke-RenderLogCommission {
    param([Parameter(Mandatory)][string]$Root)
    [void][IO.Directory]::CreateDirectory($Root)
    $settings = @(
        "merge backend   : pyramid",
        "coverage mode   : crop",
        "resampler       : CatmullRom",
        "defect map      : off",
        "lateral CA      : CORRECTING"
    )
    $coverage = "coverage      : CROPPED to the region EVERY frame covers -- " +
        "3466 x 2310 plane px at (25, 17) of 3516 x 2344"
    $correctPath = Join-Path $Root "crop-correct.log"
    Write-AtomicText $correctPath (($settings + $coverage) -join "`n")
    $restored = Assert-RenderLog $correctPath "crop" -ExpectedCrop @(25, 17, 3466, 2310)

    $plants = [ordered]@{
        wrong_origin = $coverage.Replace("(25, 17)", "(26, 17)")
        wrong_dimensions = $coverage.Replace("3466 x 2310", "3467 x 2310")
        duplicate = "$coverage`n$coverage"
    }
    $files = @((Get-HashRecord $correctPath))
    $refusals = [ordered]@{}
    foreach ($plant in $plants.GetEnumerator()) {
        $path = Join-Path $Root "crop-$($plant.Key).log"
        Write-AtomicText $path (($settings + $plant.Value) -join "`n")
        $files += Get-HashRecord $path
        try {
            [void](Assert-RenderLog $path "crop" -ExpectedCrop @(25, 17, 3466, 2310))
        }
        catch {
            $refusals[$plant.Key] = $_.Exception.Message
            continue
        }
        throw "Render-log commissioning accepted the $($plant.Key) Crop plant"
    }
    if ($refusals.Count -ne $plants.Count) {
        throw "Render-log commissioning did not refuse every Crop plant"
    }
    return [ordered]@{
        status = "COMMISSIONED"
        fixed_predicate = [ordered]@{ x = 25; y = 17; width = 3466; height = 2310 }
        restored = $restored
        refusals = $refusals
        files = $files
    }
}

function Get-ArmEntry {
    param(
        [Parameter(Mandatory)]$PlanObject,
        [Parameter(Mandatory)][string]$CaseName,
        [Parameter(Mandatory)][string]$Mode
    )
    $found = @($PlanObject.arms | Where-Object {
        $_.case -eq $CaseName -and $_.mode -eq $Mode
    })
    if ($found.Count -ne 1) {
        throw "Run plan has $($found.Count) entries for $CaseName/$Mode"
    }
    return $found[0]
}

function Assert-LaterExposureAllowed {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$CaseName
    )
    if ($CaseName -eq "flat-1s") {
        return
    }
    if (-not $ContinueAfterFlat1s) {
        throw "Later exposures require -ContinueAfterFlat1s after the operator reads flat-1s"
    }
    $previousCase = if ($CaseName -eq "flat-6s") {
        "flat-2p5s"
    }
    else {
        "flat-1s"
    }
    $scaleReceipt = Join-Path $Root "arms\$previousCase-scale\receipt.json"
    $cropReceipt = Join-Path $Root "arms\$previousCase-crop\receipt.json"
    foreach ($path in @($scaleReceipt, $cropReceipt)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Complete both $previousCase arms before ${CaseName}: missing $path"
        }
        [void](Invoke-Json @("verify-arm", "--receipt", $path))
    }
    $cropArm = Get-Content -LiteralPath $cropReceipt -Raw | ConvertFrom-Json
    $result = Get-Content -LiteralPath $cropArm.result.path -Raw | ConvertFrom-Json
    $violations = [long]$result.m8_r.primary_full.violations +
        [long]$result.m8_r.delivered_subset.violations +
        [long]$result.m8_o.violations
    if ($violations -ne 0) {
        throw "Stopping rule: $previousCase Crop has $violations M8-R/M8-O violations"
    }
}

function Assert-SyntheticCommission {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)]$Prepare
    )
    $path = Join-Path $Root "commission\synthetic\receipt.json"
    $receipt = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($receipt.schema -ne "strehl-m8-v2-synthetic-commission" -or
        [int]$receipt.version -ne 1 -or
        $receipt.source_commit -ne $Prepare.source_commit) {
        throw "Synthetic commissioning receipt is unsupported or belongs to another source"
    }
    foreach ($file in $receipt.files) {
        $current = Get-HashRecord $file.path
        if ($current.sha256 -ne $file.sha256 -or $current.bytes -ne $file.bytes) {
            throw "Synthetic commissioning evidence changed: $($file.path)"
        }
    }
    foreach ($operation in $receipt.operations) {
        foreach ($record in @($operation.command, $operation.log)) {
            $current = Get-HashRecord $record.path
            if ($current.sha256 -ne $record.sha256 -or $current.bytes -ne $record.bytes) {
                throw "Synthetic commissioning command/log changed: $($record.path)"
            }
        }
    }
}

function Invoke-PlannedRender {
    param(
        [Parameter(Mandatory)]$Command,
        [Parameter(Mandatory)][string]$LogPath
    )
    Set-PlannedEnvironment $Command.environment
    return Invoke-Logged ([string]$Command.file) @(
        $Command.arguments | ForEach-Object { [string]$_ }
    ) $LogPath
}

function Invoke-RealArm {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)]$Entry,
        [Parameter(Mandatory)]$Readiness,
        [Parameter(Mandatory)][string]$PlanPath,
        [Parameter(Mandatory)][string]$InputPath,
        [Parameter(Mandatory)][string]$Evidence,
        [switch]$IdentityArm
    )
    $armRoot = Get-FullPath $Entry.root
    Assert-NoMacroWrite $armRoot
    if (-not (Test-PathWithin $armRoot (Join-Path $Root "arms"))) {
        throw "Planned arm root escapes the private arms directory: $armRoot"
    }
    if (Test-Path -LiteralPath $armRoot) {
        throw "Arm output must be absent/new; duplicate run refused: $armRoot"
    }
    $lockName = if ($IdentityArm) { "identity-crop" } else { "$($Entry.case)-$($Entry.mode)" }
    $lock = New-ArmLock $Root $lockName
    try {
        [void][IO.Directory]::CreateDirectory($armRoot)
        foreach ($relative in @("tiff", "logs", "commands")) {
            [void][IO.Directory]::CreateDirectory((Join-Path $armRoot $relative))
        }

        $commands = @()
        if ($IdentityArm) {
            $released = Get-FullPath $Entry.released_reference
            if (Test-PathWithin $released $MacroRoot) {
                throw "Identity must use the released private copy, never the capture tree"
            }
            $releasedHash = Get-HashRecord $released
            if ($releasedHash.sha256 -ne $Entry.released_reference_sha256) {
                throw "Released copied reference hash differs from the frozen flat-1s hash"
            }
            [void][IO.Directory]::CreateDirectory($Entry.source)
            Copy-Item -LiteralPath $released -Destination $Entry.raw
            if ((Get-FileHash -LiteralPath $Entry.raw -Algorithm SHA256).Hash -ne
                $Entry.released_reference_sha256) {
                throw "Copied identity RAW changed during the private copy"
            }
            $identitySidecarLog = Join-Path $armRoot "logs\identity-sidecar.log"
            $commands += Invoke-Logged $Python @(
                "-B", $ManifestTool, "identity-sidecar",
                "--source", [string]$Entry.raw,
                "--output", [string]$Entry.sidecar
            ) $identitySidecarLog
            $commands += Invoke-Logged $Python @(
                "-B", $ManifestTool, "single-inventory",
                "--source", [string]$Entry.raw,
                "--output", [string]$Entry.source_inventory
            ) (Join-Path $armRoot "logs\identity-inventory.log")
        }
        else {
            $commands += Invoke-Logged $Python @(
                "-B", $ManifestTool, "extract-inventory",
                "--input", $InputPath,
                "--case", [string]$Entry.case,
                "--output", [string]$Entry.source_inventory
            ) (Join-Path $armRoot "logs\extract-inventory.log")
        }

        $writerRecord = Join-Path $armRoot "writer-record.json"
        $writer = [ordered]@{
            schema = "strehl-m8-v2-writer-record"
            version = 1
            arm = $lockName
            lock = Get-HashRecord $lock.path
            writer_processes = @(
                [ordered]@{
                    ordinal = 1
                    launcher_pid = $PID
                    executable = [string]$Entry.render_commands.instrumented_on.file
                    trace_dir = [string]$Entry.render_commands.instrumented_on.environment.STREHL_M8_V2_TRACE_DIR
                }
            )
        }
        Write-AtomicObject $writer $writerRecord

        $renderSpecs = @(
            [ordered]@{
                role = "uninstrumented"
                command = $Entry.render_commands.uninstrumented
                log = Join-Path $armRoot "logs\render-uninstrumented.log"
            },
            [ordered]@{
                role = "instrumented_off"
                command = $Entry.render_commands.instrumented_off
                log = Join-Path $armRoot "logs\render-instrumented-off.log"
            },
            [ordered]@{
                role = "instrumented_on"
                command = $Entry.render_commands.instrumented_on
                log = Join-Path $armRoot "logs\render-instrumented-on.log"
            }
        )
        $reportedCropRectangles = [ordered]@{}
        foreach ($spec in $renderSpecs) {
            $commands += Invoke-PlannedRender $spec.command $spec.log
            $reportedCropRectangles[$spec.role] = Assert-RenderLog `
                $spec.log ([string]$Entry.mode) `
                -ExpectedCrop $Entry.crop_xywh -IdentityArm:$IdentityArm
            if ($spec.role -eq "instrumented_off" -and
                (Test-Path -LiteralPath $Entry.render_commands.instrumented_on.environment.STREHL_M8_V2_TRACE_DIR)) {
                throw "Tracing-off render touched the trace directory"
            }
        }

        $outputRecords = [ordered]@{}
        foreach ($role in @("uninstrumented", "instrumented_off", "instrumented_on")) {
            $outputRecords[$role] = Get-HashRecord $Entry.outputs.$role
        }
        $hashes = @(
            $outputRecords.uninstrumented.sha256,
            $outputRecords.instrumented_off.sha256,
            $outputRecords.instrumented_on.sha256
        )
        if (@($hashes | Select-Object -Unique).Count -ne 1) {
            throw "OUTPUT TRANSPARENCY FAILURE: three TIFF SHA-256 values differ; checker remains unopened"
        }

        # The trace and checker are inspected only after the three output hashes
        # have proved identical.
        $traceAuditPath = Join-Path $armRoot "trace-audit.json"
        $traceArguments = @(
            "-B", $ManifestTool, "trace-audit",
            "--trace-dir", [string]$Entry.render_commands.instrumented_on.environment.STREHL_M8_V2_TRACE_DIR,
            "--inventory", [string]$Entry.source_inventory,
            "--writer-record", $writerRecord
        )
        foreach ($hash in $hashes) {
            $traceArguments += @("--tiff-hash", $hash)
        }
        $traceArguments += @("--output", $traceAuditPath)
        $commands += Invoke-Logged $Python $traceArguments (
            Join-Path $armRoot "logs\trace-audit.log"
        )

        $sidecarHash = if ($IdentityArm) {
            (Get-FileHash -LiteralPath $Entry.sidecar -Algorithm SHA256).Hash
        }
        else {
            [string]$Entry.sidecar.sha256
        }
        $checkerArguments = @(
            $Entry.checker_command.arguments | ForEach-Object {
                if ([string]$_ -eq "{IDENTITY_SIDECAR_SHA256}") {
                    $sidecarHash
                }
                else {
                    [string]$_
                }
            }
        )
        Set-PlannedEnvironment $Entry.render_commands.instrumented_on.environment
        Remove-Item Env:STREHL_M8_V2_TRACE_DIR -ErrorAction SilentlyContinue
        $commands += Invoke-Logged ([string]$Entry.checker_command.file) $checkerArguments (
            Join-Path $armRoot "logs\checker-adjudicate.log"
        )
        $resultPath = Join-Path $armRoot "adjudication\result.json"
        $commands += Invoke-Logged $Python @(
            "-B", $Checker, "verify", "--result", $resultPath
        ) (Join-Path $armRoot "logs\checker-verify.log")

        $externalRecord = $null
        if ($IdentityArm) {
            $externalPath = Join-Path $armRoot "external-identity.json"
            $externalArgs = @(
                "-B", $ManifestTool, "external-identity",
                "--comparator", $ExternalComparator,
                "--raw", [string]$Entry.raw,
                "--crop", (($Entry.crop_xywh | ForEach-Object { [string]$_ }) -join ",")
            )
            foreach ($role in @("uninstrumented", "instrumented_off", "instrumented_on")) {
                $externalArgs += @("--candidate", [string]$Entry.outputs.$role)
            }
            $externalArgs += @("--output", $externalPath)
            $commands += Invoke-Logged $Python $externalArgs (
                Join-Path $armRoot "logs\external-identity.log"
            )
            $externalRecord = Get-HashRecord $externalPath
        }

        [void](Invoke-Json @("verify-input", "--input", $InputPath))
        $afterTrees = Assert-PreparedTrees $Readiness.prepare
        $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        $indexPath = Join-Path (Split-Path -Parent $resultPath) $result.evidence_index.path
        $indexRecord = Get-HashRecord $indexPath
        if ($indexRecord.sha256 -ne $result.evidence_index.sha256) {
            throw "Checker result-to-index hash differs"
        }

        $receiptPath = Join-Path $armRoot "receipt.json"
        $files = Get-AllFileRecords $armRoot @($receiptPath)
        $files += Get-HashRecord $lock.path
        $tracePayloadHash = (Get-FileHash -LiteralPath $traceAuditPath -Algorithm SHA256).Hash
        $receipt = [ordered]@{
            schema = "strehl-m8-v2-arm-receipt"
            version = 1
            arm = $lockName
            kind = if ($IdentityArm) { "identity" } else { "full" }
            case = [string]$Entry.case
            mode = [string]$Entry.mode
            evidence_commit = $Evidence
            source_commit = $Readiness.prepare.source_commit
            run_plan = Get-HashRecord $PlanPath
            input_manifest = Get-HashRecord $InputPath
            prepare_receipt = Get-HashRecord $Readiness.prepare_path
            binaries = $Readiness.prepare.binaries
            outputs = $outputRecords
            source_trees = $afterTrees
            commands = @($commands)
            trace = [ordered]@{
                trace_dir = [string]$Entry.render_commands.instrumented_on.environment.STREHL_M8_V2_TRACE_DIR
                inventory = [string]$Entry.source_inventory
                writer_record = $writerRecord
                transparency_hashes = $hashes
                audit = Get-HashRecord $traceAuditPath
                audit_payload_sha256 = $tracePayloadHash
            }
            result = Get-HashRecord $resultPath
            evidence_index = $indexRecord
            external_identity = $externalRecord
            reported_crop_rectangles = $reportedCropRectangles
            files = @($files)
        }
        Write-AtomicObject $receipt $receiptPath
        return $receiptPath
    }
    finally {
        if ($null -ne $lock -and $null -ne $lock.stream) {
            $lock.stream.Dispose()
        }
    }
}

function Start-CapturedProcess {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $File
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) {
        [void]$info.ArgumentList.Add($argument)
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    if (-not $process.Start()) {
        throw "Could not start $File"
    }
    return [ordered]@{
        process = $process
        stdout = $process.StandardOutput.ReadToEndAsync()
        stderr = $process.StandardError.ReadToEndAsync()
    }
}

function Write-AtomicText {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Text
    )
    $full = Assert-NewOutputFile $Path
    $temporary = "$full.partial-$PID"
    [IO.File]::WriteAllText($temporary, $Text, [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $full)
}

Set-BaseEnvironment

switch ($Phase) {
    "PREPARE" {
        if (-not $SourceCommit) {
            throw "-SourceCommit must be an explicit committed 40-hex SHA"
        }
        $root = Assert-PrivateRootForPrepare $OutputRoot

        # This runs before creating the private root.  The runner, producer,
        # checker, fixture, schemas and related external comparators must all be
        # committed at the requested source commit and byte-identical in the
        # operator checkout.
        $toolAudit = Invoke-ToolAudit $SourceCommit
        $resolvedCommit = [string]$toolAudit.commit

        [void][IO.Directory]::CreateDirectory($root)
        foreach ($relative in @(
            "commands",
            "logs",
            "snapshots",
            "targets",
            "arms",
            "locks",
            "commission",
            "temp"
        )) {
            [void][IO.Directory]::CreateDirectory((Join-Path $root $relative))
        }
        Set-PrivateTemp $root
        $operations = @()
        $toolAuditPath = Join-Path $root "tool-audit.json"
        Write-AtomicObject $toolAudit $toolAuditPath

        $gitTreePath = Join-Path $root "source-blobs.json"
        $operations += Invoke-Logged $Python @(
            "-B", $ManifestTool, "git-tree",
            "--repo", $Repo,
            "--commit", $resolvedCommit,
            "--output", $gitTreePath
        ) (Join-Path $root "logs\git-tree.log")

        $archive = Join-Path $root "source.tar"
        $operations += Invoke-Logged "git" @(
            "-C", $Repo,
            "archive",
            "--format=tar",
            "--output=$archive",
            $resolvedCommit
        ) (Join-Path $root "logs\git-archive.log")

        $unSnapshot = Join-Path $root "snapshots\uninstrumented"
        $inSnapshot = Join-Path $root "snapshots\instrumented"
        [void][IO.Directory]::CreateDirectory($unSnapshot)
        [void][IO.Directory]::CreateDirectory($inSnapshot)
        $operations += Invoke-Logged "tar.exe" @(
            "-xf", $archive, "-C", $unSnapshot
        ) (Join-Path $root "logs\extract-uninstrumented.log")
        $operations += Invoke-Logged "tar.exe" @(
            "-xf", $archive, "-C", $inSnapshot
        ) (Join-Path $root "logs\extract-instrumented.log")

        $unArchiveTree = Get-TreeAudit $unSnapshot
        $inArchiveTree = Get-TreeAudit $inSnapshot
        Assert-TreeEqual $unArchiveTree $inArchiveTree "two archive exports"

        $fixtureTarget = Join-Path $inSnapshot "crates\strehl-cli\examples\m8_fixture_v2.rs"
        $fixtureParent = Split-Path -Parent $fixtureTarget
        [void][IO.Directory]::CreateDirectory($fixtureParent)
        Copy-Item -LiteralPath $FixtureSource -Destination $fixtureTarget
        $injectionRecord = Join-Path $root "injection.json"
        $operations += Invoke-Logged $Python @(
            "-B", $Injector, $inSnapshot,
            "--hook", $TraceSource,
            "--record", $injectionRecord
        ) (Join-Path $root "logs\inject.log")

        $unPreBuild = Get-TreeAudit $unSnapshot
        $inPreBuild = Get-TreeAudit $inSnapshot
        $unTarget = Join-Path $root "targets\uninstrumented"
        $inTarget = Join-Path $root "targets\instrumented"
        [void][IO.Directory]::CreateDirectory($unTarget)
        [void][IO.Directory]::CreateDirectory($inTarget)
        $operations += Invoke-Logged "cargo" @(
            "build", "--release", "--locked",
            "-p", "strehl-cli", "--bin", "strehl", "-j", "8",
            "--manifest-path", (Join-Path $unSnapshot "Cargo.toml"),
            "--target-dir", $unTarget
        ) (Join-Path $root "logs\build-uninstrumented.log")
        $operations += Invoke-Logged "cargo" @(
            "build", "--release", "--locked",
            "-p", "strehl-cli", "--bin", "strehl", "-j", "8",
            "--manifest-path", (Join-Path $inSnapshot "Cargo.toml"),
            "--target-dir", $inTarget
        ) (Join-Path $root "logs\build-instrumented.log")
        $operations += Invoke-Logged "cargo" @(
            "build", "--release", "--locked",
            "-p", "strehl-cli", "--example", "m8_fixture_v2", "-j", "8",
            "--manifest-path", (Join-Path $inSnapshot "Cargo.toml"),
            "--target-dir", $inTarget
        ) (Join-Path $root "logs\build-fixture.log")

        $unPostBuild = Get-TreeAudit $unSnapshot
        $inPostBuild = Get-TreeAudit $inSnapshot
        Assert-TreeEqual $unPreBuild $unPostBuild "uninstrumented build"
        Assert-TreeEqual $inPreBuild $inPostBuild "instrumented build"

        $operations += Invoke-Logged "rustc" @("-Vv") (
            Join-Path $root "logs\rustc-version.log"
        )
        $operations += Invoke-Logged "cargo" @("-V") (
            Join-Path $root "logs\cargo-version.log"
        )
        $operations += Invoke-Logged "powercfg.exe" @("/getactivescheme") (
            Join-Path $root "logs\power-plan.log"
        )
        $runtime = Invoke-Json @("runtime-info")
        $powerPlanText = (
            Get-Content -LiteralPath (Join-Path $root "logs\power-plan.log") -Raw
        ).Trim()

        $unBinary = Join-Path $unTarget "release\strehl.exe"
        $inBinary = Join-Path $inTarget "release\strehl.exe"
        $fixtureBinary = Join-Path $inTarget "release\examples\m8_fixture_v2.exe"
        $preparePath = Join-Path $root "prepare.json"
        $prepare = [ordered]@{
            schema = "strehl-m8-v2-prepare"
            version = 1
            repo = $Repo
            source_commit = $resolvedCommit
            output_root = $root
            git_tree = Get-HashRecord $gitTreePath
            git_archive = Get-HashRecord $archive
            tool_audit = Get-HashRecord $toolAuditPath
            source_files = [ordered]@{
                cargo_lock = Get-HashRecord (Join-Path $unSnapshot "Cargo.lock")
                rust_toolchain = Get-HashRecord (Join-Path $unSnapshot "rust-toolchain.toml")
                cargo_toml = Get-HashRecord (Join-Path $unSnapshot "Cargo.toml")
            }
            snapshots = [ordered]@{
                uninstrumented = [ordered]@{
                    path = $unSnapshot
                    archive = $unArchiveTree
                    pre_build = $unPreBuild
                    post_build = $unPostBuild
                }
                instrumented = [ordered]@{
                    path = $inSnapshot
                    archive = $inArchiveTree
                    pre_build = $inPreBuild
                    post_build = $inPostBuild
                    injection = Get-HashRecord $injectionRecord
                    fixture = Get-HashRecord $fixtureTarget
                }
            }
            binaries = [ordered]@{
                uninstrumented = Get-HashRecord $unBinary
                instrumented = Get-HashRecord $inBinary
                fixture = Get-HashRecord $fixtureBinary
            }
            runtime = $runtime
            host_tools = Get-HostToolRecords
            toolchain = [ordered]@{
                rustc = Get-HashRecord (Join-Path $root "logs\rustc-version.log")
                cargo = Get-HashRecord (Join-Path $root "logs\cargo-version.log")
            }
            os = $runtime.os
            power_plan = Get-HashRecord (Join-Path $root "logs\power-plan.log")
            power_plan_text = $powerPlanText
            environment = Get-AuditEnvironment
            operations = @($operations)
            full_stack_rendered = $false
        }
        Write-AtomicObject $prepare $preparePath
        Write-Output "PREPARED $preparePath"
    }

    "INPUT-MANIFEST" {
        $root = Assert-ExistingPrivateRoot $OutputRoot
        Set-PrivateTemp $root
        foreach ($required in @(
            "CaptureRoot",
            "SidecarRoot",
            "InputManifestStage",
            "InputManifestFinalPath",
            "RunPlanStage",
            "RunPlanFinalPath"
        )) {
            if (-not (Get-Variable -Name $required -ValueOnly)) {
                throw "-$required is mandatory for INPUT-MANIFEST"
            }
        }
        if ((Get-FullPath $CaptureRoot) -ne $ExpectedCaptureRoot) {
            throw "CaptureRoot must be the exact released path $ExpectedCaptureRoot"
        }
        if ((Get-FullPath $SidecarRoot) -ne $ExpectedSidecarRoot) {
            throw "SidecarRoot must be the exact released path $ExpectedSidecarRoot"
        }
        $inputStage = Assert-NewOutputFile $InputManifestStage
        $planStage = Assert-NewOutputFile $RunPlanStage
        Assert-NoMacroWrite $InputManifestFinalPath
        Assert-NoMacroWrite $RunPlanFinalPath
        $preparePath = Join-Path $root "prepare.json"
        if (-not (Test-Path -LiteralPath $preparePath -PathType Leaf)) {
            throw "PREPARE must complete first: $preparePath"
        }
        $operations = @()
        $operations += Invoke-Logged $Python @(
            "-B", $ManifestTool, "input-manifest",
            "--capture-root", $CaptureRoot,
            "--sidecar-root", $SidecarRoot,
            "--exif-tool", $ExifTool,
            "--output", $inputStage
        ) (Join-Path $root "logs\input-manifest.log")
        $operations += Invoke-Logged $Python @(
            "-B", $ManifestTool, "seal-plan",
            "--prepare", $preparePath,
            "--input", $inputStage,
            "--input-runtime-path", (Get-FullPath $InputManifestFinalPath),
            "--plan-runtime-path", (Get-FullPath $RunPlanFinalPath),
            "--output", $planStage
        ) (Join-Path $root "logs\seal-plan.log")
        $receipt = [ordered]@{
            schema = "strehl-m8-v2-input-phase"
            version = 1
            input_manifest_stage = Get-HashRecord $inputStage
            input_manifest_runtime_path = Get-FullPath $InputManifestFinalPath
            run_plan_stage = Get-HashRecord $planStage
            run_plan_runtime_path = Get-FullPath $RunPlanFinalPath
            operations = @($operations)
            next = "Review, place these exact bytes at the runtime paths, commit both, then pass that full SHA as -EvidenceCommit."
        }
        Write-AtomicObject $receipt (Join-Path $root "input-phase.json")
        Write-Output "INPUT MANIFEST STAGED $inputStage"
        Write-Output "RUN PLAN STAGED $planStage"
    }

    "COMMISSION" {
        $root = Assert-ExistingPrivateRoot $OutputRoot
        Set-PrivateTemp $root
        if ($Identity) {
            foreach ($required in @("RunPlan", "InputManifest", "EvidenceCommit")) {
                if (-not (Get-Variable -Name $required -ValueOnly)) {
                    throw "-$required is mandatory for COMMISSION -Identity"
                }
            }
            $syntheticReceipt = Join-Path $root "commission\synthetic\receipt.json"
            if (-not (Test-Path -LiteralPath $syntheticReceipt -PathType Leaf)) {
                throw "Synthetic COMMISSION must complete before the real identity control"
            }
            $ready = Assert-ReadyForRealArm $root $RunPlan $InputManifest $EvidenceCommit
            Assert-SyntheticCommission $root $ready.prepare
            $entry = $ready.plan.identity
            $receipt = Invoke-RealArm $root $entry $ready $RunPlan $InputManifest (
                $EvidenceCommit
            ) -IdentityArm
            Write-Output "IDENTITY COMMISSIONED $receipt"
            break
        }

        $preparePath = Join-Path $root "prepare.json"
        $prepare = Get-Content -LiteralPath $preparePath -Raw | ConvertFrom-Json
        [void](Invoke-ToolAudit $prepare.source_commit)
        Assert-PreparedBinaries $prepare
        $beforeTrees = Assert-PreparedTrees $prepare

        $commissionRoot = Join-Path $root "commission\synthetic"
        if (Test-Path -LiteralPath $commissionRoot) {
            throw "Synthetic commission output already exists; duplicate run refused"
        }
        $lock = New-ArmLock $root "commission-synthetic"
        try {
            [void][IO.Directory]::CreateDirectory($commissionRoot)
            [void][IO.Directory]::CreateDirectory((Join-Path $commissionRoot "logs"))
            $operations = @()
            $operations += Invoke-Logged $Python @(
                "-B", $Checker, "commission"
            ) (Join-Path $commissionRoot "logs\checker-commission.log")
            $operations += Invoke-Logged $Python @(
                "-B", $ExternalComparator, "commission"
            ) (Join-Path $commissionRoot "logs\external-q1-commission.log")

            # Run the repository's complete producer/injector commissioning
            # against a private Git checkout pinned to SourceCommit. This
            # avoids producer_tests.py's HEAD archive ever depending on the
            # operator's current branch or dirty worktree.
            $producerRepo = Join-Path $commissionRoot "producer-repo"
            $producerWork = Join-Path $commissionRoot "producer-work"
            $operations += Invoke-Logged "git" @(
                "clone", "--local", "--no-checkout", $Repo, $producerRepo
            ) (Join-Path $commissionRoot "logs\producer-repo-clone.log")
            $operations += Invoke-Logged "git" @(
                "-C", $producerRepo, "checkout", "--detach", [string]$prepare.source_commit
            ) (Join-Path $commissionRoot "logs\producer-repo-checkout.log")
            $operations += Invoke-Logged $Python @(
                "-B", $ProducerTests,
                "--repo", $producerRepo,
                "--work", $producerWork
            ) (Join-Path $commissionRoot "logs\producer-tests.log")

            # PREPARE performed the one successful injection.  Re-injection of
            # that private snapshot must now refuse without changing it.
            $instrumentedBefore = Get-TreeAudit $prepare.snapshots.instrumented.path
            $operations += Invoke-Logged $Python @(
                "-B", $Injector, [string]$prepare.snapshots.instrumented.path,
                "--hook", $TraceSource
            ) (Join-Path $commissionRoot "logs\injector-reinjection-refusal.log") -ExpectFailure
            $instrumentedAfter = Get-TreeAudit $prepare.snapshots.instrumented.path
            Assert-TreeEqual $instrumentedBefore $instrumentedAfter "injector refusal"

            $fixtureTrace = Join-Path $commissionRoot "fixture-trace"
            $fixtureBinary = [string]$prepare.binaries.fixture.path
            $operations += Invoke-Logged $fixtureBinary @(
                "commission", $fixtureTrace
            ) (Join-Path $commissionRoot "logs\fixture-commission.log")
            $fixtureAudit = Join-Path $commissionRoot "fixture-audit.json"
            $operations += Invoke-Logged $Python @(
                "-B", $ManifestTool, "fixture-audit",
                "--trace-dir", $fixtureTrace,
                "--expected", "21",
                "--output", $fixtureAudit
            ) (Join-Path $commissionRoot "logs\fixture-audit.log")
            $operations += Invoke-Logged $fixtureBinary @(
                "commission", $fixtureTrace
            ) (Join-Path $commissionRoot "logs\fixture-duplicate-refusal.log") -ExpectFailure

            Remove-Item Env:STREHL_M8_V2_TRACE_DIR -ErrorAction SilentlyContinue
            $gateSentinel = Join-Path $commissionRoot "gate-off-sentinel"
            $operations += Invoke-Logged $fixtureBinary @(
                "gate-off", $gateSentinel
            ) (Join-Path $commissionRoot "logs\fixture-gate-off.log")
            if (Test-Path -LiteralPath $gateSentinel) {
                throw "Tracing-off producer touched its sentinel"
            }

            $runnerGate = Join-Path $commissionRoot "runner-gate.json"
            $operations += Invoke-Logged $Python @(
                "-B", $ManifestTool, "commission-runner-gate",
                "--output", $runnerGate
            ) (Join-Path $commissionRoot "logs\runner-gate.log")
            $renderLogCommission = Invoke-RenderLogCommission (
                Join-Path $commissionRoot "render-log-plants"
            )

            # Commission the runner's own retained create-new lock: a second
            # live opener and a later duplicate invocation must both refuse.
            $lockPlant = New-ArmLock $root "runner-lock-plant"
            try {
                $concurrentRefused = $false
                try {
                    $unexpected = New-ArmLock $root "runner-lock-plant"
                    $unexpected.stream.Dispose()
                }
                catch [IO.IOException] {
                    $concurrentRefused = $true
                }
                if (-not $concurrentRefused) {
                    throw "Runner concurrent lock plant was accepted"
                }
            }
            finally {
                $lockPlant.stream.Dispose()
            }
            $duplicateRefused = $false
            try {
                $unexpected = New-ArmLock $root "runner-lock-plant"
                $unexpected.stream.Dispose()
            }
            catch [IO.IOException] {
                $duplicateRefused = $true
            }
            if (-not $duplicateRefused) {
                throw "Runner retained duplicate lock plant was accepted"
            }

            $raceTrace = Join-Path $commissionRoot "race-trace"
            $raceArguments = @("race", $raceTrace)
            $race1Command = New-CommandRecord $fixtureBinary $raceArguments (
                Join-Path $commissionRoot "logs\race-1.log.command.json"
            )
            $race2Command = New-CommandRecord $fixtureBinary $raceArguments (
                Join-Path $commissionRoot "logs\race-2.log.command.json"
            )
            $race1 = Start-CapturedProcess $fixtureBinary $raceArguments
            $race2 = Start-CapturedProcess $fixtureBinary $raceArguments
            $race1.process.WaitForExit()
            $race2.process.WaitForExit()
            $race1Text = $race1.stdout.Result + $race1.stderr.Result
            $race2Text = $race2.stdout.Result + $race2.stderr.Result
            $race1Log = Join-Path $commissionRoot "logs\race-1.log"
            $race2Log = Join-Path $commissionRoot "logs\race-2.log"
            Write-AtomicText $race1Log $race1Text
            Write-AtomicText $race2Log $race2Text
            $codes = @($race1.process.ExitCode, $race2.process.ExitCode)
            if (@($codes | Where-Object { $_ -eq 0 }).Count -ne 1 -or
                @($codes | Where-Object { $_ -eq 1 }).Count -ne 1) {
                throw "Concurrent producer plant was not one-winner/one-refusal: $codes"
            }
            if (($race1Text + $race2Text) -notmatch "duplicate M8-v2") {
                throw "Concurrent producer loser did not report a duplicate refusal"
            }
            $operations += [ordered]@{
                file = $fixtureBinary
                arguments = $raceArguments
                exit_code = $race1.process.ExitCode
                command = $race1Command
                log = Get-HashRecord $race1Log
            }
            $operations += [ordered]@{
                file = $fixtureBinary
                arguments = $raceArguments
                exit_code = $race2.process.ExitCode
                command = $race2Command
                log = Get-HashRecord $race2Log
            }
            $raceAudit = Join-Path $commissionRoot "race-audit.json"
            $operations += Invoke-Logged $Python @(
                "-B", $ManifestTool, "fixture-audit",
                "--trace-dir", $raceTrace,
                "--expected", "1",
                "--output", $raceAudit
            ) (Join-Path $commissionRoot "logs\race-audit.log")

            $afterTrees = Assert-PreparedTrees $prepare
            Assert-TreeEqual $beforeTrees.uninstrumented $afterTrees.uninstrumented (
                "synthetic commission uninstrumented"
            )
            Assert-TreeEqual $beforeTrees.instrumented $afterTrees.instrumented (
                "synthetic commission instrumented"
            )
            $commissionFiles = @(
                (Get-HashRecord $fixtureAudit),
                (Get-HashRecord $runnerGate),
                (Get-HashRecord $raceAudit),
                (Get-HashRecord $lockPlant.path),
                (Get-HashRecord $lock.path)
            )
            $commissionFiles += @($renderLogCommission.files)
            $receiptPath = Join-Path $commissionRoot "receipt.json"
            $receipt = [ordered]@{
                schema = "strehl-m8-v2-synthetic-commission"
                version = 1
                source_commit = $prepare.source_commit
                prepare_receipt = Get-HashRecord $preparePath
                checker = "COMMISSIONED"
                producer_fixture = "COMMISSIONED"
                injector = "SUCCESS_IN_PREPARE_AND_REINJECTION_REFUSED"
                duplicate_state = "REFUSED"
                concurrent_state = "ONE_WINNER_ONE_REFUSAL"
                external_q1 = "COMMISSIONED"
                crop_log_parser = $renderLogCommission
                operations = @($operations)
                source_trees = $afterTrees
                files = $commissionFiles
            }
            Write-AtomicObject $receipt $receiptPath
            Write-Output "SYNTHETIC COMMISSIONED $receiptPath"
        }
        finally {
            if ($null -ne $lock -and $null -ne $lock.stream) {
                $lock.stream.Dispose()
            }
        }
    }

    "FULL" {
        $root = Assert-ExistingPrivateRoot $OutputRoot
        Set-PrivateTemp $root
        foreach ($required in @(
            "RunPlan",
            "InputManifest",
            "EvidenceCommit",
            "Case",
            "ArmMode"
        )) {
            if (-not (Get-Variable -Name $required -ValueOnly)) {
                throw "-$required is mandatory for FULL"
            }
        }
        foreach ($commissioned in @(
            (Join-Path $root "commission\synthetic\receipt.json"),
            (Join-Path $root "arms\identity-crop\receipt.json")
        )) {
            if (-not (Test-Path -LiteralPath $commissioned -PathType Leaf)) {
                throw "All commissioning must precede FULL: missing $commissioned"
            }
        }
        Assert-LaterExposureAllowed $root $Case
        $ready = Assert-ReadyForRealArm $root $RunPlan $InputManifest $EvidenceCommit
        Assert-SyntheticCommission $root $ready.prepare
        [void](Invoke-Json @(
            "verify-arm",
            "--receipt", (Join-Path $root "arms\identity-crop\receipt.json")
        ))
        $entry = Get-ArmEntry $ready.plan $Case $ArmMode
        $receipt = Invoke-RealArm $root $entry $ready $RunPlan $InputManifest (
            $EvidenceCommit
        )
        Write-Output "FULL ARM COMPLETE $receipt"
        if ($Case -eq "flat-1s") {
            Write-Output (
                "Do not request flat-2p5s/flat-6s until both flat-1s receipts " +
                "have been independently verified and the operator has read the Crop stopping result."
            )
        }
    }

    "VERIFY" {
        $root = Assert-ExistingPrivateRoot $OutputRoot
        Set-PrivateTemp $root
        foreach ($required in @(
            "RunPlan",
            "InputManifest",
            "EvidenceCommit",
            "ArmReceipt"
        )) {
            if (-not (Get-Variable -Name $required -ValueOnly)) {
                throw "-$required is mandatory for VERIFY"
            }
        }
        $ready = Assert-ReadyForRealArm $root $RunPlan $InputManifest $EvidenceCommit
        $receipt = Get-Content -LiteralPath $ArmReceipt -Raw | ConvertFrom-Json
        if ($receipt.evidence_commit -ne $EvidenceCommit) {
            throw "Arm receipt evidence commit differs from -EvidenceCommit"
        }
        $verified = Invoke-Json @("verify-arm", "--receipt", $ArmReceipt)
        $verificationRoot = Join-Path $root "verification-logs"
        [void][IO.Directory]::CreateDirectory($verificationRoot)
        $armLeaf = Split-Path -Leaf (Split-Path -Parent (Get-FullPath $ArmReceipt))
        $checkerLog = Join-Path $verificationRoot "$armLeaf-checker.log"
        if (-not (Test-PathWithin $checkerLog $verificationRoot)) {
            throw "VERIFY log path escapes its private verification directory"
        }
        if (Test-Path -LiteralPath $checkerLog) {
            throw "VERIFY is one-shot and will not overwrite its prior log: $checkerLog"
        }
        [void](Invoke-Logged $Python @(
            "-B", $Checker, "verify", "--result", [string]$receipt.result.path
        ) $checkerLog)
        [void](Invoke-Json @("verify-input", "--input", $InputManifest))
        [void](Invoke-ToolAudit $ready.prepare.source_commit)
        [void](Invoke-Json @(
            "committed-files",
            "--repo", $Repo,
            "--commit", $EvidenceCommit,
            "--path", $RunPlan,
            "--path", $InputManifest
        ))
        [void](Assert-PreparedTrees $ready.prepare)
        $verified | ConvertTo-Json -Depth 20
    }
}
