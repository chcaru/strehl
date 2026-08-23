# Re-run every M23 arm from scratch.  READ-ONLY on all data trees.
#   powershell -File run-m23.ps1
# Total wall clock on 32 logical cores: about 8 minutes plus the two Python gates.

$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path data, out | Out-Null

$CB  = "C:\dev\macro\test\coffee-bean"     # 105 frames
$S112 = "D:\personal\macro\112MSDCF"       # 79 frames
$D = "0.0001,0.0002,0.0004,0.0008,0.0016"
$SPANS = "1,2,8,16,32,48"

cargo build --release

$bin = ".\target\release\m23-metacal.exe"

# ---- read-only audit BEFORE (rule 14: -Force, or the corpus under-reports) ----
$o = @()
foreach ($r in "C:\dev\macro", "D:\personal\macro") {
  $f = Get-ChildItem -Path $r -Recurse -File -Force -ErrorAction SilentlyContinue
  $o += "$r : $($f.Count) files, $(($f | Measure-Object -Property Length -Sum).Sum) bytes"
}
$o | Out-File -Encoding utf8 out\readonly-audit-before.txt

# ---- main arms -------------------------------------------------------------
# NOTE: do NOT pipe these through `Tee-Object ... | Select-Object -First N`;
# it truncates the tee'd file (M12 README gotcha).  Plain `>` only.
& $bin metacal $CB coffee-bean --case coffee-bean --cfgs m10 `
    --spans $SPANS --deltas $D 2> out\run-coffee-bean.txt

& $bin metacal $S112 stack-112 --case 112MSDCF --cfgs m10 `
    --spans $SPANS --deltas $D 2> out\run-112.txt

# ---- control arms ----------------------------------------------------------
# N3   self-pair: frame k against ITSELF, zero defocus difference
& $bin metacal $CB cb-self --case cb-self --cfgs m10 `
    --spans 1 --stride 2 --self --deltas $D 2> out\run-cb-self.txt

# N3b  self-pair pushed off the sub-pixel locking zone by a 4e-3 pedestal
& $bin metacal $CB cb-self-ped --case cb-self-ped --cfgs m10 `
    --spans 1 --stride 2 --self --pedestal 0.004 --deltas $D 2> out\run-cb-self-ped.txt

# real pairs, same pedestal: defocus present, locking zone removed
& $bin metacal $CB cb-ped --case cb-ped --cfgs m10 `
    --spans 1 --stride 2 --pedestal 0.004 --deltas $D 2> out\run-cb-ped.txt

# N4b  synthetic band-limited field: NO interpolator anywhere in the path
& $bin metacal $CB cb-field --case field-p0 --cfgs m10 `
    --field 12 --deltas $D 2> out\run-cb-field.txt

# ---- analysis --------------------------------------------------------------
python m23_response.py  > out\response.txt
python m23_controls.py  > out\controls.txt
python m23_conserve.py  > out\conservation.txt
python m23_heldout.py   > out\heldout.txt
python m23_cost.py      > out\cost.txt
Remove-Item data\cost-tmp-metacal.csv -ErrorAction SilentlyContinue

# ---- read-only audit AFTER -------------------------------------------------
$o = @()
foreach ($r in "C:\dev\macro", "D:\personal\macro") {
  $f = Get-ChildItem -Path $r -Recurse -File -Force -ErrorAction SilentlyContinue
  $o += "$r : $($f.Count) files, $(($f | Measure-Object -Property Length -Sum).Sum) bytes"
}
$o | Out-File -Encoding utf8 out\readonly-audit-after.txt
Compare-Object (Get-Content out\readonly-audit-before.txt) `
               (Get-Content out\readonly-audit-after.txt)
