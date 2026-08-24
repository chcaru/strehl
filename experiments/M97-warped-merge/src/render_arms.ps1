# M97 render arms. Every arm is the same merge on the same bracket; only the
# registration differs. Timings are wall clock on this machine.
#
# NOTE: no arm may write to D:. STREHL_ALIGN=0 never touches the sidecar path,
# and STREHL_WARPMAP loads an explicitly named file and never caches.

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97"
$data = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\data"
New-Item -ItemType Directory -Force -Path $out, $data | Out-Null

$arms = @(
    @{ name = "UNALIGNED"; align = "0";    map = $null },
    @{ name = "ALIGNED";   align = $null;  map = "$out\warpmap-ruler.txt" },
    @{ name = "ZOOMNULL";  align = "zoom"; map = "$out\warpmap-ruler.txt" },
    @{ name = "JITTER6";   align = $null;  map = "$out\warpmap-ruler-JITTER6.txt" },
    @{ name = "IDENTITY";  align = $null;  map = "$out\warpmap-ruler-IDENTITY.txt" }
)

$rows = @()
foreach ($a in $arms) {
    $env:STREHL_ALIGN = $a.align
    $env:STREHL_WARPMAP = $a.map
    if ($null -eq $a.align) { Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue }
    if ($null -eq $a.map) { Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue }
    $tif = "$out\ruler-$($a.name).tif"
    $log = "$data\render-$($a.name).log"
    Write-Host "=== $($a.name) ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $dir --gate 2 --srgb --demosaic -o $tif 2>&1 | Out-File -FilePath $log -Encoding utf8
    $rc = $LASTEXITCODE
    $sw.Stop()
    $rows += [pscustomobject]@{ arm = $a.name; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2); rc = $rc }
    Write-Host ("  rc={0}  {1:N2} s -> {2}" -f $rc, $sw.Elapsed.TotalSeconds, $tif)
    Get-Content $log | Select-String -Pattern "^alignment|coverage      :|held-out err" | ForEach-Object { "    " + $_.Line.Trim() }
}
Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue

$rows | Format-Table -AutoSize
$rows | ConvertTo-Json | Set-Content "$data\timings-ruler.json"
