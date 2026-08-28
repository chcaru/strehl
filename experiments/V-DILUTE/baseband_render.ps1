# V-DILUTE Assignment 2 -- base-band isolation.
#
# The ONLY difference between --pyramid-base mean and --pyramid-base weighted at
# fixed --pyramid-bands is how the base band is combined.  So the decoded
# difference between the two renders IS the base band's contribution, isolated
# with flags and no source edit.
#
# bands 7 = shipping default (base is 28x19, < 0.008 cyc/px)
# bands 2 = POTENCY arm (base is a 4 px lowpass, reaches to 0.125 cyc/px)
param(
    [Parameter(Mandatory = $true)][string]$Subject,
    [int[]]$Bands = @(7, 2),
    [int]$Limit = 0
)

$ex  = "C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
$src = "D:\personal\macro\$Subject"
$out = "C:\dev\strehl-out\V-DILUTE\baseband"
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($b in $Bands) {
    foreach ($mode in @("mean", "weighted")) {
        $tag = "$Subject.b$b.$mode"
        $tif = Join-Path $out "$tag.tiff"
        $log = Join-Path $out "$tag.log"
        if (Test-Path $tif) { Write-Output "SKIP $tag"; continue }

        $a = @("stack", $src, "-o", $tif, "--merge", "pyramid",
               "--pyramid-bands", "$b", "--pyramid-base", $mode)
        if ($Limit -gt 0) { $a += @("--limit", "$Limit") }

        $t0 = Get-Date
        & $ex @a *>&1 | Tee-Object -FilePath $log | Out-Null
        $dt = ((Get-Date) - $t0).TotalSeconds
        if (Test-Path $tif) {
            Write-Output ("OK   {0,-34} {1,7:N1}s" -f $tag, $dt)
        } else {
            Write-Output ("FAIL {0,-34} exit={1}" -f $tag, $LASTEXITCODE)
            Get-Content $log -Tail 6 | ForEach-Object { "       $_" }
        }
    }
}
