# V-H2H2 / render_linear.ps1
#
# WHY THIS SUPERSEDES render_all.ps1's --srgb PASS
# ------------------------------------------------
# `strehl stack --help` states the standing rule outright:
#
#   "--linear-srgb ... THIS IS THE MODE TO MEASURE IN. The standing rule is
#    that quality is never judged on an --srgb render, because the transfer
#    curve is a strong non-linearity that moves every ratio a metric computes;
#    more than one result in this project has been retracted for exactly that.
#    But the only alternative used to be the default, whose primaries are the
#    sensor's own and are stated nowhere -- so a measurement was either taken
#    through a curve or in an undeclared space. This applies the matrix and
#    stops before the curve: a STATED colorimetric target that is still linear."
#
# The first pass rendered --srgb and inverted the tone numerically.  That
# works -- and it is the wrong thing to do when the tool will simply not apply
# the curve if asked.  Every gram of tone-inversion code is a gram of
# transcription risk that this flag removes.
#
# --demosaic is passed EXPLICITLY.  Without it the default output is BINNED to
# 3516x2344 -- one pixel per 2x2 sensor quad -- which discards the entire
# frequency range this milestone exists to measure.  The help says --demosaic
# is on by default "whenever --srgb is given"; it does not say --linear-srgb
# counts, so it is stated rather than assumed.
#
# NO --exposure.  Exposure is one multiply in linear light; every statistic
# downstream is normalised by the ROI mean and is therefore invariant to it.
# Leaving it off removes the confound the brief warns about instead of pinning
# it.  (MEASURED, separately: on the --srgb path --exposure is very nearly a
# no-op anyway, because the auto-tone's black and white points scale with it --
# 2.34 EV gave black 0.02520/white 1.01550 and 1.34 EV gave 0.01260/0.50775,
# exactly halved.  See test_instrument.py.)
#
# RULE 47 RECORD ------------------------------------------------------------
#   binary     C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#              sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#              built at 740e7056 -- the commit that flipped STREHL_FULLRES_GATHER
#              on by default.  ONE binary for both arms: the g0/g1 difference is
#              the env var and nothing else.
#   subcommand stack
#   flags      --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic
#              (--merge pyramid is also the default; passed so the record
#               survives the default moving)
#   NOT passed --srgb, --binned, --exposure, --auto-exposure, --limit,
#              --resampler (the sidecar's recorded resampler wins anyway --
#              catmull-rom), --photometric (default on), --focus-seam
#   env set    STREHL_FULLRES_GATHER = 0 or 1   <-- THE VARIABLE
#              STREHL_WARPMAP        = the pre-solved sidecar for that frame set
#   env cleared by name before every render: see $clear below.
#
# The warpmap is pinned because the align solve is where geometry is decided,
# and geometry must be IDENTICAL between the g0 and g1 arms or the comparison
# is between two rasters rather than between two gather kernels.  The digest in
# the sidecar is enforced by the tool (warpmap.rs:108), so each frame set needs
# its own solve and no solve can be silently reused across sets.

$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$out  = 'C:\dev\strehl-out\V-H2H2'
$ren  = "$out\lin"
$logs = "$out\logs"
New-Item -ItemType Directory -Force -Path $ren  | Out-Null

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER')

function Render($tag, $src, $map, $gather) {
  $dst = "$ren\$tag.tiff"
  $log = "$logs\lin-$tag.log"
  if (Test-Path $dst) { Write-Host "  $tag exists, skipped"; return }
  foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:STREHL_FULLRES_GATHER = $gather
  $env:STREHL_WARPMAP = $map
  $t0 = Get-Date
  & cmd /c exit 0
  & $exe stack $src --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File -FilePath $log -Encoding utf8
  $code = $LASTEXITCODE
  $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  $len = if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }
  $wrote = (Select-String -Path $log -Pattern '^wrote' | ForEach-Object { $_.Line.Trim() }) -join ' '
  Write-Host ("  {0} exit={1} {2}s bytes={3}" -f $tag, $code, $dt, $len)
  Write-Host ("      {0}" -f $wrote)
  if ($code -ne 0) { throw "$tag failed with exit $code" }
}

# frame-set roots, established in render_all.ps1
$sets = @(
  @{ tag='113-full'; src='D:\personal\macro\113MSDCF';        map="$out\warpmaps\113MSDCF.warpmap.txt" },
  @{ tag='113-A';    src="$out\halves\113-A";                 map="$out\warpmaps\113-A.warpmap.txt" },
  @{ tag='113-B';    src="$out\halves\113-B";                 map="$out\warpmaps\113-B.warpmap.txt" },
  @{ tag='cb-full';  src='D:\personal\macro\coffee-bean';     map="$out\warpmaps\coffee-bean.warpmap.txt" },
  @{ tag='cb-A';     src="$out\halves\cb-A";                  map="$out\warpmaps\cb-A.warpmap.txt" },
  @{ tag='cb-B';     src="$out\halves\cb-B";                  map="$out\warpmaps\cb-B.warpmap.txt" }
)

foreach ($s in $sets) {
  if (-not (Test-Path $s.src)) { throw ("missing frame set " + $s.src) }
  if (-not (Test-Path $s.map)) { throw ("missing warpmap "   + $s.map) }
  foreach ($g in @('0','1')) {
    Render ("{0}-g{1}" -f $s.tag, $g) $s.src $s.map $g
  }
}
Write-Host "ALL LINEAR-SRGB RENDERS DONE"
