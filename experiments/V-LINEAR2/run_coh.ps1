# V-LINEAR2 / run_coh.ps1
#
# Builds the comparator half-stacks IN A SHARED RASTER, which run_halves.ps1
# did not, so that coherent power can actually be measured on the comparator
# arms instead of measuring their misregistration.
#
# THE ERROR THIS FILE CORRECTS, recorded rather than quietly fixed.
# run_halves.ps1 ran each comparator's WHOLE pipeline on half A and half B.
# Both align internally against a reference frame chosen from the frames they
# were given: align_image_stack anchors on the first image, focus-stack on the
# middle one by default (`--reference=0 ... default middle one`).  Half A and
# half B therefore anchor on DIFFERENT frames, at different focus, hence
# different magnification.  Measured proof, from the outputs it did produce:
#     focusstack-1.5-A.tif   4613 x 6919
#     focusstack-1.5-B.tif   4619 x 6927
#     focusstack-1.5.tif     4614 x 6921
# three different rasters.  A cross-spectrum between two rasters that disagree
# by several pixels is destroyed by the phase ramp -- at 0.22 cyc/px one pixel
# of residual shift is 1.4 rad -- so `Cn_comp` would have come out LOW for a
# reason that has nothing to do with noise.  That error runs IN STREHL'S
# FAVOUR, which is exactly the direction this lane exists to guard against.
#
# THE FIX.  align_image_stack has already been run ONCE over all 63 frames, to
# a single common raster, in run_free.ps1.  Fusing odd and even subsets OF THAT
# ALIGNED SET gives two outputs that are pixel-identical in geometry by
# construction, because neither enfuse nor `focus-stack --no-align` moves a
# pixel.  Nothing needs registering and nothing can be flattered by failing to.
#
# WHAT THIS CHANGES ABOUT WHAT IS BEING COMPARED, stated plainly:
#   * enfuse: nothing.  The primary enfuse arm in run_free.ps1 was ALREADY
#     built from these same aligned frames, so full/A/B are the same pipeline.
#   * focus-stack: this is a DIFFERENT arm from focusstack-1.5.tif, which used
#     focus-stack's own aligner.  Here it is Hugin's alignment plus
#     focus-stack's merge.  A matching full-stack output is therefore rebuilt
#     the same way (coh-fs15-full) so that full, A and B are one pipeline.
#     It is labelled separately and never conflated with the fs15 arm.
#
# THE SPLIT is V-HEADTOHEAD2's, verified by listing
# C:\dev\strehl-out\V-H2H2\halves\113-A and 113-B:
#     A = odd  frames DSC00001,3,..,63  (32)      B = even DSC00002,4,..,62 (31)
# align_image_stack was given the frames with --use-given-order, so al_0000
# corresponds to DSC00001; A is therefore the EVEN-indexed al_ files.
#
# RULE 47.  Reads C:\dev\strehl-out\V-LINEAR2\aligned\al_*.tif (run_free.ps1).
# Writes  C:\dev\strehl-out\V-LINEAR2\out\coh-*.tif

$ErrorActionPreference = 'Stop'

$root = 'C:\dev\strehl-out\V-LINEAR2'
$ad   = "$root\aligned"
$out  = "$root\out"
$logs = "$root\logs"
$hb   = "$root\hugin\Hugin\bin"
$fsUp = 'C:\dev\macro\tools\focus-stack\focus-stack\focus-stack.exe'

$all = Get-ChildItem "$ad\al_*.tif" | Sort-Object Name | ForEach-Object FullName
if ($all.Count -ne 63) { throw "expected 63 aligned frames, found $($all.Count)" }
$idx = 0..($all.Count - 1)
$sets = @{
  full = $all
  A    = @($idx | Where-Object { $_ % 2 -eq 0 } | ForEach-Object { $all[$_] })  # DSC odd
  B    = @($idx | Where-Object { $_ % 2 -eq 1 } | ForEach-Object { $all[$_] })  # DSC even
}
foreach ($k in 'full','A','B') { Write-Host ("set {0}: {1} aligned frames" -f $k, $sets[$k].Count) }

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

# --- enfuse on the shared-raster subsets (full already exists) -------------
foreach ($k in 'A','B') {
  $dst = "$out\coh-enfuse-$k.tif"
  if (Test-Path $dst) { Say "coh-enfuse-$k exists, skipped"; continue }
  Say "coh-enfuse-$k starting"
  $t0 = Get-Date
  & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 `
      --hard-mask --output=$dst @($sets[$k]) 2>&1 |
      Out-File "$logs\coh-enfuse-$k.log" -Encoding utf8
  Say ("coh-enfuse-{0} exit={1} {2}s bytes={3}" -f $k, $LASTEXITCODE,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

# --- focus-stack MERGE ONLY, on the same shared-raster subsets -------------
foreach ($k in 'full','A','B') {
  $dst = "$out\coh-fs15-$k.tif"
  if (Test-Path $dst) { Say "coh-fs15-$k exists, skipped"; continue }
  Say "coh-fs15-$k starting"
  $t0 = Get-Date
  & $fsUp --no-align "--output=$dst" @($sets[$k]) 2>&1 |
      Out-File "$logs\coh-fs15-$k.log" -Encoding utf8
  Say ("coh-fs15-{0} exit={1} {2}s bytes={3}" -f $k, $LASTEXITCODE,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

Say "COHERENCE INPUTS DONE"
Get-ChildItem "$out\coh-*.tif" | Select-Object Name, Length
