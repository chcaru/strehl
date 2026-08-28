# Corpus before/after for the candidate fix, cheapest subject first.
#
# WHY BOTH ARMS ARE RE-RENDERED. The obvious cheap design is to score bands5
# against the delivered faithful masters in C:\dev\strehl-out\ORCH-FAITHFUL.
# That design is wrong. Those masters were rendered at commit 5f367a94; this
# binary is cc985615-dirty and additionally carries another lane's uncommitted
# merge_cmd.rs. A bands5-vs-delivered difference would therefore be the flag
# PLUS 13+ commits PLUS a foreign working-tree diff, and nothing in the number
# would say which. Re-rendering the baseline with the same binary costs a
# second pass and makes the difference attributable to the flag alone.
#
# WHY THIS SUBJECT LIST. The acceptance condition is not "the fix helps the
# subjects it was tuned on"; it is "the fix helps those and does not harm the
# rest". So the list spans all three verdict classes from the baseline table --
# 7 HALO, 7 gradient-only, 12 clean -- and both ends of stack depth, because
# every depth-related effect this project has measured separates only across N:
#
#   HALO      109MSDCF 22, 119MSDCF 33, coffee-bean 105, leaf-2-cpl 182,
#             dry-erase-marker-head-cpl 299
#             (tweezers-cpl 100 and lead-1-cpl 123 already rendered by the
#              knob sweep; sweep.ps1 skips existing files)
#   gradient  flat-on-ruler-cpl 79, 112MSDCF 79
#   clean     coffee-bubbles 19, foam 100, bee-1-cpl 299
#
# bee-1-cpl is on the list specifically because it is ORCH's showcase subject
# and the deepest stack in the corpus. A change that fixes tweezers-cpl and
# puts a rim on bee-1-cpl is not a fix, and 299 frames is where dilution
# effects would show up if the band count has any.

param(
    [string]$ArmSet = "ab",
    [string]$Bin = "C:\dev\blog\death-of-software\projects\strehl\target-vspeed\release\strehl.exe"
)

$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Cheapest first, so the corpus-level signal arrives long before the 299-frame
# stacks finish. Nine other agents are on this machine and a run that only
# reports at the end may not report at all.
$subjects = @(
    "coffee-bubbles",             #  19  clean
    "109MSDCF",                   #  22  HALO dark
    "119MSDCF",                   #  33  HALO pair
    "flat-on-ruler-cpl",          #  79  gradient
    "112MSDCF",                   #  79  gradient
    "foam",                       # 100  clean
    "coffee-bean",                # 105  HALO dark
    "leaf-2-cpl",                 # 182  HALO pair
    "dry-erase-marker-head-cpl",  # 299  HALO bright
    "bee-1-cpl"                   # 299  clean, showcase
)

foreach ($s in $subjects) {
    Write-Output "==== $s ===="
    & (Join-Path $here "sweep.ps1") -Subject $s -ArmSet $ArmSet -Bin $Bin
    Write-Output ""
}
Write-Output "AB SWEEP COMPLETE"
