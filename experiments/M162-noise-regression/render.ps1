[CmdletBinding()]
param(
    [ValidateSet("current", "historical", "all")]
    [string]$Stage = "current",
    [string]$OutputRoot = "C:\dev\strehl-out\M162-noise-regression",
    [string]$Source = "D:\personal\macro\coffee-bean",
    [switch]$ValidateOnly,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CurrentExe = "C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe"
$CurrentExeHash = "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
$CurrentCommit = "6af834dac08d6605aee7ea3ad75809fdf6313770"
$HistoricalExe = "C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe"
$HistoricalExeHash = "CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6"
$HistoricalCommit = "b9b6921edc7ecec95443509b0778b4ed48404871"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-TextSha256([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash)
}

function Assert-FileHash([string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "required file is missing: $Path"
    }
    $actual = Get-Sha256 $Path
    if ($actual -ne $Expected.ToUpperInvariant()) {
        throw "SHA-256 mismatch for $Path`nexpected $Expected`nactual   $actual"
    }
}

function Clear-StrehlEnvironment {
    Get-ChildItem Env: |
        Where-Object { $_.Name -like "STREHL_*" } |
        ForEach-Object {
            Remove-Item "Env:\$($_.Name)" -ErrorAction SilentlyContinue
        }
}

function Get-SourceSnapshot([string]$Root) {
    return @(
        Get-ChildItem -LiteralPath $Root -File -Filter *.ARW |
            Sort-Object Name |
            ForEach-Object {
                [pscustomobject]@{
                    name = $_.Name
                    bytes = $_.Length
                    last_write_utc = $_.LastWriteTimeUtc.ToString("o")
                }
            }
    )
}

function Compare-SourceSnapshot($Before, $After) {
    $a = $Before | ConvertTo-Json -Depth 4 -Compress
    $b = $After | ConvertTo-Json -Depth 4 -Compress
    if ($a -ne $b) {
        throw "source capture metadata changed during the run; no result is admissible"
    }
}

function Write-SourceManifest([string]$Root, [string]$Destination) {
    $files = @(Get-ChildItem -LiteralPath $Root -File -Filter *.ARW | Sort-Object Name)
    if ($files.Count -eq 0) {
        throw "no ARW files found under $Root"
    }
    $rows = @()
    foreach ($file in $files) {
        $rows += [ordered]@{
            name = $file.Name
            bytes = $file.Length
            sha256 = Get-Sha256 $file.FullName
        }
    }
    $record = [ordered]@{
        schema = 1
        source = $Root
        policy = "read-only; M162 writes nothing under the capture root"
        frame_count = $rows.Count
        files = $rows
    }
    $record | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $Destination -Encoding utf8
}

function Get-ContractHash(
    [string]$Arm,
    [string]$ExeHash,
    [string]$Commit,
    [string]$SourceManifestHash,
    [string]$WarpmapHash,
    [string[]]$Arguments,
    [hashtable]$Environment
) {
    $lines = @(
        "schema=1",
        "arm=$Arm",
        "exe_sha256=$ExeHash",
        "commit=$Commit",
        "source_manifest_sha256=$SourceManifestHash",
        "warpmap_sha256=$WarpmapHash"
    )
    foreach ($argument in $Arguments) {
        $lines += "arg=$argument"
    }
    foreach ($key in @($Environment.Keys | Sort-Object)) {
        $lines += "env=$key=$($Environment[$key])"
    }
    return Get-TextSha256 ($lines -join "`n")
}

function Ensure-Warpmap(
    [string]$Name,
    [string]$Exe,
    [string]$ExeHash,
    [string]$Commit,
    [string]$MapPath,
    [string]$CachePath,
    [string]$SourceManifestHash
) {
    $manifestPath = "$MapPath.manifest.json"
    $logPath = "$MapPath.log"
    $contract = Get-TextSha256 (
        @(
            "schema=1",
            "name=$Name",
            "exe_sha256=$ExeHash",
            "commit=$Commit",
            "source_manifest_sha256=$SourceManifestHash",
            "arg=align",
            "arg=$Source",
            "arg=--out",
            "arg=$MapPath"
        ) -join "`n"
    )

    if (-not $Force -and (Test-Path -LiteralPath $MapPath) -and
        (Test-Path -LiteralPath $manifestPath)) {
        $old = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $actual = Get-Sha256 $MapPath
        if ($old.contract_sha256 -eq $contract -and
            $old.warpmap_sha256 -eq $actual -and
            $old.exit_code -eq 0) {
            Write-Host "warpmap ${Name}: verified resume $actual"
            return $actual
        }
        throw "stale or mismatched warpmap record at $MapPath; use -Force to replace it"
    }
    if ((Test-Path -LiteralPath $MapPath) -or (Test-Path -LiteralPath $manifestPath)) {
        if (-not $Force) {
            throw "partial warpmap state at $MapPath; use -Force to replace it"
        }
        Remove-Item -LiteralPath $MapPath, $manifestPath, $logPath -Force -ErrorAction SilentlyContinue
    }

    New-Item -ItemType Directory -Force -Path (Split-Path $MapPath -Parent), $CachePath |
        Out-Null
    Clear-StrehlEnvironment
    $env:STREHL_CACHE_DIR = $CachePath
    $arguments = @("align", $Source, "--out", $MapPath)
    $started = [DateTime]::UtcNow
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $stdxx = & $Exe @arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    $stopwatch.Stop()
    ($stdxx | ForEach-Object { "$_" }) -join "`r`n" |
        Set-Content -LiteralPath $logPath -Encoding utf8
    if ($code -ne 0 -or -not (Test-Path -LiteralPath $MapPath)) {
        throw "alignment failed for $Name with exit $code; see $logPath"
    }

    $mapHash = Get-Sha256 $MapPath
    [ordered]@{
        schema = 1
        name = $Name
        contract_sha256 = $contract
        executable = $Exe
        executable_sha256 = $ExeHash
        commit = $Commit
        source = $Source
        source_manifest_sha256 = $SourceManifestHash
        arguments = $arguments
        environment = [ordered]@{
            STREHL_CACHE_DIR = $CachePath
        }
        cleared_environment = "all inherited STREHL_*"
        started_utc = $started.ToString("o")
        elapsed_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        exit_code = $code
        warpmap = $MapPath
        warpmap_sha256 = $mapHash
        log = $logPath
    } | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $manifestPath -Encoding utf8
    Write-Host "warpmap ${Name}: wrote $mapHash"
    return $mapHash
}

function Invoke-Arm(
    [string]$Arm,
    [string]$Exe,
    [string]$ExeHash,
    [string]$Commit,
    [string]$Warpmap,
    [string]$WarpmapHash,
    [string]$CachePath,
    [string]$SourceManifestHash,
    [string[]]$ExtraArguments,
    [hashtable]$ExtraEnvironment,
    [string]$Interpretation
) {
    $renderDir = Join-Path $OutputRoot "renders"
    $manifestDir = Join-Path $OutputRoot "manifests"
    $logDir = Join-Path $OutputRoot "logs"
    New-Item -ItemType Directory -Force -Path $renderDir, $manifestDir, $logDir, $CachePath |
        Out-Null

    $target = Join-Path $renderDir "$Arm.tiff"
    $manifestPath = Join-Path $manifestDir "$Arm.json"
    $logPath = Join-Path $logDir "$Arm.log"
    $arguments = @("stack", $Source, "-o", $target) + $ExtraArguments
    $environment = @{
        STREHL_WARPMAP = $Warpmap
        STREHL_CACHE_DIR = $CachePath
    }
    foreach ($key in $ExtraEnvironment.Keys) {
        $environment[$key] = [string]$ExtraEnvironment[$key]
    }
    $contract = Get-ContractHash $Arm $ExeHash $Commit $SourceManifestHash `
        $WarpmapHash $arguments $environment

    if (-not $Force -and (Test-Path -LiteralPath $target) -and
        (Test-Path -LiteralPath $manifestPath)) {
        $old = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $actual = Get-Sha256 $target
        if ($old.contract_sha256 -eq $contract -and
            $old.output_sha256 -eq $actual -and
            $old.exit_code -eq 0) {
            Write-Host "${Arm}: verified resume $actual"
            return
        }
        throw "stale or mismatched arm record for $Arm; use -Force to replace it"
    }
    if ((Test-Path -LiteralPath $target) -or
        (Test-Path -LiteralPath $manifestPath) -or
        (Test-Path -LiteralPath $logPath)) {
        if (-not $Force) {
            throw "partial arm state for $Arm; use -Force to replace it"
        }
        Remove-Item -LiteralPath $target, $manifestPath, $logPath -Force -ErrorAction SilentlyContinue
    }

    Clear-StrehlEnvironment
    foreach ($key in $environment.Keys) {
        Set-Item "Env:\$key" $environment[$key]
    }
    $started = [DateTime]::UtcNow
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $stdxx = & $Exe @arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    $stopwatch.Stop()
    $text = ($stdxx | ForEach-Object { "$_" }) -join "`r`n"
    $text | Set-Content -LiteralPath $logPath -Encoding utf8

    if ($code -ne 0 -or -not (Test-Path -LiteralPath $target)) {
        [ordered]@{
            schema = 1
            arm = $Arm
            contract_sha256 = $contract
            exit_code = $code
            output_exists = Test-Path -LiteralPath $target
            log = $logPath
        } | ConvertTo-Json -Depth 4 |
            Set-Content -LiteralPath $manifestPath -Encoding utf8
        throw "render failed for $Arm with exit $code; see $logPath"
    }

    $outputHash = Get-Sha256 $target
    [ordered]@{
        schema = 1
        arm = $Arm
        interpretation = $Interpretation
        contract_sha256 = $contract
        executable = $Exe
        executable_sha256 = $ExeHash
        commit = $Commit
        source = $Source
        source_manifest_sha256 = $SourceManifestHash
        arguments = $arguments
        environment = [ordered]@{
            cleared = "all inherited STREHL_*"
            set = $environment
        }
        warpmap = $Warpmap
        warpmap_sha256 = $WarpmapHash
        started_utc = $started.ToString("o")
        elapsed_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        exit_code = $code
        output = $target
        output_bytes = (Get-Item -LiteralPath $target).Length
        output_sha256 = $outputHash
        log = $logPath
    } | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $manifestPath -Encoding utf8
    Write-Host "${Arm}: wrote $outputHash in $([math]::Round($stopwatch.Elapsed.TotalSeconds, 1)) s"
}

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "source capture is missing: $Source"
}

if ($ValidateOnly) {
    $frames = @(Get-ChildItem -LiteralPath $Source -File -Filter *.ARW)
    if ($frames.Count -eq 0) {
        throw "no ARW files found under $Source"
    }
    if ($Stage -in @("current", "all")) {
        Assert-FileHash $CurrentExe $CurrentExeHash
    }
    if ($Stage -in @("historical", "all")) {
        Assert-FileHash $HistoricalExe $HistoricalExeHash
    }
    Write-Host "validation only: $($frames.Count) source frames; binary hashes match; no files written"
    return
}

$ambient = @{}
Get-ChildItem Env: |
    Where-Object { $_.Name -like "STREHL_*" } |
    ForEach-Object { $ambient[$_.Name] = $_.Value }

$before = Get-SourceSnapshot $Source
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$sourceManifest = Join-Path $OutputRoot "source-manifest.json"

try {
    Write-SourceManifest $Source $sourceManifest
    $sourceManifestHash = Get-Sha256 $sourceManifest

    if ($Stage -in @("current", "all")) {
        Assert-FileHash $CurrentExe $CurrentExeHash
        $currentMap = Join-Path $OutputRoot "warpmaps\deliver-v6.warpmap.txt"
        $currentCache = Join-Path $OutputRoot "cache\deliver-v6"
        $currentMapHash = Ensure-Warpmap "deliver-v6" $CurrentExe $CurrentExeHash `
            $CurrentCommit $currentMap $currentCache $sourceManifestHash

        $arms = @(
            @{
                name = "v6-g2-full"
                args = @("--srgb")
                env = @{}
                note = "exact DELIVER-V6 flags; compiled pyramid gate 2.0 and full-resolution gather"
            },
            @{
                name = "v6-g4p5-full"
                args = @("--srgb", "--pyramid-gate", "4.5")
                env = @{}
                note = "gate-only reversion at full-resolution gather"
            },
            @{
                name = "v6-g2-plane"
                args = @("--srgb")
                env = @{ STREHL_FULLRES_GATHER = "0" }
                note = "gather-only reversion at compiled gate 2.0"
            },
            @{
                name = "v6-g4p5-plane"
                args = @("--srgb", "--pyramid-gate", "4.5")
                env = @{ STREHL_FULLRES_GATHER = "0" }
                note = "SHIP-V2-like gate and plane gather in the current binary"
            },
            @{
                name = "v6-g2-full-white-floor"
                args = @("--srgb")
                env = @{ STREHL_GATE_FLOOR = "white" }
                note = "measured per-frame floor reverted to the white-noise constant"
            },
            @{
                name = "v6-g2-full-ca-off"
                args = @("--srgb")
                env = @{ STREHL_FIX_CA = "0" }
                note = "lateral-CA correction disabled"
            }
        )
        foreach ($arm in $arms) {
            Invoke-Arm $arm.name $CurrentExe $CurrentExeHash $CurrentCommit `
                $currentMap $currentMapHash $currentCache $sourceManifestHash `
                $arm.args $arm.env $arm.note
        }
    }

    if ($Stage -in @("historical", "all")) {
        Assert-FileHash $HistoricalExe $HistoricalExeHash
        $historicalMap = Join-Path $OutputRoot "warpmaps\b9b-ship-v2.warpmap.txt"
        $historicalCache = Join-Path $OutputRoot "cache\b9b-ship-v2"
        $historicalMapHash = Ensure-Warpmap "b9b-ship-v2" $HistoricalExe `
            $HistoricalExeHash $HistoricalCommit $historicalMap $historicalCache `
            $sourceManifestHash
        Invoke-Arm "b9b-ship-v2-reconstruction" $HistoricalExe $HistoricalExeHash `
            $HistoricalCommit $historicalMap $historicalMapHash $historicalCache `
            $sourceManifestHash `
            @("--merge", "pyramid", "--pyramid-gate", "4.5", "--srgb", "--auto-exposure") `
            @{} `
            "nearest retained SHIP-V2 reconstruction; not the archived comparator producer"
    }
}
finally {
    Clear-StrehlEnvironment
    foreach ($key in $ambient.Keys) {
        Set-Item "Env:\$key" $ambient[$key]
    }
    $after = Get-SourceSnapshot $Source
    Compare-SourceSnapshot $before $after
}

Write-Host "source capture metadata unchanged; all writes stayed outside $Source"
