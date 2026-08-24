$ErrorActionPreference = "Stop"

$Here = $PSScriptRoot
$Python = (Get-Command python).Source
$Stacks = @("bee-1", "bee-2", "bee-3")
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

Push-Location (Resolve-Path (Join-Path $Here "..\.."))
try {
    $MethodPaths = @(
        "experiments\M70-through-focus-spectrum\src\s04_through_focus.py",
        "experiments\M70-through-focus-spectrum\src\s05_analyse.py",
        "experiments\M70-through-focus-spectrum\src\s10_architecture.py",
        "experiments\M70-through-focus-spectrum\src\m70lib.py",
        "crates\strehl-core\src\profile.rs"
    )
    & git diff --quiet d882b0c HEAD -- $MethodPaths
    if ($LASTEXITCODE -ne 0) { throw "M70 method differs from d882b0c" }
    & git diff --quiet -- $MethodPaths
    if ($LASTEXITCODE -ne 0) { throw "M70 method has uncommitted changes" }
} finally {
    Pop-Location
}

foreach ($Stack in $Stacks) {
    $Started = [DateTime]::UtcNow.ToString("o")
    $Saved = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Run = @(
        & $Python -X faulthandler (Join-Path $Here "bee_physics_measure.py") --stack $Stack 2>&1 |
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
    $Path = Join-Path $Here "bee-physics-$Stack.log"
    [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
    $Lines | ForEach-Object { Write-Host $_ }
    if ($Code -ne 0) { throw "$Stack physics measurement exited $Code" }
}
