# M98 D4 view renders -- sRGB + demosaic, FOR LOOKING AT ONLY.
#
# M85 section 5 and rule 5: no number is measured on a demosaiced sRGB render.
# These exist to be shown to the owner; every figure annotated on the panel is
# carried in from the linear camera-native measurement path.
param(
    [string]$Stack = "bee-3-cpl",
    [double[]]$Gates = @(0, 0.5, 1, 2, 4)
)
$bin = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe"
$renders = "C:\dev\strehl-out\M98\renders"
$logs = "C:\dev\strehl-out\M98\logs"
$src = "D:\personal\macro\$Stack"
New-Item -ItemType Directory -Force -Path $renders, $logs | Out-Null
$before = (Get-ChildItem $src -File | ForEach-Object { $_.Name }) -join "|"
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
foreach ($g in $Gates) {
    $gs = "{0:g}" -f $g
    $out = Join-Path $renders "$Stack-VIEW-g$gs.tif"
    if (Test-Path $out) { Write-Output "skip  $(Split-Path $out -Leaf)"; continue }
    $t = Measure-Command {
        & $bin stack $src --gate $gs --srgb --demosaic -o $out 2>&1 |
            Out-File -FilePath (Join-Path $logs "$Stack-VIEW-g$gs.log") -Encoding utf8
    }
    Write-Output ("done  {0}  {1:N1}s" -f (Split-Path $out -Leaf), $t.TotalSeconds)
    $after = (Get-ChildItem $src -File | ForEach-Object { $_.Name }) -join "|"
    if ($after -ne $before) { throw "READ-ONLY VIOLATION in $src" }
}
Write-Output "read-only guarantee held: $src listing unchanged"
