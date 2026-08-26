$PSNativeCommandUseErrorActionPreference = $false
$BIN = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe"
$SRC = "D:\personal\macro\dry-erase-marker-head-cpl"
$OUT = "C:\dev\strehl-out\BUILD-BLEND\bandsep"
# The 2x2 above ran --unclamped so the excursion was VISIBLE. These two are the
# SHIPPING configuration (hull clamp on, as at HEAD), because that is where the
# mitigation has to be judged: with the clamp on, the zero count is 0.000% either
# way and the question becomes how much the clamp is having to DO.
foreach ($a in @(@{n="A-clamped";mc=0}, @{n="C-clamped";mc=1})) {
  $dst = Join-Path $OUT "$($a.n).tiff"
  if (Test-Path $dst) { "SKIP $($a.n)"; continue }
  $env:STREHL_PYRAMID_MEAN_COARSE = "$($a.mc)"
  "=== $($a.n)  mean_coarse=$($a.mc)  (clamped)"
  & $BIN $SRC $dst --camera-linear --bands 7 *> (Join-Path $OUT "$($a.n).log")
  if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $OUT "$($a.n).log") -Tail 12; throw "failed $($a.n)" }
  Select-String -Path (Join-Path $OUT "$($a.n).log") -Pattern 'clamp|hull' | ForEach-Object { "    " + $_.Line.Trim() }
}
Remove-Item Env:\STREHL_PYRAMID_MEAN_COARSE -ErrorAction SilentlyContinue
"done"
