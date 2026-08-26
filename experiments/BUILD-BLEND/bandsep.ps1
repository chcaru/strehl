# BUILD-BLEND: separating the two mechanisms confounded in the band count
#
# REGISTERED BEFORE THE FIRST RENDER.  ORCH's band sweep localised the
# out-of-hull excursion to the seventh band -- flat and negligible from 2 to 6,
# then a 52x step on the single addition of band 7.  ORCH correctly notes that
# going 6 -> 7 does TWO things at once and that the band count alone cannot
# separate them:
#
#   M1  a Laplacian level at the coarsest selected scale (level 6) becomes
#       SELECTED, where at bands=6 that scale lived inside the averaged base
#       residual and was merged as a plain mean.
#
#   M2  the exponent ramp SHIFTS.  exponent_at anchors the ramp at the COARSEST
#       band (which always gets exactly `exponent`), so adding a coarser level
#       multiplies every pre-existing level's exponent by sharpen_per_octave=1.4,
#       pushing one more level into the MAX_EXPONENT=8 cap.
#
# Both are addressable from inside the code with EXISTING config fields, so this
# is a 2x2 factorial rather than a ladder:
#
#   arm  invocation                          M1 (band 6 selected)  M2 (ramp shifted)
#   A    --bands 7                                  yes                  yes
#   B    --bands 6                                  no                   no
#   C    --bands 7, MEAN_COARSE=1                   no                   yes
#   D    --bands 7 --exponent 1.42857               yes                  no
#
# Why each isolation is EXACT rather than approximate:
#
#   C   `averaged = k + mean_coarse >= nb` (pyramid.rs:1050) zeroes the weight
#       for the coarsest Laplacian band, routing it through the unweighted
#       fallback = a plain mean.  Because Laplacian_6 + upsample(base_7) ==
#       Gaussian_6 and the mean is LINEAR across frames, averaging both level 6
#       and the level-7 base reproduces bands=6's BaseBand::Mean base at level 6
#       identically.  The finer bands keep the bands=7 ramp.
#
#   D   exponent_at(k, bands) = min(exponent * 1.4^((bands-1)-k), 8.0).
#       At exponent = 2.0/1.4 = 1.42857 with bands=7, indexing from the FINE
#       end, levels 0..5 evaluate to 8.00, 7.683, 5.488, 3.920, 2.800, 2.000 --
#       which is bands=6's default sequence exactly -- plus a new coarsest level
#       at 1.4286.  The new band is therefore present but LESS selective than it
#       would be by default (1.43 vs 2.0), which biases AGAINST detecting an
#       effect from M1.  A positive result under that handicap is strong.
#
# PREDICTIONS, registered now, outcome unknown:
#
#   If M1 alone is operative      A high, D high, B low, C low
#   If M2 alone is operative      A high, C high, B low, D low
#   If the INTERACTION is needed  A high, B and C and D all low
#   If neither reproduces         A high, B/C/D low -> my isolation is wrong,
#                                 and I report that rather than reinterpreting
#
# My own prior, recorded so it can be scored: I expect M1, because the block
# artifacts are 40-60 px and one level-6 coefficient reconstructs to a ~64 px
# footprint.  A ramp shift on FINER bands cannot produce a 64 px hard-edged
# block.  If C comes back high I will have been wrong about the mechanism.
#
# READOUT.  All arms rendered --camera-linear --unclamped so the metric is
# ORCH's exact-zero percentage in ORCH's units, directly comparable to their
# table.  The clamp is disabled deliberately: at HEAD the hull clamp already
# reads 0.000% on every arm, which would make all four arms tie at zero and
# measure nothing.  Unclamped is the instrument that can still SEE the
# excursion this experiment is trying to attribute.

$ErrorActionPreference = "Stop"
# ...except around the native call: blend-render writes its banner to stderr, and
# with 2>&1 under "Stop" PowerShell raises NativeCommandError on the FIRST line of
# it and aborts before the render begins. Exit status is checked explicitly via
# $LASTEXITCODE below, which is the correct signal for a native process anyway.
$PSNativeCommandUseErrorActionPreference = $false
$BIN = "C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe"
$SRC = "D:\personal\macro\dry-erase-marker-head-cpl"
$OUT = "C:\dev\strehl-out\BUILD-BLEND\bandsep"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

if (-not (Test-Path $BIN)) { throw "binary missing: $BIN" }
"binary sha256 : " + (Get-FileHash $BIN -Algorithm SHA256).Hash
"source        : $SRC"

$arms = @(
  @{ n = "A-bands7";        bands = 7; exp = $null;     mc = 0 },
  @{ n = "B-bands6";        bands = 6; exp = $null;     mc = 0 },
  @{ n = "C-ramp-only";     bands = 7; exp = $null;     mc = 1 },
  @{ n = "D-newband-only";  bands = 7; exp = "1.42857"; mc = 0 }
)

foreach ($a in $arms) {
  $dst = Join-Path $OUT "$($a.n).tiff"
  if (Test-Path $dst) { "SKIP $($a.n) (exists)"; continue }
  $argv = @($SRC, $dst, "--camera-linear", "--unclamped", "--bands", $a.bands)
  if ($a.exp) { $argv += @("--exponent", $a.exp) }
  $env:STREHL_PYRAMID_MEAN_COARSE = "$($a.mc)"
  "=== $($a.n)  bands=$($a.bands) exponent=$(if($a.exp){$a.exp}else{'default'}) mean_coarse=$($a.mc)"
  $t0 = Get-Date
  $log = Join-Path $OUT "$($a.n).log"
  # NOT `| Select-Object -First N`: that closes the pipe as soon as it has its N
  # objects, which terminates the upstream NATIVE process. It killed the first
  # run of this script mid-render and reported exit -1, which reads exactly like
  # a merge failure. Capture everything to a log and filter the file afterwards.
  $ErrorActionPreference = "Continue"
  & $BIN @argv *> $log
  $rc = $LASTEXITCODE
  $ErrorActionPreference = "Stop"
  if ($rc -ne 0) { Get-Content $log -Tail 15; throw "render failed for $($a.n) (exit $rc)" }
  if (-not (Test-Path $dst)) { throw "render reported success but wrote no file: $dst" }
  Select-String -Path $log -Pattern 'bands  |exponent|hull|clamp' | ForEach-Object { "    " + $_.Line.Trim() }
  "    {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds
}
Remove-Item Env:\STREHL_PYRAMID_MEAN_COARSE -ErrorAction SilentlyContinue
"`nall arms rendered to $OUT"
