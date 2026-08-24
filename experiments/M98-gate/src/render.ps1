# M98 render driver.
#
# One render per (stack, arm, gate, half).  --out requires exactly one --gate,
# so the ladder cannot be folded into a single pass when images are wanted.
#
# The output is the BINNED LINEAR CAMERA-NATIVE default -- the byte-frozen
# measurement file.  --srgb / --demosaic are used only for the owner-facing
# artefact and no number is measured on them (M85 section 5).
param(
    [Parameter(Mandatory = $true)][string]$Stack,
    [string[]]$Arms = @("ALN", "ZOOM"),
    [double[]]$Gates = @(0, 0.5, 1, 2, 4),
    [string[]]$Halves = @("A", "B")
)
$bin = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe"
$frames = "C:\dev\strehl-out\M98\frames"
$renders = "C:\dev\strehl-out\M98\renders"
$logs = "C:\dev\strehl-out\M98\logs"
New-Item -ItemType Directory -Force -Path $renders, $logs | Out-Null

foreach ($half in $Halves) {
    $dir = Join-Path $frames "$Stack-$half"
    if (-not (Test-Path $dir)) { throw "missing $dir" }
    foreach ($arm in $Arms) {
        if ($arm -eq "ZOOM") { $env:STREHL_ALIGN = "zoom" } else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
        foreach ($g in $Gates) {
            $gs = "{0:g}" -f $g
            $out = Join-Path $renders "$Stack-$arm-g$gs-$half.tif"
            $log = Join-Path $logs "$Stack-$arm-g$gs-$half.log"
            if (Test-Path $out) { Write-Output "skip  $out"; continue }
            $t = Measure-Command {
                & $bin stack $dir --gate $gs -o $out 2>&1 | Out-File -FilePath $log -Encoding utf8
            }
            Write-Output ("done  {0}  {1:N1}s" -f (Split-Path $out -Leaf), $t.TotalSeconds)
        }
    }
}
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
