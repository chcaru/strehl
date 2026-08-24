# M111 -- render the `marker` stack with and without the merge-state dump.
#
# Rule 47: the whole invocation and environment is recorded here, beside the
# outputs, including every variable left at a default.
#
#   binary        : built from a pristine `git archive a7bd05a` tree plus this
#                   milestone's additive dump module, in an isolated target dir.
#   stack         : D:\personal\macro\dry-erase-marker-head-cpl, 299 frames,
#                   DSC00286..DSC00584, --limit not passed (all 299).
#   flags         : stack <dir> --srgb --auto-exposure --gate 4 --out <tif>
#                   --limit (not passed), --demosaic (not passed; --srgb implies
#                   the full-resolution demosaicked path), --flat-roi (not
#                   passed), --detail-roi (not passed), --stats (not passed),
#                   --target-n-eff (not passed), --index-map (not passed).
#   STREHL_ALIGN  : unset -> registration ON.
#   STREHL_WARPMAP: PINNED to a private copy of the solve ORCH's render cached,
#                   per rule 45. This removes the solver and the shared sidecar
#                   from every arm; without it a concurrent agent's --limit run
#                   can replace the registration between two of my renders.
#   STREHL_FIX_HALO       : unset (MUST stay off; +63.9% on a halo metric,
#                           +558.4% RMSE against truth).
#   STREHL_FIX_HALO_DELTA : unset.
#   STREHL_CACHE_DIR      : unset -- unused once STREHL_WARPMAP is set.
#   STREHL_DUMP_ELECTION  : unset in arm 1, set in arm 2.
#   STREHL_DUMP_MERGE_STATE: unset in arm 1, set in arm 2.
#   STREHL_M111_REG_RADIUS : unset in both (shipped radius 8).
#   threads       : rayon default = 32 logical CPUs, 13 chunks of <= 23 frames.
#
# Arms 1 and 2 differ ONLY in the two dump variables, so an equal SHA256 is
# rule 26's non-perturbation proof and an unequal one is a defect.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$root = "C:\dev\strehl-out\M111"
$exe = "$root\.cargo-target\release\strehl.exe"
$stack = "D:\personal\macro\dry-erase-marker-head-cpl"
$out = "$root\render"
New-Item -ItemType Directory -Force -Path $out | Out-Null

Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_MERGE_STATE -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS -ErrorAction SilentlyContinue

# Rule 45: pin the registration to a private copy, never the shared sidecar.
$warp = "$root\marker-warpmap.txt"
if (-not (Test-Path $warp)) {
    Copy-Item "$env:LOCALAPPDATA\strehl\warpmaps\dry-erase-marker-head-cpl-57fff568a7ede183.warpmap.txt" $warp
    (Get-Item $warp).LastWriteTime = Get-Date
}
$env:STREHL_WARPMAP = $warp
"warpmap       : $warp  sha256=$((Get-FileHash $warp -Algorithm SHA256).Hash)"
"binary        : $exe  mtime=$((Get-Item $exe).LastWriteTime)"
""

# ---- arm 1: no dump ---------------------------------------------------------
$tif1 = "$out\marker-nodump.tif"
$o1 = & $exe stack $stack --srgb --auto-exposure --gate 4 --out $tif1 2>&1
$c1 = $LASTEXITCODE
$o1 | Out-String | Set-Content -Encoding utf8 "$out\marker-nodump.log"
if ($c1 -ne 0) { throw "arm 1 exited $c1 (expected 0)" }

# ---- arm 2: dump on ---------------------------------------------------------
$dumpdir = "$out\state-r8"
New-Item -ItemType Directory -Force -Path $dumpdir | Out-Null
$env:STREHL_DUMP_ELECTION = "$dumpdir\election.tif"
$env:STREHL_DUMP_MERGE_STATE = $dumpdir
$tif2 = "$out\marker-dump.tif"
$o2 = & $exe stack $stack --srgb --auto-exposure --gate 4 --out $tif2 2>&1
$c2 = $LASTEXITCODE
$o2 | Out-String | Set-Content -Encoding utf8 "$out\marker-dump.log"
if ($c2 -ne 0) { throw "arm 2 exited $c2 (expected 0)" }
Remove-Item Env:STREHL_DUMP_ELECTION
Remove-Item Env:STREHL_DUMP_MERGE_STATE

$h1 = (Get-FileHash $tif1 -Algorithm SHA256).Hash
$h2 = (Get-FileHash $tif2 -Algorithm SHA256).Hash
"NC4 non-perturbation (rule 26)"
"  arm1 no dump  : $h1  $((Get-Item $tif1).Length) bytes"
"  arm2 dump on  : $h2  $((Get-Item $tif2).Length) bytes"
if ($h1 -ne $h2) { throw "THE DUMP MOVED THE OUTPUT: $h1 vs $h2" }
"  IDENTICAL -- the dump does not touch the merged image."
""
"ORCH reference for comparison:"
$orch = "C:\dev\strehl-out\ORCH-thennow\marker-HEAD-8f46f04.tif"
"  8f46f04 render: $((Get-FileHash $orch -Algorithm SHA256).Hash)  $((Get-Item $orch).Length) bytes"
Get-ChildItem $dumpdir | Select-Object Name, Length | Format-Table -AutoSize | Out-String
