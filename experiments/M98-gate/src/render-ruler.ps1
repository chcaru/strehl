# M98 ruler render driver -- the external anchor.
#
# `highly-angled-ruler-mm-cpl` is in align_cmd.rs's TILTED_SUBJECTS, so
# `load_or_solve` returns None BEFORE it touches `sidecar_path()`.  Nothing is
# written next to the frames, so this is the one stack that can be rendered
# directly out of the read-only D:\personal\macro tree.  Verified after the
# first render by asserting the directory listing is unchanged.
param(
    [double[]]$Gates = @(0, 0.5, 1, 2, 4),
    [string]$Src = "D:\personal\macro\highly-angled-ruler-mm-cpl"
)
$bin = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe"
$renders = "C:\dev\strehl-out\M98\renders"
$logs = "C:\dev\strehl-out\M98\logs"
New-Item -ItemType Directory -Force -Path $renders, $logs | Out-Null

$before = (Get-ChildItem $Src -File | Measure-Object).Count
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
foreach ($g in $Gates) {
    $gs = "{0:g}" -f $g
    $out = Join-Path $renders "ruler-g$gs.tif"
    $log = Join-Path $logs "ruler-g$gs.log"
    if (Test-Path $out) { Write-Output "skip  $out"; continue }
    $t = Measure-Command {
        & $bin stack $Src --gate $gs -o $out 2>&1 | Out-File -FilePath $log -Encoding utf8
    }
    Write-Output ("done  ruler-g$gs.tif  {0:N1}s" -f $t.TotalSeconds)
    $after = (Get-ChildItem $Src -File | Measure-Object).Count
    if ($after -ne $before) { throw "READ-ONLY VIOLATION: $Src file count $before -> $after" }
}
Write-Output "read-only guarantee held: $Src still has $before files"
