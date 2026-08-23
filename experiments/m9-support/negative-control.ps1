# M9 negative control for the regression test added in
# crates/strehl-core/src/focus.rs :: centre_tap_fraction_is_the_value_m9_measured
#
# Project rule: a test that has never been seen to fail is not evidence.
# This script deliberately regresses the shipped focus measure in two
# independent ways, proves the test goes red for each, then restores the file
# from a byte copy and bumps LastWriteTime so cargo does not silently skip the
# rebuild (Copy-Item preserves the source mtime).
#
# Never uses `git checkout --`.
#
#   pwsh -File experiments\m9-support\negative-control.ps1
#
$ErrorActionPreference = 'Stop'
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$root   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$target = Join-Path $root 'crates\strehl-core\src\focus.rs'
$backup = Join-Path $PSScriptRoot 'scratch\focus.rs.orig'
New-Item -ItemType Directory -Force -Path (Split-Path $backup) | Out-Null

function Invoke-Test {
    Push-Location $root
    try {
        $ErrorActionPreference = 'Continue'
        $text = (cargo test -p strehl-core focus::tests::centre 2>&1 | Out-String)
        return @{ Code = $LASTEXITCODE; Text = $text }
    } finally { Pop-Location }
}

function Restore-Target {
    Copy-Item -LiteralPath $backup -Destination $target -Force
    # Copy-Item preserves the SOURCE mtime, which is older than the regressed
    # file cargo last compiled. Without this bump cargo skips the rebuild.
    (Get-Item -LiteralPath $target).LastWriteTime = Get-Date
}

Copy-Item -LiteralPath $target -Destination $backup -Force
Write-Host "backed up focus.rs -> $backup"
if (-not (Get-Content -LiteralPath $backup -Raw).Contains('pub const INNER_RADIUS: usize = 1;')) {
    throw "refusing to run: focus.rs is not in its shipped state (INNER_RADIUS != 1)"
}

$cases = @(
    @{ Name = 'INNER_RADIUS 1 -> 2 (phi 1/18 -> 1/50)'
       From = 'pub const INNER_RADIUS: usize = 1;'
       To   = 'pub const INNER_RADIUS: usize = 2;' },
    @{ Name = 'OUTER_RADIUS 3 -> 5 (read extent 49 -> 121 taps)'
       From = 'pub const OUTER_RADIUS: usize = 3;'
       To   = 'pub const OUTER_RADIUS: usize = 5;' }
)

$allRed = $true
foreach ($c in $cases) {
    Restore-Target
    $src = Get-Content -LiteralPath $target -Raw
    if (-not $src.Contains($c.From)) { throw "anchor not found: $($c.From)" }
    Set-Content -LiteralPath $target -Value $src.Replace($c.From, $c.To) -NoNewline
    (Get-Item -LiteralPath $target).LastWriteTime = Get-Date

    $r = Invoke-Test
    if ($r.Code -eq 0) {
        Write-Host "NEGATIVE CONTROL FAILED (test stayed green): $($c.Name)" -ForegroundColor Red
        $allRed = $false
    } else {
        $line = ($r.Text -split "`n" | Select-String 'centre-tap|read extent|must sit clear' | Select-Object -First 1)
        Write-Host "red as required: $($c.Name)" -ForegroundColor Green
        Write-Host "    $($line -replace '^\s+','')"
    }
}

Restore-Target
$r = Invoke-Test
if ($r.Code -ne 0) { throw "restore failed: test is still red after restoring focus.rs" }
Write-Host "restored and green again" -ForegroundColor Green
Remove-Item -LiteralPath $backup -Force
Remove-Item -LiteralPath (Split-Path $backup) -Force -Recurse -ErrorAction SilentlyContinue

if (-not $allRed) { exit 1 }
Write-Host "`nNEGATIVE CONTROL PASSED: the test fires for both planted regressions."
