# One binary, one instant, one variable.
#
# ORCH: "two pins built hours apart have already been mistaken for an A/B here
# twice." So this script does not invoke cargo between the arms -- it runs the
# already-built test executable directly, and it HASHES THE RENDERING BINARY
# BEFORE AND AFTER EACH ARM. A shared tree with a dozen lanes in it can rebuild
# strehl.exe underneath a measurement; if that happens the two arms are two
# binaries and the comparison is void. The script refuses rather than reports.

$ErrorActionPreference = "Stop"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$cli  = Join-Path $root "target\release\strehl.exe"
$test = (Get-ChildItem (Join-Path $root "target\release\deps\byte_freeze-*.exe") |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }

Write-Host "cli  : $cli"
Write-Host "test : $test"
$sha0 = CliSha
Write-Host "strehl.exe sha256 before: $sha0"
Write-Host ""

$results = @{}
foreach ($arm in @("0", "1")) {
    $env:STREHL_PYRAMID_SIGNIFICANCE = $arm
    Write-Host "=== arm STREHL_PYRAMID_SIGNIFICANCE=$arm ==="
    # A native command writing to stderr is not an error, but `Stop` treats it
    # as one and would abort the second arm -- leaving a one-armed "A/B".
    $ErrorActionPreference = "Continue"
    $out = & $test --nocapture --test-threads 1 2>&1 | Out-String
    $ErrorActionPreference = "Stop"
    $before = CliSha
    if ($before -ne $sha0) {
        Write-Host "VOID: strehl.exe changed during arm $arm ($sha0 -> $before)"
        exit 2
    }
    # Both the HOLDS line and the MOVED banner carry a sha; take whichever the
    # run produced, per row.
    foreach ($row in @("coffee-bean-20-gate2-unaligned", "coffee-bean-20-gate2-sidecar")) {
        $sha = $null
        if ($out -match "freeze ``$row`` HOLDS: ([0-9A-F]{64})") { $sha = $Matches[1] }
        elseif ($out -match "BYTE-FREEZE MOVED: $row[\s\S]*?actual\s+sha256\s*:\s*([0-9A-F]{64})") { $sha = $Matches[1] }
        $results["$row|$arm"] = $sha
        Write-Host ("  {0,-32} -> {1}" -f $row, $sha)
    }
    Write-Host ""
}
Remove-Item Env:STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue

$sha1 = CliSha
if ($sha1 -ne $sha0) { Write-Host "VOID: strehl.exe moved across the run"; exit 2 }
Write-Host "strehl.exe sha256 after : $sha1  (unchanged -- arms are comparable)"
Write-Host ""

$live = $false
foreach ($row in @("coffee-bean-20-gate2-unaligned", "coffee-bean-20-gate2-sidecar")) {
    $a = $results["$row|0"]; $b = $results["$row|1"]
    if (-not $a -or -not $b) { Write-Host "$row : UNPARSED ($a / $b)"; continue }
    if ($a -eq $b) {
        Write-Host "$row : INERT -- the fix does not move this render"
    } else {
        Write-Host "$row : LIVE"
        Write-Host "    off: $a"
        Write-Host "    on : $b"
        $live = $true
    }
}
if (-not $live) { Write-Host ""; Write-Host "VERDICT: the fix is INERT on every frozen row." }
