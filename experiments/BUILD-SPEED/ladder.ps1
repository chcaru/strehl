# Scaling ladder for the DEFAULT pyramid path: how does end-to-end cost move
# with frame count, and what is the intercept?
#
# Rule 16 binds this file. A one-directional sweep attributes thermal drift,
# clock ramp and cache warming to whichever setting came last -- M14 measured
# -0.7% forward and +19% reverse on one binary. So the ladder is walked UP and
# then DOWN, and the per-setting figure is the MINIMUM over every rep in both
# directions. The result is quoted as a bound, not a value, because this box is
# shared with a dozen agents and the load is not mine to control.
#
# Each rung is a --limit on the SAME subject, so frame count is the only thing
# that moves: same geometry, same optics, same decode cost per frame. A
# different subject would confound frame count with content.

$ErrorActionPreference = 'Stop'
$exe = 'C:\dev\strehl-out\BUILD-SPEED\cargo-target\release\strehl.exe'
$dir = 'D:\personal\macro\bee-3-cpl'
$outdir = 'C:\dev\strehl-out\BUILD-SPEED\out'
$env:STREHL_CACHE_DIR = 'C:\dev\strehl-out\BUILD-SPEED\warpcache'
$env:BS_COMMIT = 'b9b6921edc7ecec95443509b0778b4ed48404871'
Set-Location C:\dev\blog\death-of-software\projects\strehl

$rungs = @(20, 40, 80, 150)

foreach ($n in $rungs) {
    python experiments\BUILD-SPEED\timeit_stack.py --exe $exe --dir $dir `
        --out "$outdir\bee-3-cpl-n$n.tif" --reps 2 --limit $n `
        --label "LADDER-UP-$n" --flag=--srgb --flag=--auto-exposure
}
foreach ($n in ($rungs | Sort-Object -Descending)) {
    python experiments\BUILD-SPEED\timeit_stack.py --exe $exe --dir $dir `
        --out "$outdir\bee-3-cpl-n$n.tif" --reps 1 --limit $n `
        --label "LADDER-DOWN-$n" --flag=--srgb --flag=--auto-exposure
}
