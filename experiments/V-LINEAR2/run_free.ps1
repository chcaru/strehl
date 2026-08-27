# V-LINEAR2 / run_free.ps1
#
# Runs the FREE / OPEN-SOURCE comparator field over the same 63 linear develops
# strehl made, so that a head-to-head can be reported against software this
# project can actually re-run.  Zerene is unavailable: its trial has expired and
# it refuses to write output (docs/research/V-LINEAR.md sec.1, MEASURED).
#
# LICENCE POSTURE.  Both comparators are RUN as shipped binaries and measured as
# black boxes.  No comparator source is vendored into this repository and no
# binary is redistributed from it.
#   * Hugin (align_image_stack, enfuse/enblend) -- GPL.  Obtained as the official
#     Hugin-2025.0.1-win64.msi, hash-verified by winget
#     (sha256 BA40159130200568C09B8FBE329B631B9AFAFF7E5FBEAE3DD2812333C46E9FCA),
#     then EXTRACTED with `msiexec /a` rather than installed, because this
#     session is not elevated.  Extraction is a plain administrative install; it
#     patches nothing.
#   * focus-stack 1.5 -- MIT (Copyright (c) 2019 Petteri Aimonen).  The copy
#     already on this machine at C:\dev\macro\tools\focus-stack\ was PROVEN to be
#     the official release, not a local fork, by downloading
#     focus-stack_Windows.zip from the upstream GitHub release and confirming
#     focus-stack.exe is byte-identical:
#         sha256 E256176D70BEC54BB51A448B2ADC452E7F49D21BC5042B40689A3257BBFDEE9E
#     (C:\dev\macro\focus-stack\dist\focus-stack.exe is a DIFFERENT binary,
#      sha256 0ABA0CF0..., built May 2026 against OpenCV 4.13 -- that is the
#      owner's local fork and is run as a separate, clearly labelled arm.)
#
# MEASURED BEFORE THIS SCRIPT WAS WRITTEN, and it decides the reporting:
#   focus-stack 1.5 writes 8 BITS PER CHANNEL in every output format tried
#   (.tif -> uint8, .png -> uint8).  On these linear develops -- median
#   1112/65535 = 1.7% -- that lands the median at 8-bit level 4.  A linear
#   encoding of this scene does not fit in 8 bits, so focus-stack's fine-scale
#   band power is quantisation-limited, NOT resolution-limited.  quantfloor.py
#   measures that floor; the focus-stack arm is only reported against it.
#   enfuse, by contrast, round-trips 16-bit (verified: output bitspersample 16,
#   median 1126 against an input median 1112), so the Hugin arm carries no
#   bit-depth confound and is the primary comparator.
#
# RULE 47 RECORD -----------------------------------------------------------
#   inputs      C:\dev\strehl-out\V-LINEAR\lintiff\DSC00001..00063.tif
#               63 files, 197,798,923 bytes each, 7032x4688 u16 RGB.
#               Made by experiments/V-LINEAR/develop_frames.ps1 from
#               D:\personal\macro\113MSDCF (READ-ONLY) with
#               `strehl develop --linear-srgb --demosaic`, STREHL_ALIGN=0.
#   strehl arm  NOT produced here.  It is C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff,
#               made by experiments/V-HEADTOHEAD2/render_linear.ps1 with
#               `strehl stack D:\personal\macro\113MSDCF --merge pyramid
#                --pyramid-gate 4.5 --linear-srgb --demosaic`,
#               STREHL_FULLRES_GATHER=1, pinned binary 740e7056.
#
#   align_image_stack.exe  version 2025.0.1.9609d5726ad8
#     PASSED     -l   inputs ARE linear; this is not an assumption, the develop
#                     wrote a gamma-1.0 TRC (V-LINEAR sec.2, MEASURED)
#                -m   optimise field of view per image -- the tool's own help
#                     names this as the focus-stack case ("slightly different
#                     magnification").  Omitting it would leave focus breathing
#                     in the residual and hand strehl an unearned win.
#                -C   auto crop to the area covered by all images
#                -a   output prefix
#                --use-given-order   the default sorts by EXPOSURE VALUE; these
#                     frames are all one exposure, so that sort is undefined
#                     with respect to focus order, and consecutive-pair matching
#                     needs focus order.  Passed to remove the risk, not because
#                     the sort was observed to misbehave.
#     NOT PASSED -d (radial distortion; V-LINEAR sec.3 measured k1 = -0.0023 px,
#                     there is no distortion here to solve), -i, -x/-y/-z, -e,
#                     -S/-A/-P, -t (default 3 px), --corr (default 0.9),
#                     -c (default 8), -g (default 5x5), -s (default 1),
#                     --gpu (CPU remap is deterministic), --align-to-first,
#                     --dont-remap-ref, --distortion
#
#   enfuse.exe   version 4.3-993fd4822e8d
#     PASSED     --exposure-weight=0 --saturation-weight=0 --contrast-weight=1
#                --hard-mask
#                This quadruple is the canonical focus-stacking invocation from
#                enfuse's own documentation: turn off the two exposure-fusion
#                terms, weight purely on local contrast, and take the hard
#                (winner-take-all) mask rather than a blended one.  --hard-mask
#                is what makes it a focus stacker instead of an averager.
#     NOT PASSED --entropy-weight (default 0), --contrast-window-size
#                (default 5), --contrast-edge-scale (default 0, i.e. the
#                variance detector rather than Laplacian-of-Gaussian),
#                --gray-projector (default average), --levels (default maximum),
#                --depth (default: follows input, verified 16-bit out),
#                --wrap, --blend-colorspace
#
#   focus-stack.exe  1.5-42-g0cd289e, OpenCV 4.12.0
#     PASSED     --output only.  Every algorithmic default is left alone
#                deliberately: this is what a user gets.
#     NOT PASSED --global-align, --full-resolution-align, --no-whitebalance,
#                --no-contrast, --no-transform, --align-keep-size, --nocrop,
#                --consistency (default 2), --denoise (default 1.0),
#                --batchsize (default 8), --threads (default nCPU+1),
#                --no-opencl (so OpenCL/RTX 5090 IS used -- recorded because it
#                makes the run not bit-reproducible on another machine)
#
#   env          no STREHL_* variable is read by any of these tools.
#   outputs      C:\dev\strehl-out\V-LINEAR2\out\*.tif  (+ aligned\ ~14 GB)

$ErrorActionPreference = 'Stop'

$lin     = 'C:\dev\strehl-out\V-LINEAR\lintiff'
$root    = 'C:\dev\strehl-out\V-LINEAR2'
$aligned = "$root\aligned"
$out     = "$root\out"
$logs    = "$root\logs"
$hb      = "$root\hugin\Hugin\bin"
$fsUp    = 'C:\dev\macro\tools\focus-stack\focus-stack\focus-stack.exe'
$fsFork  = 'C:\dev\macro\focus-stack\dist\focus-stack.exe'

foreach ($d in @($aligned, $out, $logs)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

$files = 1..63 | ForEach-Object { "$lin\DSC{0:D5}.tif" -f $_ }
foreach ($f in $files) { if (-not (Test-Path $f)) { throw "missing input $f" } }
Write-Host ("inputs: {0} files, {1:N0} bytes each" -f $files.Count, (Get-Item $files[0]).Length)

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

# --- arm 1: focus-stack 1.5, upstream, defaults ---------------------------
foreach ($arm in @(@{n='focusstack-1.5'; exe=$fsUp}, @{n='focusstack-fork'; exe=$fsFork})) {
  $dst = "$out\$($arm.n).tif"
  if (Test-Path $dst) { Say "$($arm.n) exists, skipped"; continue }
  if (-not (Test-Path $arm.exe)) { Say "$($arm.n) MISSING BINARY $($arm.exe)"; continue }
  Say "$($arm.n) starting"
  $t0 = Get-Date
  & $arm.exe "--output=$dst" @files 2>&1 | Out-File "$logs\$($arm.n).log" -Encoding utf8
  $code = $LASTEXITCODE
  Say ("{0} exit={1} {2}s bytes={3}" -f $arm.n, $code,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

# --- arm 2: Hugin align_image_stack + enfuse ------------------------------
$have = (Get-ChildItem "$aligned\al_*.tif" -ErrorAction SilentlyContinue).Count
if ($have -ne $files.Count) {
  Say "align_image_stack starting ($have/$($files.Count) present)"
  Remove-Item "$aligned\al_*.tif" -ErrorAction SilentlyContinue
  $t0 = Get-Date
  & "$hb\align_image_stack.exe" -l -m -C --use-given-order -a "$aligned\al_" @files 2>&1 |
      Out-File "$logs\align_image_stack.log" -Encoding utf8
  $code = $LASTEXITCODE
  Say ("align_image_stack exit={0} {1}s files={2}" -f $code,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       (Get-ChildItem "$aligned\al_*.tif" -ErrorAction SilentlyContinue).Count)
  if ($code -ne 0) { throw "align_image_stack failed $code" }
} else { Say "aligned frames already present, skipped" }

$dst = "$out\enfuse-hardmask.tif"
if (Test-Path $dst) { Say "enfuse exists, skipped" } else {
  Say "enfuse starting"
  $al = (Get-ChildItem "$aligned\al_*.tif" | Sort-Object Name | ForEach-Object FullName)
  $t0 = Get-Date
  & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 `
      --hard-mask --output=$dst @al 2>&1 | Out-File "$logs\enfuse.log" -Encoding utf8
  $code = $LASTEXITCODE
  Say ("enfuse exit={0} {1}s bytes={2}" -f $code,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

Say "DONE"
Get-ChildItem $out | Select-Object Name, Length
