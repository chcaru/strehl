$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Python = (Get-Command python).Source
$Stacks = @("wrapped-text-1", "wrapped-text-2", "109MSDCF", "coffee-bean", "foam", "bee-1")
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

foreach ($Stack in $Stacks) {
    $Started = [DateTime]::UtcNow.ToString("o")
    $Saved = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Run = @(
        & $Python -X faulthandler (Join-Path $Here "sharpness.py") --stack $Stack 2>&1 |
            ForEach-Object { $_.ToString() }
    )
    $Code = $LASTEXITCODE
    $ErrorActionPreference = $Saved
    $Finished = [DateTime]::UtcNow.ToString("o")
    $Lines = @(
        "python=$Python",
        "STACK=$Stack",
        "started_utc=$Started"
    ) + $Run + @("exit=$Code", "finished_utc=$Finished")
    $Path = Join-Path $Here "sharpness-$Stack.log"
    [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
    $Lines | ForEach-Object { Write-Host $_ }
    if ($Code -ne 0) { throw "$Stack sharpness exited $Code" }
}
