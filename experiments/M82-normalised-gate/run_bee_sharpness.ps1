$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Python = (Get-Command python).Source
$Stacks = @("bee-1", "bee-2", "bee-3")
$Source = Join-Path $Here "m82lib.py"
$SourceHash = (Get-FileHash -Algorithm SHA256 $Source).Hash.ToLowerInvariant()
$Confirm = Get-Content -Raw (Join-Path $Here "bee-confirm-results.json") | ConvertFrom-Json
if (-not $Confirm.all_confirmed) { throw "bee confirmations are not all within tolerance" }
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

foreach ($Stack in $Stacks) {
    $Started = [DateTime]::UtcNow.ToString("o")
    $Saved = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Run = @(
        & $Python -X faulthandler (Join-Path $Here "sharpness.py") `
            --stack $Stack `
            --confirm-results "bee-confirm-results.json" `
            --output-prefix "bee-sharpness" 2>&1 |
            ForEach-Object { $_.ToString() }
    )
    $Code = $LASTEXITCODE
    $ErrorActionPreference = $Saved
    $Finished = [DateTime]::UtcNow.ToString("o")
    $Lines = @(
        "python=$Python",
        "STACK=$Stack",
        "DIRECTORY=$Stack-cpl",
        "m82lib_sha256=$SourceHash",
        "started_utc=$Started"
    ) + $Run + @("exit=$Code", "finished_utc=$Finished")
    $Path = Join-Path $Here "bee-sharpness-$Stack.log"
    [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
    $Lines | ForEach-Object { Write-Host $_ }
    if ($Code -ne 0) { throw "$Stack sharpness exited $Code" }
    if ((Get-FileHash -Algorithm SHA256 $Source).Hash.ToLowerInvariant() -ne $SourceHash) {
        throw "m82lib.py changed during sharpness run"
    }
}
