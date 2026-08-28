# r2_develop.ps1 -- linear per-frame develops for the round-2 band-qualification
# subjects (docs/research/V-LINEAR-BANDS.md section 9).
#
# WHAT THIS IS.  bandsignal.py measures a property of the SOURCE FRAMES -- the
# ratio of in-focus to defocused band power -- so what it needs is a set of
# per-frame linear develops, not a stack.  Every frame is developed on its own
# with STREHL_ALIGN=0, which is why this script never merges anything and never
# produces an arm.  Nothing here is a quality measurement of strehl and no
# number out of it should be read as one.
#
# THE DEVELOP INVOCATION IS COPIED, NOT INVENTED.  It is the one used by
# experiments/V-NOISE2/run_subject.ps1 for the round-1 subjects:
#
#   strehl stack <one-frame-dir> --out <dst> --merge pyramid --pyramid-gate 4.5
#          --linear-srgb --demosaic          with STREHL_FULLRES_GATHER=1, ALIGN=0
#
# --demosaic must be explicit or the output is binned to half raster.  There is
# deliberately no --srgb, no --exposure and no --auto-exposure: ORCH's exposure
# regression at HEAD double-applies normalisation under --auto-exposure and
# blows highlights, and a clipped frame has no structure for a band ratio to
# measure.  This lane is case 3 of that broadcast -- rendered at a pinned
# binary, without --auto-exposure.
#
# WHICH BINARY, AND WHY IT WAS MEASURED RATHER THAN ASSUMED.  Round-1 develops
# were written by an older binary; the working tree today is d35f905533e2-DIRTY
# (another lane's uncommitted changes).  Comparing round-2 subjects against the
# round-1 table is only legitimate if the develop path did not move.  So it was
# tested rather than argued: leaf-2-cpl/DSC00001.ARW was developed by the pin
# 740e7056 (15EA73461905EA2D) and by dirty HEAD (F1D66AD7220DCC6C) and both were
# compared against the round-1 develop already on disk.  All three decode to
# BIT-IDENTICAL arrays -- 0 differing pixels of 99,010,560 (4688x7040x3),
# maxabs 0, all three means 2104.1348.
#
# Note the trap that measurement stepped over: the three files have three
# DIFFERENT byte lengths (198023952 / 198023947 / 198023958).  A file-hash
# comparison would have reported three different develops and the wrong
# conclusion that the binary matters.  The difference is TIFF metadata.  This is
# why the house rule is to compare decoded arrays and never file hashes.
#
# The pin is used anyway, for the reason that it CANNOT MOVE.  Dirty HEAD is
# equivalent today but belongs to another lane, which may rebuild it mid-run;
# an immutable input is worth 2.2 s/frame.
#
# DECIMATION.  -Stride k develops every k-th ARW.  A 299-frame subject at
# stride 4 costs 75 develops instead of 299, and the sweep would itself have
# sub-sampled to ~80 reads anyway, so the stride throws away frames the
# measurement was never going to look at.  bandsweep.py --decim k is then told
# the on-disk set is every k-th frame of a k-times longer stack so that the
# `far` defocus offset stays in REAL frame units.  That protocol was
# commissioned digit-exactly -- see bandsweep.py's header.
#
# READ-ONLY: D:\personal\macro is never written.  Outputs go under
# C:\dev\strehl-out\V-LINEAR\r2\<Key>\lintiff.

param(
  [Parameter(Mandatory=$true)][string]$Key,
  [int]$Stride = 1,
  [string]$Exe = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe',
  # DISK.  Heavy output goes to D: per ORCH's disk broadcast -- C: hit 4.4% free
  # while this lane was running.  D:\personal\macro and D:\macro-dark-frames are
  # READ-ONLY source data; this writes to its own directory at the D: root.
  # Subjects developed to C: before the broadcast (112MSDCF, flat-on-ruler-cpl,
  # tweezers-cpl) keep their C: paths in bandsweep.SUBJECTS, because the develops
  # are BIT-IDENTICAL wherever they are written -- the drive is not a variable
  # the measurement can see.
  [string]$Root = 'D:\strehl-out\V-LINEAR\r2'
)

$ErrorActionPreference = 'Stop'

$src  = "D:\personal\macro\$Key"
$root = "$Root\$Key"
$lin  = "$root\lintiff"
$wrk  = "$root\work"
$logs = "$root\logs"

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

if (-not (Test-Path $src)) { throw "no such subject: $src" }
if (-not (Test-Path $Exe)) { throw "no such binary: $Exe" }
New-Item -ItemType Directory -Force -Path $lin, $wrk, $logs | Out-Null

$sha = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0,16)
Say "binary $Exe"
Say "  sha16 $sha"

# ---------------------------------------------------------------- frame list
$all = Get-ChildItem $src -File -Filter *.ARW | Sort-Object Name
if ($all.Count -eq 0) { throw "no ARW under $src" }
$frames = @()
for ($i = 0; $i -lt $all.Count; $i += $Stride) { $frames += $all[$i] }
Say ("$Key : $($all.Count) ARW in source, stride $Stride -> $($frames.Count) develops")

# ---------------------------------------------------------------- disk guard
# Refuse up front rather than dying at frame 60 with a half-written set.  198 MB
# is the observed develop size; 15 GB of headroom is left for other lanes.
$need = $frames.Count * 198MB
$drv  = (Split-Path -Qualifier $lin).TrimEnd(':')
$free = (Get-PSDrive $drv).Free
Say ("free on ${drv}: {0:N1} GB;  this subject needs {1:N1} GB" -f ($free/1GB), ($need/1GB))
if ($free - $need -lt 15GB) {
  throw ("refusing to start: {0:N1} GB free on ${drv}, need {1:N1} GB, would leave under 15 GB" -f ($free/1GB), ($need/1GB))
}

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER','STREHL_FIX_HALO',
           'STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE','STREHL_COVER',
           'STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR')

# ------------------------------------------------------------------ develops
# SIZE CHECK.  The first develop fixes the expected byte length and every later
# frame must match it.  It is not a constant across subjects (different sensor
# rasters give different lengths); what must hold is that frames WITHIN one
# stack agree, because a stack of mixed rasters is the failure this guards.
$expect = 0
$n = 0
$made = 0
$t0 = Get-Date
foreach ($f in $frames) {
  $n++
  $stem = [IO.Path]::GetFileNameWithoutExtension($f.Name)
  $dst  = "$lin\$stem.tif"
  if ((Test-Path $dst) -and ($expect -eq 0 -or (Get-Item $dst).Length -eq $expect)) {
    if ($expect -eq 0) { $expect = (Get-Item $dst).Length }
    continue
  }
  $one = "$wrk\dev1"
  Remove-Item "$one\*" -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $one | Out-Null
  Copy-Item $f.FullName "$one\$($f.Name)" -Force
  foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_ALIGN = '0'
  # The pin writes its build banner to stderr, and Windows PowerShell turns any
  # native stderr into a terminating NativeCommandError while $ErrorActionPreference
  # is 'Stop'.  Exit code is the authoritative success signal and is checked
  # immediately below, so the preference is relaxed only across the call itself.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $Exe stack $one --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File "$logs\dev-$stem.log" -Encoding utf8
  $rc = $LASTEXITCODE
  $ErrorActionPreference = $prev
  if ($rc -ne 0) { throw "develop $stem exit $rc (see $logs\dev-$stem.log)" }
  $len = (Get-Item $dst).Length
  if ($expect -eq 0) { $expect = $len; Say "  frame size for $Key fixed at $expect bytes" }
  elseif ($len -ne $expect) { throw "develop $stem wrote $len bytes, expected $expect (mixed raster in stack)" }
  $made++
  if ($n % 20 -eq 0) {
    $el = (Get-Date) - $t0
    Say ("  {0}/{1}  ({2:N1} min elapsed, {3:N1} s/frame)" -f $n, $frames.Count, $el.TotalMinutes,
         $(if ($made) { $el.TotalSeconds / $made } else { 0 }))
  }
}
Remove-Item "$wrk\dev1\*" -Force -ErrorAction SilentlyContinue

$have = (Get-ChildItem "$lin\*.tif" -File)
Say ("develops done: {0} files, {1:N1} GB, {2} newly made" -f $have.Count, (($have | Measure-Object Length -Sum).Sum/1GB), $made)
if ($have.Count -ne $frames.Count) {
  throw "expected $($frames.Count) develops, found $($have.Count)"
}
Say "OK  $Key  stride=$Stride  binary=$sha"
