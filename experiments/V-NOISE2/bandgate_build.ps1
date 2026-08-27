# V-NOISE2 / bandgate_build.ps1 -- build the half-stacks needed to score ORCH's
# per-band gate-floor knob with sec.9's R.
#
# WHY THIS EXISTS RATHER THAN SCORING ORCH'S TWO MASTERS DIRECTLY.
# ORCH offered A-unset.tiff and C-coarse8.tiff and asked whether the split-half
# construction needs its own renders.  IT DOES.  R = phi_strehl / phi_enfuse
# and phi = P_d/P_m is computed from the difference between TWO INDEPENDENT
# HALF-STACKS of the SAME arm.  A-unset and C-coarse8 are single full-stack
# masters that differ by the TREATMENT, so their difference is the knob's
# effect, not a noise realisation.  Feeding them to incoh.py would measure the
# knob against itself and would not be a phi at all.  So each arm gets its own
# A/B halves here.
#
# WHAT IS HELD IDENTICAL BETWEEN THE TWO ARMS, so the knob is the only variable:
#   * the frames in each half (same even/odd split of the same ordered list)
#   * the WARPMAP -- computed once per half and reused by both arms, so the two
#     arms are not separated by an alignment difference
#   * the binary, the recipe, and the develop step
#   * the enfuse comparator, which does not depend on the knob and is therefore
#     rendered ONCE and shared as the denominator of both arms' R
#
# COMMISSIONING OF THE TREATMENT ITSELF, on half A, before any statistic.
# If the env var silently failed to reach the binary, unset and coarse8 would
# be identical and R would read "unmoved" -- a FALSE NEGATIVE that would tell
# ORCH to stop building the right thing.  So two arms are asserted here:
#   ONES  STREHL_GATE_FLOOR_SCALE=1,1,1,1,1,1,1  MUST be byte-identical to unset
#         (the knob is wired and is neutral at identity)
#   C8    STREHL_GATE_FLOOR_SCALE=1,8,8,8,8,8,8  MUST DIFFER from unset
#         (the knob actually bites)
# Failing either is a hard stop.  This reproduces ORCH's own commissioning
# inside MY harness rather than inheriting it.
#
# BINARY: HEAD, per discipline 34.  Anything at or before 9b05d0b7 is stale.
# D:\ IS READ-ONLY.  Frames are COPIED to C: and the copy is decoded.

param(
  [string]$Key  = 'leaf',
  [string]$Src  = 'D:\personal\macro\leaf-2-cpl',
  [int]$Tdist   = 3
)

$ErrorActionPreference = 'Stop'

# strehl and enfuse write informational lines to stderr; under 'Stop' those
# become terminating errors inside a redirected pipeline and kill a healthy
# run.  The exit code is the real check and is still enforced.
function Native([scriptblock]$sb, [string]$what) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & $sb } finally { $ErrorActionPreference = $old }
  if ($LASTEXITCODE -ne 0) { throw "$what exit $LASTEXITCODE" }
}

$repo = 'C:\dev\blog\death-of-software\projects\strehl'
$exe  = "$repo\target\release\strehl.exe"
$hb   = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'

# RULE 47: the binary is verified by CONTENT, not trusted from a path.
$want = '82EA1F96DA4550F6'
$got  = (Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0,16)
if ($got -ne $want) { throw "binary mismatch: expected HEAD $want got $got" }

$root = "C:\dev\strehl-out\V-NOISE2\$Key"
$arm  = "$root\arms"; $logs = "$root\logs"; $wrk = "$root\work"
$lin  = "$root\lintiff"; $ali = "$root\aligned"
foreach ($d in @($root,$arm,$logs,$wrk,$lin,$ali)) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }
function ClearEnv {
  foreach ($v in @('STREHL_FULLRES_GATHER','STREHL_ALIGN','STREHL_WARPMAP',
                   'STREHL_GATE_FLOOR_SCALE')) {
    Remove-Item "env:$v" -ErrorAction SilentlyContinue
  }
}

# The two treatment arms.  '' means the env var is not set at all.
$ARMS = @(
  @{ tag = 'unset';   scale = '' },
  @{ tag = 'coarse8'; scale = '1,8,8,8,8,8,8' }
)

$frames = Get-ChildItem "$Src\*.ARW" | Sort-Object Name
if ($frames.Count -lt 2) { throw "no frames under $Src" }
Say "$Key : $($frames.Count) frames; binary sha16 $got (HEAD)"
$free = [math]::Round((Get-PSDrive C).Free/1GB,1)
Say "free on C: $free GB"

# ------------------------------------------------------------- 1. develops
$expect = 0; $n = 0
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
  Native { & $exe stack $one --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 |
    Out-File "$logs\dev-$stem.log" -Encoding utf8 } "develop $stem"
  $len = (Get-Item $dst).Length
  if ($expect -eq 0) { $expect = $len; Say "  frame size fixed at $expect bytes" }
  elseif ($len -ne $expect) {
    throw "develop $stem wrote $len bytes, expected $expect (mixed raster)"
  }
  if ($n % 25 -eq 0) { Say "  developed $n/$($frames.Count)" }
}
ClearEnv
Say ("develops done: " + (Get-ChildItem "$lin\*.tif").Count + " files")

# ------------------------------------ 2. strehl halves, BOTH arms, shared warpmap
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
  # ONE warpmap per half, reused by every arm: the arms must not differ by
  # alignment.
  $map = "$root\$Key-$tag.warpmap.txt"
  if (-not (Test-Path $map)) {
    Say "strehl align $tag ($cnt frames)"
    ClearEnv
    Native { & $exe align $hd --out $map 2>&1 |
      Out-File "$logs\align-$tag.log" -Encoding utf8 } "strehl align $tag"
  }
  foreach ($a in $ARMS) {
    $dst = "$arm\strehl-$($a.tag)-$tag.tiff"
    if (Test-Path $dst) { Say "strehl-$($a.tag)-$tag exists, skipped"; continue }
    Say "strehl stack $tag  arm=$($a.tag)"
    ClearEnv
    $env:STREHL_FULLRES_GATHER = '1'
    $env:STREHL_WARPMAP = $map
    if ($a.scale -ne '') { $env:STREHL_GATE_FLOOR_SCALE = $a.scale }
    $t0 = Get-Date
    Native { & $exe stack $hd --out $dst --merge pyramid --pyramid-gate 4.5 `
          --linear-srgb --demosaic 2>&1 |
      Out-File "$logs\stack-$($a.tag)-$tag.log" -Encoding utf8 } "stack $tag $($a.tag)"
    Say ("  strehl-$($a.tag)-$tag {0}s bytes={1}" -f `
         [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
  }
  # ---- commissioning of the treatment, on half A only ----
  if ($tag -eq 'A') {
    $ones = "$arm\strehl-ones-A.tiff"
    if (-not (Test-Path $ones)) {
      Say "COMMISSIONING: strehl stack A  arm=ones (1,1,1,1,1,1,1)"
      ClearEnv
      $env:STREHL_FULLRES_GATHER = '1'
      $env:STREHL_WARPMAP = $map
      $env:STREHL_GATE_FLOOR_SCALE = '1,1,1,1,1,1,1'
      Native { & $exe stack $hd --out $ones --merge pyramid --pyramid-gate 4.5 `
            --linear-srgb --demosaic 2>&1 |
        Out-File "$logs\stack-ones-A.log" -Encoding utf8 } "stack A ones"
    }
    ClearEnv
    $hU = (Get-FileHash "$arm\strehl-unset-A.tiff"   -Algorithm SHA256).Hash
    $hO = (Get-FileHash $ones                         -Algorithm SHA256).Hash
    $hC = (Get-FileHash "$arm\strehl-coarse8-A.tiff" -Algorithm SHA256).Hash
    Say "  unset   sha16 $($hU.Substring(0,16))"
    Say "  ones    sha16 $($hO.Substring(0,16))"
    Say "  coarse8 sha16 $($hC.Substring(0,16))"
    if ($hO -ne $hU) {
      throw "COMMISSIONING FAILED: ones is NOT byte-identical to unset -- the knob is not neutral at identity, so nothing downstream is interpretable"
    }
    if ($hC -eq $hU) {
      throw "COMMISSIONING FAILED: coarse8 is byte-identical to unset -- the env var never reached the binary, so a null R would be a FALSE NEGATIVE"
    }
    Say "  COMMISSIONING PASSED: ones == unset (wired, neutral) and coarse8 != unset (bites)"
  }
}
ClearEnv

# ------------------------------------------------- 3. ONE shared-raster align
$need = $frames.Count
$have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
if ($have -ne $need) {
  Say "align_image_stack over all $need developed frames (the slow step)"
  Remove-Item "$ali\al_*.tif" -Force -ErrorAction SilentlyContinue
  $inp = $frames | ForEach-Object {
    "$lin\" + [IO.Path]::GetFileNameWithoutExtension($_.Name) + ".tif" }
  $t0 = Get-Date
  Native { & "$hb\align_image_stack.exe" -l -m -C -t $Tdist --use-given-order `
      -a "$ali\al_" @inp 2>&1 |
    Out-File "$logs\ais.log" -Encoding utf8 } "align_image_stack"
  $have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
  Say ("  align_image_stack -t $Tdist {0}s -> $have files" -f `
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
  if ($have -ne $need) { throw "align_image_stack produced $have of $need" }
} else { Say "aligned set exists ($have files), skipped" }

# ------------------------------- 4. enfuse halves, ONCE, shared by both arms
$alist = Get-ChildItem "$ali\al_*.tif" | Sort-Object Name | ForEach-Object FullName
for ($p = 0; $p -lt 2; $p++) {
  $tag = @('A','B')[$p]
  $dst = "$arm\coh-enfuse-$tag.tif"
  if (Test-Path $dst) { Say "coh-enfuse-$tag exists, skipped"; continue }
  $inp = @()
  for ($i = $p; $i -lt $alist.Count; $i += 2) { $inp += $alist[$i] }
  Say "coh-enfuse-$tag ($($inp.Count) frames)"
  $t0 = Get-Date
  Native { & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 `
      --contrast-weight=1 --hard-mask -o $dst @inp 2>&1 |
    Out-File "$logs\coh-enfuse-$tag.log" -Encoding utf8 } "enfuse $tag"
  Say ("  coh-enfuse-$tag {0}s bytes={1}" -f `
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
}

$man = @{
  key = $Key; src = $Src; n = $frames.Count; binary_sha16 = $got
  arms = @($ARMS | ForEach-Object { $_.tag })
  gate_floor_scale = @{ unset = ''; coarse8 = '1,8,8,8,8,8,8' }
  tdist = $Tdist
}
$man | ConvertTo-Json -Depth 5 | Out-File "$root\manifest.json" -Encoding utf8
Say "$Key done"
Get-ChildItem $arm | Select-Object Name,Length
