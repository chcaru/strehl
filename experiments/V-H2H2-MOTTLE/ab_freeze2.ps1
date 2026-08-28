# One binary, one instant, one variable -- with a potency arm.
#
# ORCH: "two pins built hours apart have already been mistaken for an A/B here
# twice." So this script does not invoke cargo between the arms; it runs the
# already-built test executable directly and HASHES THE RENDERING BINARY BEFORE
# AND AFTER EACH ARM. A shared tree with a dozen lanes in it can rebuild
# strehl.exe underneath a measurement; if that happens the arms are two binaries
# and the comparison is void. This refuses rather than reports.
#
# The 1000x arm is the point of the whole script. Arms 0 and 1 alone cannot
# distinguish "the effect is real but below the output quantiser" from "the code
# is never reached", because both render byte-identical output. If 1000x also
# renders byte-identical output, the path is dead and no measurement of it means
# anything.
#
# Out-String defaults to the console width and WRAPS, which splits a 64-char
# sha across two lines and makes a row silently unparseable -- that read as a
# missing row in the first version of this script. -Width 4096 is load-bearing.

$ErrorActionPreference = "Stop"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$cli  = Join-Path $root "target\release\strehl.exe"
$test = (Get-ChildItem (Join-Path $root "target\release\deps\byte_freeze-*.exe") |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$rows = @("coffee-bean-20-gate2-unaligned", "coffee-bean-20-gate2-sidecar")
$arms = @("0", "1", "1000")

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }

Write-Host "cli  : $cli"
Write-Host "test : $test"
$sha0 = CliSha
Write-Host "strehl.exe sha256: $sha0"
Write-Host ""

$results = @{}
foreach ($arm in $arms) {
    $env:STREHL_PYRAMID_SIGNIFICANCE = $arm
    Write-Host "=== arm STREHL_PYRAMID_SIGNIFICANCE=$arm ==="
    $ErrorActionPreference = "Continue"
    $out = & $test --nocapture --test-threads 1 2>&1 | Out-String -Width 4096
    $ErrorActionPreference = "Stop"
    if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe changed during arm $arm"; exit 2 }
    foreach ($row in $rows) {
        $sha = $null
        if ($out -match "freeze ``$row`` HOLDS: ([0-9A-F]{64})") { $sha = $Matches[1] }
        elseif ($out -match "BYTE-FREEZE MOVED: $row[\s\S]*?actual\s+sha256\s*:\s*([0-9A-F]{64})") { $sha = $Matches[1] }
        $results["$row|$arm"] = $sha
        Write-Host ("  {0,-32} -> {1}" -f $row, $(if ($sha) { $sha } else { "UNPARSED" }))
    }
    Write-Host ""
}
Remove-Item Env:STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue
if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe moved across the run"; exit 2 }

# Partition: every row lands in exactly one bucket and the buckets sum to the
# census, so an unparsed row cannot read as an inert one (ORCH's rule).
$b = @{ LIVE = @(); INERT = @(); UNPARSED = @() }
foreach ($row in $rows) {
    $off = $results["$row|0"]; $on = $results["$row|1"]; $hot = $results["$row|1000"]
    if (-not $off -or -not $on -or -not $hot) { $b.UNPARSED += $row; continue }
    if ($off -eq $on -and $off -eq $hot) { $b.INERT += $row } else { $b.LIVE += $row }
    Write-Host ("{0}`n  off  : {1}`n  x1   : {2}  {3}`n  x1000: {4}  {5}" -f `
        $row, $off, $on, $(if ($on -eq $off) { "SAME" } else { "differs" }),
        $hot, $(if ($hot -eq $off) { "SAME" } else { "differs" }))
}
Write-Host ""
Write-Host ("PARTITION  live {0}  inert {1}  unparsed {2}  = {3} of {4} rows" -f `
    $b.LIVE.Count, $b.INERT.Count, $b.UNPARSED.Count,
    ($b.LIVE.Count + $b.INERT.Count + $b.UNPARSED.Count), $rows.Count)
if ($b.UNPARSED.Count) { Write-Host "UNPARSED rows are NOT passing rows: $($b.UNPARSED -join ', ')" }
