# P7 timing, alternating per AGENTS rule 16 so a warming disk or a busy machine
# cannot be mistaken for the cost of the feature. Medians are reported.

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$map = "D:\personal\macro\bee-3-cpl\warpmap.txt"
$tmp = "C:\dev\strehl-out\M97\timing.tif"
$data = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\data"

# Alternating, and the second pair runs in the opposite order.
$order = @("OFF", "ON", "ON", "OFF", "OFF", "ON")
$rows = @()
foreach ($mode in $order) {
    Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
    if ($mode -eq "OFF") { $env:STREHL_ALIGN = "0" } else { $env:STREHL_WARPMAP = $map }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $dir --gate 2 -o $tmp 2>&1 | Out-Null
    $rc = $LASTEXITCODE
    $sw.Stop()
    $rows += [pscustomobject]@{ mode = $mode; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2); rc = $rc }
    Write-Host ("  {0,-3} rc={1}  {2:N2} s" -f $mode, $rc, $sw.Elapsed.TotalSeconds)
}
Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue

foreach ($m in @("OFF", "ON")) {
    $v = @($rows | Where-Object { $_.mode -eq $m } | ForEach-Object { $_.seconds } | Sort-Object)
    # [int](3/2) is 2 in PowerShell -- [int] rounds half to EVEN, so the naive
    # index printed the max and called it the median. Measured, and it is why
    # the medians in the report are taken from the raw rows in the JSON.
    $mid = [math]::Floor($v.Count / 2)
    Write-Host ("{0}: n={1} median {2:N2} s  min {3:N2}  max {4:N2}" -f $m, $v.Count, $v[$mid], $v[0], $v[-1])
}
$rows | ConvertTo-Json | Set-Content "$data\timings-alternating.json"
