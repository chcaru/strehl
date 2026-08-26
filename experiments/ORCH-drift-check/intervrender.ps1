# Four renders: two subjects x {clamped, unclamped}, one commit, one line apart.
# Same protocol as clean6.ps1 so these are comparable to everything already measured.
$ErrorActionPreference = "Continue"
$root = "C:\dev\strehl-out\ORCH-CLAMP\interv"
$A = "$root\clamped\target\release\examples\blend-render.exe"
$B = "$root\unclamped\target\release\examples\blend-render.exe"
$out = "$root\renders"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($p in @($A, $B)) { if (-not (Test-Path $p)) { "MISSING: $p"; exit 1 } }
$ha = (Get-FileHash $A -Algorithm SHA256).Hash.Substring(0,16)
$hb = (Get-FileHash $B -Algorithm SHA256).Hash.Substring(0,16)
"clamped   : $ha"
"unclamped : $hb"
if ($ha -eq $hb) { "BINARIES IDENTICAL -- nothing to compare"; exit 1 }

# Pin --chunks. VERIFY-WIRE measured that worker count changes the reduction
# order and moves output by 1 DN; an unpinned pair would carry that as noise.
$subjects = @("flower-bud-alone-cpl", "dry-erase-marker-head-cpl")
foreach ($s in $subjects) {
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { "  SKIP $s"; continue }
  "`n=== $s ==="
  foreach ($arm in @(@("clamped",$A), @("unclamped",$B))) {
    $name, $exe = $arm
    $dst = "$out\$s--$name.tiff"
    if (Test-Path $dst) { "    $name already present, skipping"; continue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe $src $dst --gate 4 --base-mean --camera-linear --chunks 5 2>&1 |
      Out-File -FilePath "$out\$s-$name.log" -Encoding utf8
    $rc = $LASTEXITCODE
    $sw.Stop()
    "    {0,-10} exit={1} wall={2,7:N1} s" -f $name, $rc, $sw.Elapsed.TotalSeconds
    if ($rc -ne 0) { Get-Content "$out\$s-$name.log" -Tail 12 | ForEach-Object { "     $_" } }
  }
}

"`n=== outputs ==="
Get-ChildItem "$out\*.tiff" -EA SilentlyContinue | ForEach-Object { "  {0,-46} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB) }

# State check: the clamped arm's log must SAY it clamped, and the unclamped arm
# must not. A pair of binaries that differ in hash but not in behaviour would
# otherwise read as a successful control.
"`n=== behaviour check: the arms must differ in what they report, not just in hash ==="
foreach ($s in $subjects) {
  foreach ($name in @("clamped","unclamped")) {
    $log = "$out\$s-$name.log"
    if (-not (Test-Path $log)) { continue }
    $h = Select-String -Path $log -Pattern "hull|clamp" -EA SilentlyContinue
    "  $s / $name : $(if ($h) { ($h | Select-Object -First 1).Line.Trim() } else { '<no hull/clamp line in log>' })"
  }
}
