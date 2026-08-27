# V-NOISE2 / ladder_build.ps1 -- build ONE rung of the M115 frame-count ladder.
#
# PREREGISTRATION.md sec.11 fixes this design and was committed (7497c353)
# before this file existed.  Nothing here computes a statistic; it only builds
# arms, and incoh.py reads them later.
#
# WHY THIS IS NOT run_subject.ps1 -Stride N.
# run_subject.ps1 re-runs align_image_stack whenever the frame count changes
# ($need -ne $have wipes al_*.tif).  Doing that per rung would (a) destroy the
# existing 299-frame aligned set, and (b) let ALIGNMENT QUALITY vary with N,
# which is precisely the confound that would manufacture ORCH's predicted
# result out of nothing.  The mechanism under test is a claim about the MERGE,
# so the merge is the only thing allowed to vary.
#
# THE ALIGNED SET IS THEREFORE SHARED AND READ-ONLY HERE.  bee's al_0000..0298
# were produced by ONE align_image_stack run over all 299 developed frames.
# al_NNNN corresponds to frames[NNNN] because that run was given
# --use-given-order.  Every rung subsamples THAT set by index; no rung realigns.
#
# INDEXING, which must match run_subject.ps1 exactly or the rungs are not
# comparable with sec.9.  With stride s over the ordered frame list:
#     subsampled = all[0], all[s], all[2s], ...
#     A = even POSITIONS of the subsampled list = all[0], all[2s], all[4s], ...
#     B = odd  POSITIONS                        = all[s], all[3s], all[5s], ...
# The parity split is applied AFTER the subsample, as run_subject.ps1 does.
#
# BINARY.  Pin 9b05d0b7 (sha16 44C2F2CD2E5B2894) per ORCH, verified below
# before use.  bee's existing strehl arms were built with 740e7056; reusing
# them for the N=299 rung would confound binary with N, so that rung's strehl
# arms are rebuilt here.  enfuse does not involve the strehl binary, so its
# existing N=299 outputs are reused unchanged.
#
# D:\ IS READ-ONLY.  Frames are COPIED to C: and the copy is decoded.

param(
  [Parameter(Mandatory=$true)][int]$Stride,
  [Parameter(Mandatory=$true)][string]$Rung,
  [int]$BOffset = -1,
  [string]$Src  = 'D:\personal\macro\bee-1-cpl',
  [string]$Base = 'C:\dev\strehl-out\V-NOISE2\bee',
  [switch]$KeepHalves
)

$ErrorActionPreference = 'Stop'

# strehl.exe and enfuse write INFORMATIONAL lines to stderr ("align: track
# prior on, lambda=1 huber=Some(1.0) px").  Under $ErrorActionPreference =
# 'Stop', PowerShell turns native stderr inside a redirected pipeline into a
# TERMINATING error, so a healthy run aborts on a log line.  That is a FALSE
# error and it killed two rung builds.  The real health check is the exit
# code, which is still enforced here; only the false one is removed.
function Native([scriptblock]$sb, [string]$what) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & $sb } finally { $ErrorActionPreference = $old }
  if ($LASTEXITCODE -ne 0) { throw "$what exit $LASTEXITCODE" }
}

$exe = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$hb  = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'

# RULE 47: the pin is verified here, not trusted from a path string.  ORCH
# warns that PIN-V3\strehl.exe is mislabelled, so the check is on content.
$want = '44C2F2CD2E5B2894'
$got  = (Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0,16)
if ($got -ne $want) { throw "pin mismatch: expected $want got $got" }

$root = "C:\dev\strehl-out\V-NOISE2\bee-$Rung"
$arm  = "$root\arms"
$logs = "$root\logs"
$wrk  = "$root\work"
foreach ($d in $arm,$logs,$wrk) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

$lock = "$root\.build.lock"
if (Test-Path $lock) {
  $old = (Get-Content $lock -First 1 -ErrorAction SilentlyContinue) -as [int]
  if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
    throw "another instance (pid $old) is building '$Rung'"
  }
  Remove-Item $lock -Force
}
"$PID" | Out-File $lock -Encoding ascii

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER','STREHL_FIX_HALO',
           'STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE','STREHL_COVER',
           'STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR')
function ClearEnv { foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue } }

# ------------------------------------------------------------ frame indexing
$all = Get-ChildItem $Src -File -Filter *.ARW | Sort-Object Name
if ($all.Count -eq 0) { throw "no ARW under $Src" }
$sub = @()
for ($i = 0; $i -lt $all.Count; $i += $Stride) { $sub += $i }
Say "$Rung : stride $Stride -> N = $($sub.Count) of $($all.Count)"

$alist = Get-ChildItem "$Base\aligned\al_*.tif" | Sort-Object Name | ForEach-Object FullName
if ($alist.Count -ne $all.Count) {
  throw "aligned set has $($alist.Count) files but source has $($all.Count) ARW -- index mapping would be wrong"
}

# Parity AFTER subsample, matching run_subject.ps1.
#
# -BOffset EXISTS TO KILL A CONFOUND THIS LADDER DISCOVERED IN ITSELF.
# With the default split, half-A takes even POSITIONS of the subsampled list
# and half-B the odd ones, so the two halves sample focus planes `Stride`
# frames apart: 9 apart at L1 but only 1 apart at L4.  That alone makes the
# halves disagree far more at low N, in the same direction as the effect under
# test, and it is not dilution.  MEASURED consequence at L1: FINE phi reached
# 1.003, i.e. P_d exceeded P_m and the halves shared NO coherent detail at
# 4-5 px at all.
#
# BOffset decouples the two.  Half-A is always all[0], all[2s], all[4s], ...;
# half-B is all[o], all[2s+o], ....  o = Stride reproduces the original split
# exactly (and is the default), while o = 1 holds N and the depth range fixed
# and makes the halves ADJACENT in focus.  L1 and L1P therefore share half-A
# frame for frame and differ only in how far half-B is displaced in focus.
if ($BOffset -lt 0) { $BOffset = $Stride }
$blk = 2 * $Stride
$idxA = @(); $idxB = @()
for ($i = 0; $i -lt $all.Count; $i += $blk) {
  $idxA += $i
  if (($i + $BOffset) -lt $all.Count) { $idxB += ($i + $BOffset) }
}
$n = $idxA.Count + $idxB.Count
Say "  BOffset $BOffset (halves sample focus planes $BOffset frame(s) apart)"
Say "  halves: A = $($idxA.Count) frames, B = $($idxB.Count) frames, N = $n"

$manifest = @{
  rung = $Rung; stride = $Stride; n = $n; boffset = $BOffset
  n_a = $idxA.Count; n_b = $idxB.Count
  pin = $want; src = $Src
  idx_a = $idxA; idx_b = $idxB
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content "$root\manifest.json" -Encoding utf8

# ------------------------------------------------ strehl halves, from the RAW
foreach ($t in @(@{tag='A';idx=$idxA}, @{tag='B';idx=$idxB})) {
  $tag = $t.tag
  $dst = "$arm\strehl-$tag.tiff"
  if (Test-Path $dst) { Say "strehl-$tag exists, skipped"; continue }
  $hd = "$wrk\half-$tag"
  New-Item -ItemType Directory -Force -Path $hd | Out-Null
  foreach ($i in $t.idx) {
    $f = $all[$i]
    $d = "$hd\$($f.Name)"
    if (-not (Test-Path $d) -or (Get-Item $d).Length -ne $f.Length) {
      Copy-Item $f.FullName $d -Force
    }
  }
  $have = (Get-ChildItem "$hd\*.ARW").Count
  if ($have -ne $t.idx.Count) { throw "half-$tag has $have frames, expected $($t.idx.Count)" }

  $map = "$root\$Rung-$tag.warpmap.txt"
  if (-not (Test-Path $map)) {
    Say "strehl align $tag ($have frames)"
    ClearEnv
    Native { & $exe align $hd --out $map 2>&1 |
      Out-File "$logs\align-$tag.log" -Encoding utf8 } "strehl align $tag"
  }
  Say "strehl stack $tag"
  ClearEnv
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_WARPMAP = $map
  $t0 = Get-Date
  Native { & $exe stack $hd --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 |
    Out-File "$logs\stack-$tag.log" -Encoding utf8 } "strehl stack $tag"
  Say ("  strehl-$tag {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
}
ClearEnv

# ------------------------------------------------------------------- enfuse
foreach ($t in @(@{tag='A';idx=$idxA}, @{tag='B';idx=$idxB})) {
  $tag = $t.tag
  $dst = "$arm\coh-enfuse-$tag.tif"
  if (Test-Path $dst) { Say "coh-enfuse-$tag exists, skipped"; continue }
  $inp = @($t.idx | ForEach-Object { $alist[$_] })
  Say "coh-enfuse-$tag ($($inp.Count) frames)"
  $t0 = Get-Date
  Native { & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 `
      --contrast-weight=1 --hard-mask -o $dst @inp 2>&1 |
    Out-File "$logs\coh-enfuse-$tag.log" -Encoding utf8 } "enfuse $tag"
  Say ("  coh-enfuse-$tag {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
}

if (-not $KeepHalves) {
  Remove-Item "$wrk\half-A","$wrk\half-B" -Recurse -Force -ErrorAction SilentlyContinue
  Say "half dirs removed (disk); pass -KeepHalves to retain"
}

Say "rung $Rung done"
Get-ChildItem $arm -File | Select-Object Name, Length | Format-Table -AutoSize
