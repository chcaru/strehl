# M97 bar D2b -- RED control. Removes the three is_refused skips, rebuilds,
# and asserts the refusal input FAILS (the pre-fix defect), then restores from
# the $env:TEMP copy and rebuilds. try/finally so a mid-run error cannot leave
# the shared working tree mutated.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "C:\dev\strehl-target-m97"
$env:PYTHONIOENCODING = "utf-8"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\d2"
$env:STREHL_CACHE_DIR = "$out\cache"
$env:STREHL_ALIGN = "1"
$env:STREHL_WARPMAP = "C:\dev\strehl-out\M97\warpmap-ruler-REFUSE.txt"
$repo = "C:\dev\blog\death-of-software\projects\strehl"

try {
    python C:\dev\strehl-out\M97\mutate_skips.py break
    if ($LASTEXITCODE -ne 0) { throw "mutation did not land -- aborting, control is invalid" }

    Push-Location $repo
    $b = cargo build --release -p strehl-cli --bin strehl 2>&1
    $bc = $LASTEXITCODE
    Pop-Location
    Write-Output "MUTATED_BUILD_EXIT=$bc"
    if ($bc -ne 0) {
        $b | Out-String | Select-String "error" | Select-Object -Last 5 | ForEach-Object { "    | " + $_.Line.Trim() }
        throw "mutated build failed to compile; cannot run the control"
    }

    $o = & $exe stack $dir --out "$out\red.tiff" --gate 4 2>&1
    $code = $LASTEXITCODE
    $o | Out-String | Set-Content -Encoding utf8 "$out\red.log"
    $len = if (Test-Path "$out\red.tiff") { (Get-Item "$out\red.tiff").Length } else { 0 }
    Write-Output "RED_EXIT=$code RED_BYTES=$len"
    $o | Out-String | Select-String "Error|refused|DROPPING" | Select-Object -Last 4 |
        ForEach-Object { "    | " + $_.Line.Trim() }
}
finally {
    Write-Output ""
    python C:\dev\strehl-out\M97\mutate_skips.py restore
    Write-Output "RESTORE_EXIT=$LASTEXITCODE"
    Push-Location $repo
    $b2 = cargo build --release -p strehl-cli --bin strehl 2>&1
    Write-Output "RESTORED_BUILD_EXIT=$LASTEXITCODE"
    Pop-Location
}
