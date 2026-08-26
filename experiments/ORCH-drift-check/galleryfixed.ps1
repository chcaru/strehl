# The deliverable gallery: every subject through the FIXED pipeline.
#
# Arm is the pyramid merge with the hull clamp (verified in ORCH-veiling 32) --
# the combination that removes the halo without the black crush. Rendered from
# the pinned interventional build so the gallery is reproducible from a named
# commit rather than from whatever the shared tree happened to contain.
#
# Writes 16-bit TIFF plus a viewable JPEG. Sources on D:\ are read-only.
$ErrorActionPreference = "Continue"
$exe = "C:\dev\strehl-out\ORCH-CLAMP\interv\clamped\target\release\examples\blend-render.exe"
$out = "C:\dev\strehl-out\GALLERY-FIXED"
$src = "D:\personal\macro"

Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null
if (-not (Test-Path $exe)) { "MISSING BINARY: $exe"; exit 1 }

$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
"binary : $exe"
"sha256 : $hash"
"commit : 3dfa435 (pinned git archive, Hull::InputRange as committed)"
"" | Out-File "$out\RUN.txt" -Encoding utf8
"binary sha256 : $hash"       | Out-File "$out\RUN.txt" -Append -Encoding utf8
"commit        : 3dfa435"     | Out-File "$out\RUN.txt" -Append -Encoding utf8
"merge         : pyramid, hull clamp ON, gate 4, base-mean, camera-linear" |
  Out-File "$out\RUN.txt" -Append -Encoding utf8
"started       : $(Get-Date -Format o)" | Out-File "$out\RUN.txt" -Append -Encoding utf8

$subjects = Get-ChildItem $src -Directory |
  Where-Object { (Get-ChildItem "$($_.FullName)\*.ARW" -EA SilentlyContinue).Count -gt 0 } |
  Sort-Object Name

$done = 0; $failed = @(); $skipped = 0
foreach ($s in $subjects) {
  $dst = "$out\$($s.Name).tiff"
  if (Test-Path $dst) { "  {0,-42} already present" -f $s.Name; $skipped++; continue }
  $n = (Get-ChildItem "$($s.FullName)\*.ARW").Count
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $exe $s.FullName $dst --gate 4 --base-mean --camera-linear --chunks 5 2>&1 |
    Out-File -FilePath "$out\$($s.Name).log" -Encoding utf8
  $rc = $LASTEXITCODE
  $sw.Stop()
  "  {0,-42} n={1,4} exit={2} wall={3,7:N1} s" -f $s.Name, $n, $rc, $sw.Elapsed.TotalSeconds
  if ($rc -eq 0) { $done++ } else { $failed += $s.Name; Get-Content "$out\$($s.Name).log" -Tail 8 | ForEach-Object { "     $_" } }
}

# A partition that sums, so a skipped subject cannot read as a rendered one.
"`nrendered={0} skipped={1} failed={2} of {3}" -f $done, $skipped, $failed.Count, $subjects.Count
if ($failed.Count) { "FAILED: $($failed -join ', ')" }
"finished : $(Get-Date -Format o)" | Out-File "$out\RUN.txt" -Append -Encoding utf8
"rendered={0} skipped={1} failed={2} of {3}" -f $done, $skipped, $failed.Count, $subjects.Count |
  Out-File "$out\RUN.txt" -Append -Encoding utf8
