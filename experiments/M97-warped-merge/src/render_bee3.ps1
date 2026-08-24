# M97 owner-facing deliverable: bee-3-cpl before/after, plus the matched null.
#
# Reads the sidecar M86c already cached beside the capture. STREHL_WARPMAP
# only ever READS, so this run leaves D: exactly as it found it.

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$map = "D:\personal\macro\bee-3-cpl\warpmap.txt"
$out = "C:\dev\strehl-out\M97-before-after"
$data = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\data"
New-Item -ItemType Directory -Force -Path $out, $data | Out-Null

$arms = @(
    @{ name = "BEFORE-unaligned"; align = "0";    map = $null },
    @{ name = "AFTER-aligned";    align = $null;  map = $map },
    @{ name = "NULL-zoomonly";    align = "zoom"; map = $map }
)

$rows = @()
foreach ($a in $arms) {
    Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
    if ($null -ne $a.align) { $env:STREHL_ALIGN = $a.align }
    if ($null -ne $a.map) { $env:STREHL_WARPMAP = $a.map }
    $tif = "$out\bee-3-$($a.name).tif"
    $log = "$data\bee3-$($a.name).log"
    Write-Host "=== $($a.name) ==="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $dir --gate 2 --srgb --demosaic -o $tif 2>&1 | Out-File -FilePath $log -Encoding utf8
    $rc = $LASTEXITCODE
    $sw.Stop()
    $rows += [pscustomobject]@{ arm = $a.name; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2); rc = $rc }
    Write-Host ("  rc={0}  {1:N2} s -> {2}" -f $rc, $sw.Elapsed.TotalSeconds, $tif)
}
Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
$rows | Format-Table -AutoSize
$rows | ConvertTo-Json | Set-Content "$data\timings-bee3.json"
