# V-NOISE2 / run_subject.ps1 -- build every arm for ONE subject.
#
# PREREGISTRATION.md sec.2 fixes this pipeline.  It is M127's, unchanged, with
# the subject as a parameter.  Nothing here chooses or tunes anything: it
# develops, aligns, fuses and stacks, and every statistic is computed later by
# a separate script that reads only the outputs.
#
# THE ORDER MATTERS AND IS run_coh.ps1's CORRECTION.  align_image_stack is run
# ONCE over all N developed frames, and the comparator halves are fused from
# EVEN/ODD SUBSETS OF THAT ONE ALIGNED SET.  Aligning the halves separately
# would anchor them on different reference frames at different magnification --
# measured in run_coh.ps1 as three different rasters, 4613x6919 / 4619x6927 /
# 4614x6921 -- and a half-difference between two rasters that disagree by
# several pixels measures misregistration, not noise.  That error runs IN
# STREHL'S FAVOUR, which is the direction this lane exists to guard against.
#
# THE SPLIT, identical on both arms by construction:
#   A = frames at EVEN index (0,2,4,...)   B = frames at ODD index (1,3,5,...)
# align_image_stack is given --use-given-order, so al_0000 is frames[0] and the
# same parity selects the same exposures on the comparator side.
#
# RULE 47 RECORD ------------------------------------------------------------
#   binary   C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#            sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#            VERIFIED by Get-FileHash before this script was written.
#   develop  stack <one-frame-dir> --out <tif> --merge pyramid --pyramid-gate 4.5
#            --linear-srgb --demosaic       env STREHL_ALIGN=0 STREHL_FULLRES_GATHER=1
#   halves   strehl align <halfdir> --out <map>          (no other flags)
#            strehl stack <halfdir> --out <tiff> --merge pyramid --pyramid-gate 4.5
#            --linear-srgb --demosaic       env STREHL_WARPMAP=<map> STREHL_FULLRES_GATHER=1
#   aligned  align_image_stack -l -m -C --use-given-order -a al_
#   enfuse   enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1
#            --hard-mask
#   fs       focus-stack --no-align
#   NOT passed to strehl: --srgb --binned --exposure --auto-exposure --limit
#            --resampler --gate --stats --focus-seam
#
#   D:\ IS READ-ONLY.  Every frame is COPIED to C:\dev\strehl-out\V-NOISE2\ and
#   the copy is what is decoded.
#
# USAGE
#   .\run_subject.ps1 -Key 119 -Src D:\personal\macro\119MSDCF
#   .\run_subject.ps1 -Key bee -Src D:\personal\macro\bee-1-cpl -Stride 1
#
# -Stride is the PRE-REGISTERED uniform-subsample deviation (sec.2).  It is
# applied IDENTICALLY to all three arms, so it cannot bias a ratio between
# them; it changes the absolute noise level and is reported when != 1.
#
# -Tdist is align_image_stack's control-point pruning distance (Hugin's -t,
# default 3).  MEASURED NEED: on `fba` (205 frames) the default aborted after
# 308s with "After control points pruning reference images has no control
# points ... Increase error distance (-t parameter)" and produced 0 of 205
# files.  It is a PRUNING parameter -- it changes which control points are
# discarded as outliers, applied to every frame alike -- so it cannot prefer an
# arm, but a looser prune could leave a worse alignment, and a worse alignment
# degrades the COMPARATORS only (strehl aligns itself).  That error runs in
# strehl's favour, so it must be checked, not assumed: the integer-shift search
# in hd2.py is the diagnostic.  On 113 and 119 it moved strehl by -15.5% and
# the comparators by +0.2%, i.e. it found nothing left to fix on an arm that
# align_image_stack had already registered.  If it moves the comparators on a
# subject built with a raised -t, that subject's alignment is suspect and the
# subject is reported as such.  Any value != 3 is reported per subject.
# Resumable: every step skips if its output already exists.

param(
  [Parameter(Mandatory=$true)][string]$Key,
  [Parameter(Mandatory=$true)][string]$Src,
  [int]$Stride = 1,
  [int]$Tdist = 3
)

$ErrorActionPreference = 'Stop'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$hb   = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'
$fsUp = 'C:\dev\macro\tools\focus-stack\focus-stack\focus-stack.exe'
$root = "C:\dev\strehl-out\V-NOISE2\$Key"

$lin  = "$root\lintiff"
$ali  = "$root\aligned"
$arm  = "$root\arms"
$logs = "$root\logs"
$wrk  = "$root\work"
foreach ($d in $lin,$ali,$arm,$logs,$wrk) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER','STREHL_FIX_HALO',
           'STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE','STREHL_COVER',
           'STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR')
function ClearEnv { foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue } }

# ---------------------------------------------------------------- frame list
$all = Get-ChildItem $Src -File -Filter *.ARW | Sort-Object Name
if ($all.Count -eq 0) { throw "no ARW under $Src" }
$frames = @()
for ($i = 0; $i -lt $all.Count; $i += $Stride) { $frames += $all[$i] }
Say ("$Key : $($all.Count) ARW in source, stride $Stride -> $($frames.Count) frames used")
$free = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Say ("free on C: $free GB;  projected lintiff+aligned = " +
     [math]::Round($frames.Count * 197798923.0 * 2 / 1GB, 1) + " GB")

# ------------------------------------------------------------- 1. develops
# SIZE CHECK.  The first develop of THIS subject fixes the expected byte size
# and every later frame must match it.  It is not a hard constant: subjects
# differ in sensor raster (119MSDCF develops to 197798923 bytes,
# flower-bud-alone-cpl to 198023947), and a constant copied from one subject
# rejects another for being a different camera mode rather than for being
# broken.  What must hold is that the frames WITHIN a stack agree, because a
# stack of mixed rasters is the actual failure this guard is for.
$expect = 0
$n = 0
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
  ClearEnv
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_ALIGN = '0'
  & $exe stack $one --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File "$logs\dev-$stem.log" -Encoding utf8
  if ($LASTEXITCODE -ne 0) { throw "develop $stem exit $LASTEXITCODE" }
  $len = (Get-Item $dst).Length
  if ($expect -eq 0) { $expect = $len; Say "  frame size for $Key fixed at $expect bytes" }
  elseif ($len -ne $expect) { throw "develop $stem wrote $len bytes, expected $expect (mixed raster in stack)" }
  if ($n % 25 -eq 0) { Say ("  developed $n/$($frames.Count)") }
}
Say ("develops done: " + (Get-ChildItem "$lin\*.tif").Count + " files")

# --------------------------------------------- 2. strehl halves, from the RAW
for ($p = 0; $p -lt 2; $p++) {
  $tag = @('A','B')[$p]
  $hd  = "$wrk\half-$tag"
  New-Item -ItemType Directory -Force -Path $hd | Out-Null
  $cnt = 0
  for ($i = $p; $i -lt $frames.Count; $i += 2) {
    $d = "$hd\$($frames[$i].Name)"
    if (-not (Test-Path $d) -or (Get-Item $d).Length -ne $frames[$i].Length) {
      Copy-Item $frames[$i].FullName $d -Force
    }
    $cnt++
  }
  $dst = "$arm\strehl-$tag.tiff"
  if (Test-Path $dst) { Say "strehl-$tag exists, skipped"; continue }
  $map = "$root\$Key-$tag.warpmap.txt"
  if (-not (Test-Path $map)) {
    Say "strehl align $tag ($cnt frames)"
    ClearEnv
    & $exe align $hd --out $map 2>&1 | Out-File "$logs\align-$tag.log" -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "strehl align $tag exit $LASTEXITCODE" }
  }
  Say "strehl stack $tag"
  ClearEnv
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_WARPMAP = $map
  $t0 = Get-Date
  & $exe stack $hd --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File "$logs\stack-$tag.log" -Encoding utf8
  if ($LASTEXITCODE -ne 0) { throw "strehl stack $tag exit $LASTEXITCODE" }
  Say ("  strehl-$tag {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
}
ClearEnv

# ------------------------------------------------- 3. ONE shared-raster align
$need = $frames.Count
$have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
if ($have -ne $need) {
  Say "align_image_stack over all $need developed frames (this is the slow step)"
  Remove-Item "$ali\al_*.tif" -Force -ErrorAction SilentlyContinue
  $inp = $frames | ForEach-Object { "$lin\" + [IO.Path]::GetFileNameWithoutExtension($_.Name) + ".tif" }
  $t0 = Get-Date
  & "$hb\align_image_stack.exe" -l -m -C -t $Tdist --use-given-order -a "$ali\al_" @inp 2>&1 |
      Out-File "$logs\ais.log" -Encoding utf8
  $c = $LASTEXITCODE
  $have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
  Say ("  align_image_stack -t $Tdist exit=$c {0}s -> $have files" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
  if ($have -ne $need) { throw "align_image_stack produced $have of $need" }
} else { Say "aligned set exists ($have files), skipped" }

$alist = Get-ChildItem "$ali\al_*.tif" | Sort-Object Name | ForEach-Object FullName
$idx = 0..($alist.Count - 1)
$sets = @{
  A = @($idx | Where-Object { $_ % 2 -eq 0 } | ForEach-Object { $alist[$_] })
  B = @($idx | Where-Object { $_ % 2 -eq 1 } | ForEach-Object { $alist[$_] })
}

# ------------------------------------------------------------- 4. enfuse
foreach ($k in 'A','B') {
  $dst = "$arm\coh-enfuse-$k.tif"
  if (Test-Path $dst) { Say "coh-enfuse-$k exists, skipped"; continue }
  Say "coh-enfuse-$k ($($sets[$k].Count) frames)"
  $t0 = Get-Date
  & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 `
      --hard-mask --output=$dst @($sets[$k]) 2>&1 |
      Out-File "$logs\coh-enfuse-$k.log" -Encoding utf8
  Say ("  exit=$LASTEXITCODE {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

# ---------------------------------------------------------- 5. focus-stack
foreach ($k in 'A','B') {
  $dst = "$arm\coh-fs15-$k.tif"
  if (Test-Path $dst) { Say "coh-fs15-$k exists, skipped"; continue }
  Say "coh-fs15-$k ($($sets[$k].Count) frames)"
  $t0 = Get-Date
  & $fsUp --no-align "--output=$dst" @($sets[$k]) 2>&1 |
      Out-File "$logs\coh-fs15-$k.log" -Encoding utf8
  Say ("  exit=$LASTEXITCODE {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

Say "SUBJECT $Key DONE"
Get-ChildItem $arm | Select-Object Name, Length
