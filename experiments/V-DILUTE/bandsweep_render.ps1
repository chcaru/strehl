# V-DILUTE Assignment 2 -- ORCH item 2: sweep --pyramid-bands.
#
# Prediction to falsify (ORCH's): more bands -> less structure left in the base
# band -> sharper output, with the gain LARGER on deep stacks.
param(
    [Parameter(Mandatory = $true)][string]$Subject,
    [int[]]$Bands = @(3, 4, 5, 6, 7, 8, 9)
)

$ex  = "C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
$src = "D:\personal\macro\$Subject"
$out = "C:\dev\strehl-out\V-DILUTE\bandsweep"
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($b in $Bands) {
    $tag = "$Subject.nb$b"
    $tif = Join-Path $out "$tag.tiff"
    $log = Join-Path $out "$tag.log"
    if (Test-Path $tif) { Write-Output "SKIP $tag"; continue }

    $t0 = Get-Date
    & $ex stack $src -o $tif --merge pyramid --pyramid-bands $b *>&1 |
        Tee-Object -FilePath $log | Out-Null
    $dt = ((Get-Date) - $t0).TotalSeconds
    if (Test-Path $tif) {
        Write-Output ("OK   {0,-26} {1,7:N1}s" -f $tag, $dt)
    } else {
        Write-Output ("FAIL {0,-26} exit={1}" -f $tag, $LASTEXITCODE)
        Get-Content $log -Tail 8 | ForEach-Object { "       $_" }
    }
}
