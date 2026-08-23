# M40 verification, step 05 -- the two-binary confidence diff.
#
# NOT a script that was run as a script: this is the exact transcript of the commands
# issued interactively, recorded so the run is reproducible. The outputs it names are
# committed beside it in ../out/ and were produced by these commands verbatim.
#
# The point of the step is a CONTROLLED comparison. crates/ at edb1c06 is byte-identical
# to crates/ at 253e56f, so a binary built from the working tree and a binary built from a
# detached worktree at 253e56f~1 differ in crates/ ONLY by the reviewed commit -- i.e.
# only by SELECTION_INFLATION and the rewritten test.
#
# RULE 20 -- what would make this fail. If inflating C1 changed the confidence mask, the
# by_sigma / by_perplexity / by_deficit / by_flags / UNION counts would differ between the
# two arms. They do not, at either gate. That is the measurement, and a single differing
# count would have refuted it.

$repo = "C:\dev\blog\death-of-software\projects\strehl"
$wt   = Join-Path $env:TEMP "strehl-m40-baseline"
$out  = "$repo\experiments\m40-verify-341\out"
$env:PATH    = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:RUST_LOG = "error"

# The pre-fix arm.
git -C $repo worktree add --detach $wt 253e56f~1
Push-Location $wt; cargo build --release; Pop-Location

# The post-fix arm is the working tree's own release binary.
Push-Location $repo; cargo build --release; Pop-Location

foreach ($g in @("0", "1")) {
  & "$wt\target\release\strehl.exe" merge "C:\dev\macro\test\109MSDCF" --gate $g `
      --stats --stats-placebo `
      --flat-roi 2272,1344,256,256 --detail-roi 2272,1344,256,256 2>&1 |
    Out-File -Encoding utf8 "$out\05-conf-109-g$g-I1000.txt"

  & "$repo\target\release\strehl.exe" merge "C:\dev\macro\test\109MSDCF" --gate $g `
      --stats --stats-placebo `
      --flat-roi 2272,1344,256,256 --detail-roi 2272,1344,256,256 2>&1 |
    Out-File -Encoding utf8 "$out\05-conf-109-g$g-I1074.txt"
}

git -C $repo worktree remove --force $wt

# Read the four channels out of all four files:
foreach ($g in @("0", "1")) { foreach ($i in @("I1000", "I1074")) {
  Write-Output "=== gate $g  $i ==="
  Get-Content "$out\05-conf-109-g$g-$i.txt" |
    Select-String -Pattern "^  C1 sigma|^  C2 perpl|^  C3 defic|^  C4 flags|^  UNION|^  mean C2" |
    ForEach-Object { $_.Line }
}}
