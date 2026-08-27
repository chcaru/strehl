# V-LINEAR / develop_frames.ps1
#
# WHAT THIS IS AND WHY IT IS strehl'S OWN DECODER
# -----------------------------------------------
# V-HEADTOHEAD2 s7 Blocker 1: the comparators were fed Lightroom-developed
# TIFFs carrying `Contrast2012=+100` while strehl reads RAW, and a tone map
# fitted on 4x4 BLOCK MEANS -- containing zero information above 0.125 cyc/px --
# reproduced Zerene's 0.25-0.30 band power from strehl's pixels to 0.02%.
# Every fine-scale number in that table was a tone measurement.
#
# The fix is to hand the comparator the same photons strehl gets, with no tone
# curve on them.  This develops each RAW frame INDIVIDUALLY through strehl's own
# decoder, which is deliberate:
#
#   * demosaic (Malvar-He-Cutler), white balance, black level, colour matrix and
#     lateral-CA correction are then BIT-FOR-BIT THE SAME operation in both arms.
#     The only thing left different between "strehl's render" and "Zerene's
#     render" is the STACKING ALGORITHM, which is the thing under test.
#   * --linear-srgb stops before the transfer curve, and the file says so in an
#     embedded ICC profile whose rTRC/gTRC/bTRC are all `curv` count 0, i.e.
#     the identity.  MEASURED by experiments/V-LINEAR/icc_dump.py.  A
#     colour-managed reader therefore cannot mistake it for gamma-encoded data.
#
# WHY STREHL_ALIGN=0
# ------------------
# With alignment ON, a one-frame stack still reports
#   "coverage : field of view scaled to 0.9974 ... then upsampled"
# which is a CatmullRom resample of the frame.  Zerene then registers and
# resamples again, so the Zerene arm would carry TWO resamples against strehl's
# one -- a fine-scale handicap pointing at the comparator, in a milestone whose
# whole job is to remove handicaps.  With STREHL_ALIGN=0 the develop is
# decode -> CA -> demosaic -> matrix -> u16 and nothing is resampled, so each
# arm carries exactly one registration resample: its own.
#
# RULE 47 RECORD ------------------------------------------------------------
#   binary     C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#              sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#              THE SAME BINARY V-HEADTOHEAD2 rendered its strehl arm with, so the
#              develop and the arm it is compared against share a decoder build.
#   subcommand stack
#   flags      --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic
#   NOT passed --srgb, --binned, --exposure, --auto-exposure, --limit,
#              --resampler, --fix-ca (the profile is default-on and matched),
#              --photometric, --gate, --stats
#   env set    STREHL_FULLRES_GATHER = 1   (matches the g1 arm of V-H2H2)
#              STREHL_ALIGN          = 0   (see above)
#   env cleared by name before every render: see $clear.
#   source     D:\personal\macro\113MSDCF, 63 x .ARW, READ-ONLY: each frame is
#              COPIED to a private one-frame directory under
#              C:\dev\strehl-out\V-LINEAR\src and the copy is what is decoded.
#
# A one-frame `stack` is a passthrough of the merge: with N=1 the soft selection
# weights are all 1 and the "averaged" fraction averages one frame with itself.
# That is asserted, not assumed -- experiments/V-LINEAR/commission_develop.py
# checks it against a second backend.

$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$src  = 'D:\personal\macro\113MSDCF'
$root = 'C:\dev\strehl-out\V-LINEAR'
$work = "$root\src"
$dst  = "$root\lintiff"
$logs = "$root\logs"
New-Item -ItemType Directory -Force -Path $work, $dst, $logs | Out-Null

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER')

$frames = Get-ChildItem $src -File -Filter *.ARW | Sort-Object Name
Write-Host ("source frames: {0}" -f $frames.Count)
if ($frames.Count -ne 63) { throw "expected 63 ARW in $src, found $($frames.Count)" }

$n = 0
foreach ($f in $frames) {
  $stem = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
  $out  = "$dst\$stem.tif"
  $n++
  if (Test-Path $out) { Write-Host "  $stem exists, skipped"; continue }

  $one = "$work\$stem"
  New-Item -ItemType Directory -Force -Path $one | Out-Null
  if (-not (Test-Path "$one\$($f.Name)")) { Copy-Item $f.FullName "$one\$($f.Name)" }

  foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_ALIGN = '0'

  $t0 = Get-Date
  $log = "$logs\dev-$stem.log"
  & $exe stack $one --out $out --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File -FilePath $log -Encoding utf8
  $code = $LASTEXITCODE
  $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  $len = if (Test-Path $out) { (Get-Item $out).Length } else { 0 }
  Write-Host ("  [{0}/{1}] {2} exit={3} {4}s bytes={5}" -f $n, $frames.Count, $stem, $code, $dt, $len)
  if ($code -ne 0) { throw "$stem failed with exit $code" }
  if ($len -ne 197798923) { throw "$stem wrote $len bytes, expected 197798923" }
}
Write-Host "ALL 63 LINEAR DEVELOPS DONE"
