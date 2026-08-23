# Confound check: does the measured window optimum track the planted feature
# size? The main run used one bar half-width (12 px, so a 24 px bar). If the
# argmin followed the bar, the "optimum" would be an artifact of the plant
# rather than a property of occlusion. Sweeping the bar width answers it.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m13-window-depth.exe"
$W = @(0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40)
$MEAS = ($W | ForEach-Object { "tenengrad-w$_" }) -join ","

$rows = @()
$hdr = $null
foreach ($half in @(4, 8, 12, 24, 48)) {
    $tmp = "data\_bar-tmp.csv"
    & $exe edge C:\dev\macro\test\109MSDCF --label 109MSDCF `
        --roi-near 2080,1056,384,256 --roi-far 2480,1040,384,256 `
        --frames 41 --steps 8,32 --widths 1 --shape bar --bar-half-width $half `
        --measures $MEAS --out $tmp | Out-Null
    $lines = Get-Content $tmp
    if ($null -eq $hdr) { $hdr = $lines[0]; $rows += $hdr }
    $rows += $lines[1..($lines.Length - 1)]
    Remove-Item $tmp
}
$rows | Set-Content -Encoding ascii data\barwidth-109MSDCF.csv
Write-Host "wrote data\barwidth-109MSDCF.csv ($($rows.Length - 1) rows)"
