$PSNativeCommandUseErrorActionPreference = $false
$BIN = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe"
$OUT = "C:\dev\strehl-out\BUILD-BLEND\gate"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null
"binary sha256 : " + (Get-FileHash $BIN -Algorithm SHA256).Hash
# ORCH's accept.py groups as <subject>--<arm>.tiff. The reference is re-rendered
# by THIS binary so the only difference between ref and candidate is the flag.
$S = "dry-erase-marker-head-cpl"
$arms = @(
  @{ n="ref";    fl=@() },
  @{ n="hull2";  fl=@("--per-level","--hull-lambda","2") },
  @{ n="hull4";  fl=@("--per-level","--hull-lambda","4") }
)
foreach ($a in $arms) {
  $dst = Join-Path $OUT "$S--$($a.n).tiff"
  if (Test-Path $dst) { "SKIP $($a.n)"; continue }
  "=== $S -- $($a.n)"
  & $BIN "D:\personal\macro\$S" $dst --camera-linear @($a.fl) *> (Join-Path $OUT "$S--$($a.n).log")
  if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $OUT "$S--$($a.n).log") -Tail 10; throw "failed $($a.n)" }
}
"done"
