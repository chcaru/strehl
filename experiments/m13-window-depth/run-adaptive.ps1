# M13 adaptive-rule sweep. Each run pins one (narrow, wide) pair; the mode
# emits both fixed arms under the same seed as the adaptive arms, so the
# within-run comparison is valid. Cross-run comparison is NOT, because the
# noise seed is derived per step inside the mode.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = ".\target\release\m13-window-depth.exe"
$stack = "C:\dev\macro\test\109MSDCF"
$pairs = @(
    @("tenengrad-w2",  "tenengrad-w40"),
    @("tenengrad-w5",  "tenengrad-w40"),
    @("tenengrad-w8",  "tenengrad-w40"),
    @("tenengrad-w2",  "tenengrad-w15"),
    @("tenengrad-w5",  "tenengrad-w15"),
    @("tenengrad-w11", "tenengrad-w40")
)
$all = @()
$header = $null
foreach ($p in $pairs) {
    $tmp = "data\_adaptive-tmp.csv"
    & $exe adaptive $stack --label 109MSDCF `
        --roi-near 2080,1056,384,256 --roi-far 2480,1040,384,256 `
        --frames 41 --steps 0,4,8,16,32 --width 1 --taus 1,2,3,4,6,8 `
        --narrow $p[0] --wide $p[1] --out $tmp | Out-Null
    $lines = Get-Content $tmp
    if ($null -eq $header) { $header = $lines[0]; $all += $header }
    $all += $lines[1..($lines.Length - 1)]
    Remove-Item $tmp
}
$all | Set-Content -Encoding ascii data\adaptive-109MSDCF.csv
Write-Host "wrote data\adaptive-109MSDCF.csv ($($all.Length - 1) rows)"
