# V-NOISE2 / bandgate_fuse.ps1 -- finish the leaf-2-cpl comparator leg ONLY.
#
# WHY THIS IS SEPARATE FROM bandgate_build.ps1.
# Mid-run, `target\release\strehl.exe` changed from 82EA1F96DA4550F6 to
# F1D66AD7220DCC6C: a build lane rebuilt the shared working tree while this
# lane was rendering.  bandgate_build.ps1's content check caught it and
# refused, which is the guard working.
#
# The four strehl arms are already rendered and are a CONSISTENT SET, all from
# 82EA1F96DA4550F6:
#     strehl-unset-A / strehl-coarse8-A / strehl-unset-B / strehl-coarse8-B
# and the treatment commissioning passed on that binary (ones byte-identical
# to unset, coarse8 differing).  What remains is the enfuse comparator, which
# is produced by Hugin's align_image_stack and enfuse and DOES NOT INVOKE
# STREHL AT ALL.  Its only strehl-derived input is the lintiff develop set,
# which was written by 82EA... and has not been touched since.
#
# So this script deliberately CANNOT re-render a strehl arm: it never calls the
# binary.  That keeps the arms on one binary without blocking on a rebuild that
# belongs to another lane.  It asserts the four arms and the develops exist and
# refuses if they do not.
#
# LESSON, and it is why the rest of this lane pins by content: a shared working
# tree's target\release\ binary is NOT stable for the duration of a long run.
# A lane that needs more renders later must copy the binary aside first.
#
# align_image_stack previously failed here at -t 3 with "After control points
# pruning reference images has no control points ... Increase error distance
# (-t parameter)".  Its own message names the fix; -Tdist is raised.

param(
  [string]$Key = 'leaf',
  [string]$Src = 'D:\personal\macro\leaf-2-cpl',
  [int]$Tdist  = 12
)

$ErrorActionPreference = 'Stop'

function Native([scriptblock]$sb, [string]$what) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & $sb } finally { $ErrorActionPreference = $old }
  if ($LASTEXITCODE -ne 0) { throw "$what exit $LASTEXITCODE" }
}

$hb   = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'
$root = "C:\dev\strehl-out\V-NOISE2\$Key"
$arm  = "$root\arms"; $logs = "$root\logs"
$lin  = "$root\lintiff"; $ali = "$root\aligned"

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

# the four arms must already exist; this script will not create them
foreach ($a in @('strehl-unset-A','strehl-coarse8-A','strehl-unset-B','strehl-coarse8-B')) {
  if (-not (Test-Path "$arm\$a.tiff")) { throw "missing arm $a -- render it with bandgate_build.ps1 on a pinned binary" }
}
Say "four strehl arms present (rendered by 82EA1F96DA4550F6)"

$frames = Get-ChildItem "$Src\*.ARW" | Sort-Object Name
$need = $frames.Count
$devs = (Get-ChildItem "$lin\*.tif" -ErrorAction SilentlyContinue).Count
if ($devs -ne $need) { throw "develops $devs != frames $need" }
Say "$devs develops present"
Say ("free on C: " + [math]::Round((Get-PSDrive C).Free/1GB,1) + " GB")

# ------------------------------------------------- ONE shared-raster align
$have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
if ($have -ne $need) {
  Say "align_image_stack -t $Tdist over all $need develops (the slow step)"
  Remove-Item "$ali\al_*.tif" -Force -ErrorAction SilentlyContinue
  $inp = $frames | ForEach-Object {
    "$lin\" + [IO.Path]::GetFileNameWithoutExtension($_.Name) + ".tif" }
  $t0 = Get-Date
  Native { & "$hb\align_image_stack.exe" -l -m -C -t $Tdist --use-given-order `
      -a "$ali\al_" @inp 2>&1 |
    Out-File "$logs\ais-t$Tdist.log" -Encoding utf8 } "align_image_stack"
  $have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
  Say ("  -t $Tdist {0}s -> $have files" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
  if ($have -ne $need) { throw "align_image_stack produced $have of $need" }
} else { Say "aligned set exists ($have files), skipped" }

# ------------------------------- enfuse halves, ONCE, shared by both arms
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
Say "$Key comparator leg done"
Get-ChildItem $arm | Select-Object Name,Length
