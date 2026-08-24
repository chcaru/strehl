$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\dry-erase-marker-head-cpl"
$out = "C:\dev\strehl-out\M97b"
$sc = "$out\warpmap-marker.txt"
$log = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97b-align-visible\data"

# Measurement-grade output only: default binned linear, camera-native RGB.
# M85 forbids measuring --srgb/--demosaic files, so those are rendered
# separately and only for looking at.
function Render($name, $envAlign, $envWarp) {
    Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
    if ($envAlign) { $env:STREHL_ALIGN = $envAlign }
    if ($envWarp) { $env:STREHL_WARPMAP = $envWarp }
    $t0 = Get-Date
    & $exe stack $dir --gate 2 -o "$out\marker-$name.tif" 2>&1 |
        Tee-Object -FilePath "$log\marker-$name.log"
    $dt = ((Get-Date) - $t0).TotalSeconds
    "=== $name rc=$LASTEXITCODE in $([math]::Round($dt,1)) s ==="
    Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
}

Render "UNALIGNED" "0" $null
Render "ALIGNED"   $null $sc
Render "ZOOMNULL"  "zoom" $sc
"ALL DONE"
