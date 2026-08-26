$PSNativeCommandUseErrorActionPreference = $false
$BIN = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe"
$OUT = "C:\dev\strehl-out\BUILD-BLEND\perlevel"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null
"binary sha256 : " + (Get-FileHash $BIN -Algorithm SHA256).Hash
# dry-erase is the subject that fails hardest; couch-fibers is ORCH's placebo,
# which reads exactly 0 clipped pixels before and must still read 0 after.
foreach ($s in @("dry-erase-marker-head-cpl","couch-fibers-cpl")) {
  $dst = Join-Path $OUT "$s-perlevel.tiff"
  if (Test-Path $dst) { "SKIP $s"; continue }
  "=== $s  --per-level"
  & $BIN "D:\personal\macro\$s" $dst --camera-linear --per-level *> (Join-Path $OUT "$s.log")
  if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $OUT "$s.log") -Tail 12; throw "failed $s" }
  Select-String -Path (Join-Path $OUT "$s.log") -Pattern 'hull clamp' | ForEach-Object { "    " + $_.Line.Trim() }
}
"done"
