# M98 full-stack render driver -- the D1 ladder.
#
# WHY FULL-STACK AND NOT THE PARITY HALVES.  Splitting a deep bracket in two
# makes each half solve its OWN alignment: on `bee-3-cpl` the halves came out at
# reference frames 75 and 74 with fit_to_cover scales 0.9227 and 0.9360, held-out
# errors 58.4 px and NOT MEASURED, and the two renders are then mutually
# misregistered by a spatially varying field of 10-50 px.  That destroyed the
# high-frequency cross-power the half-merge instrument depends on: the first pass
# returned a finite `dsig` on 0 of 24 ROIs.  Rendering the FULL stack once per
# gate uses ONE alignment solve -- the sidecar on D:, loaded identically at every
# gate -- so every rung of the ladder shares exactly the same geometry and the
# only thing that varies is the gate.  That is the comparison the question asks
# for.  The noise the second render was there to remove is removed instead by
# subtracting the measured above-cutoff floor (see s4_fullstack.py).
param(
    [string]$Stack = "bee-3-cpl",
    [double[]]$Gates = @(0, 0.5, 1, 2, 4),
    [string[]]$Arms = @("ALN", "ZOOM"),
    [string]$Src = ""
)
$bin = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe"
$renders = "C:\dev\strehl-out\M98\renders"
$logs = "C:\dev\strehl-out\M98\logs"
New-Item -ItemType Directory -Force -Path $renders, $logs | Out-Null
if (-not $Src) { $Src = "D:\personal\macro\$Stack" }

# The read-only guarantee, asserted rather than assumed.  A sidecar already
# exists for bee-3-cpl (M86c/M97), so load_or_solve LOADS and writes nothing;
# this fails loudly if that ever stops being true.
$before = (Get-ChildItem $Src -File | ForEach-Object { $_.Name }) -join "|"
foreach ($arm in $Arms) {
    if ($arm -eq "ZOOM") { $env:STREHL_ALIGN = "zoom" } else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
    foreach ($g in $Gates) {
        $gs = "{0:g}" -f $g
        $out = Join-Path $renders "$Stack-FULL-$arm-g$gs.tif"
        $log = Join-Path $logs "$Stack-FULL-$arm-g$gs.log"
        if (Test-Path $out) { Write-Output "skip  $(Split-Path $out -Leaf)"; continue }
        $t = Measure-Command {
            & $bin stack $Src --gate $gs -o $out 2>&1 | Out-File -FilePath $log -Encoding utf8
        }
        Write-Output ("done  {0}  {1:N1}s" -f (Split-Path $out -Leaf), $t.TotalSeconds)
        $after = (Get-ChildItem $Src -File | ForEach-Object { $_.Name }) -join "|"
        if ($after -ne $before) { throw "READ-ONLY VIOLATION in $Src" }
    }
}
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
Write-Output "read-only guarantee held: $Src listing unchanged"
