$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Binary = Join-Path $Here "target-unit\release\strehl.exe"
$Gates = @("0", "0.25", "0.5", "1", "2", "4", "8", "16", "24", "32", "40", "48", "64", "96", "128")
$Stacks = @("wrapped-text-1", "wrapped-text-2", "109MSDCF", "coffee-bean", "foam", "bee-1")

if (-not (Test-Path $Binary)) {
    throw "private evidence binary does not exist: $Binary"
}
Push-Location $Repo
try {
    & git diff --quiet -- crates/strehl-core/src crates/strehl-cli/src/main.rs crates/strehl-cli/src/merge_cmd.rs
    if ($LASTEXITCODE -ne 0) {
        throw "owned/runtime Rust source differs from HEAD"
    }
    $Hash = (Get-FileHash -Algorithm SHA256 $Binary).Hash.ToLowerInvariant()
    $Bytes = (Get-Item $Binary).Length
    $BinaryRecordPath = Join-Path $Here "unit-binary.json"
    if (Test-Path $BinaryRecordPath) {
        $BinaryRecord = Get-Content -Raw $BinaryRecordPath | ConvertFrom-Json
        if ($BinaryRecord.sha256 -ne $Hash) {
            throw "binary hash differs from the frozen binary record"
        }
        $Commit = $BinaryRecord.commit
    } else {
        $Commit = (& git rev-parse HEAD).Trim()
        @{
            commit = $Commit
            binary = $Binary
            sha256 = $Hash
            bytes = $Bytes
            gates = $Gates
        } | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 $BinaryRecordPath
    }

    foreach ($Stack in $Stacks) {
        $InputDir = "D:\personal\macro\$Stack"
        $Invocation = "& '$Binary' stack '$InputDir' --gate $($Gates -join ' ')"
        $Started = [DateTime]::UtcNow.ToString("o")
        $SavedErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $Run = @(& $Binary stack $InputDir --gate $Gates 2>&1 | ForEach-Object { $_.ToString() })
        $Code = $LASTEXITCODE
        $ErrorActionPreference = $SavedErrorAction
        $Finished = [DateTime]::UtcNow.ToString("o")
        $Lines = @(
            "commit=$Commit",
            "binary=$Binary",
            "sha256=$Hash",
            "STACK=$Stack",
            "INVOCATION=$Invocation",
            "started_utc=$Started"
        ) + $Run + @("exit=$Code", "finished_utc=$Finished")
        $Path = Join-Path $Here "unit-ladder-$Stack.log"
        [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
        $Lines | ForEach-Object { Write-Host $_ }
        if ($Code -ne 0) {
            throw "$Stack ladder exited $Code"
        }
    }
} finally {
    Pop-Location
}
