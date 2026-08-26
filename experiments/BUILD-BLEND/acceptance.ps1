# ORCH's clamp acceptance test, run with the PRODUCT binary instead of the
# example binary.
#
# ORCH's original design used two separately-pinned executables (strehl.exe for
# BEFORE, blend-render.exe for AFTER).  That confounds the merge backend with
# every other difference between two binaries built at different commits --
# including, as it turns out, a `.max(0.0)` clamp that exists in
# blend-render.rs:611 and does NOT exist in merge_cmd.rs:5971/6092.
#
# This runs both arms from ONE binary, one flag apart (`--merge estimator`
# against the default `--merge pyramid`), so the merge backend is the only
# thing that differs.  Every other flag is identical by construction.

$ErrorActionPreference = "Stop"
$exe = "C:\dev\strehl-out\BUILD-BLEND\target-gate\release\strehl.exe"
$out = "C:\dev\strehl-out\BUILD-BLEND\acceptance"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# dry-erase is ORCH's worst MERGE-verdict subject; couch-fibers is the placebo
# that must not regress (currently +0.0000).
$subjects = @("dry-erase-marker-head-cpl", "couch-fibers-cpl")

"binary : $exe"
"sha256 : $((Get-FileHash $exe -Algorithm SHA256).Hash)"
""

foreach ($s in $subjects) {
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { "SKIP $s (no such stack)"; continue }
  foreach ($arm in @("estimator", "pyramid")) {
    $dst = "$out\$s-$arm.tiff"
    if (Test-Path $dst) { "have  $s / $arm"; continue }
    $t0 = Get-Date
    & $exe stack $src --out $dst --merge $arm 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { "FAIL  $s / $arm (exit $LASTEXITCODE)"; continue }
    "wrote $s / $arm  in $([int]((Get-Date) - $t0).TotalSeconds) s"
  }
}
