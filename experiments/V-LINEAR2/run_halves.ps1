# V-LINEAR2 / run_halves.ps1
#
# Runs each free comparator TWICE MORE, on the two disjoint half-stacks, so
# that the comparator gets the same noise-free treatment strehl already has.
#
# WHY.  h2h2b's rigorous bound is one-sided precisely because only strehl had
# half-stacks: `Cn_strehl` is coherent power across disjoint frame sets, so
# strehl's noise contributes zero, while `Pn_comp` is the comparator's signal
# PLUS its noise.  That asymmetry is safe when it flatters the comparator and
# useless when the comparator comes out ahead -- which is what happened here
# (focus-stack 1.5 shows ~2x strehl's normalised 0.20-0.25 power).  Two things
# produce that: more resolved detail, or more noise.  Running the comparator on
# the same A/B split makes `Cn_comp` available and removes ITS noise too, so
# coherent power can be compared against coherent power.
#
# THE SPLIT is the one V-HEADTOHEAD2 already used, verified by listing
# C:\dev\strehl-out\V-H2H2\halves\113-A and 113-B:
#     A = odd  frames DSC00001,3,5..63   (32 frames)
#     B = even frames DSC00002,4,6..62   (31 frames)
# Same split, same source frames, so strehl's C and the comparator's C are
# built from the identical partition of the identical exposures.
#
# WHAT THIS STILL DOES NOT SEPARATE, stated up front: noise COMMON to both
# halves survives coherence on both arms (V-HEADTOHEAD2 sec.7 disclosed
# NOISE_COM scoring 6.05), and deterministic sharpening or ringing artefacts
# are coherent by construction.  So `Cn_comp > Cn_strehl` means "more coherent
# fine-scale structure", which is resolution OR overshoot, not resolution alone.
#
# RULE 47 RECORD.  Identical flags to run_free.ps1 -- see that file's header for
# the full passed/not-passed list.  Only the input file list differs.
#   inputs   C:\dev\strehl-out\V-LINEAR\lintiff\DSC000{odd|even}.tif
#   outputs  C:\dev\strehl-out\V-LINEAR2\out\<arm>-{A,B}.tif

$ErrorActionPreference = 'Stop'

$lin   = 'C:\dev\strehl-out\V-LINEAR\lintiff'
$root  = 'C:\dev\strehl-out\V-LINEAR2'
$out   = "$root\out"
$logs  = "$root\logs"
$hb    = "$root\hugin\Hugin\bin"
$fsUp  = 'C:\dev\macro\tools\focus-stack\focus-stack\focus-stack.exe'

$halves = @{
  A = (1..63 | Where-Object { $_ % 2 -eq 1 } | ForEach-Object { "$lin\DSC{0:D5}.tif" -f $_ })
  B = (1..63 | Where-Object { $_ % 2 -eq 0 } | ForEach-Object { "$lin\DSC{0:D5}.tif" -f $_ })
}
foreach ($k in 'A','B') { Write-Host ("half {0}: {1} frames" -f $k, $halves[$k].Count) }

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

# --- focus-stack 1.5 on each half ----------------------------------------
foreach ($k in 'A','B') {
  $dst = "$out\focusstack-1.5-$k.tif"
  if (Test-Path $dst) { Say "fs15-$k exists, skipped"; continue }
  Say "fs15-$k starting"
  $t0 = Get-Date
  & $fsUp "--output=$dst" @($halves[$k]) 2>&1 | Out-File "$logs\focusstack-1.5-$k.log" -Encoding utf8
  Say ("fs15-{0} exit={1} {2}s bytes={3}" -f $k, $LASTEXITCODE,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

# --- Hugin align+enfuse on each half --------------------------------------
foreach ($k in 'A','B') {
  $dst = "$out\enfuse-hardmask-$k.tif"
  if (Test-Path $dst) { Say "enfuse-$k exists, skipped"; continue }
  $ad = "$root\aligned-$k"
  New-Item -ItemType Directory -Force -Path $ad | Out-Null
  if ((Get-ChildItem "$ad\al_*.tif" -ErrorAction SilentlyContinue).Count -ne $halves[$k].Count) {
    Say "align-$k starting"
    Remove-Item "$ad\al_*.tif" -ErrorAction SilentlyContinue
    $t0 = Get-Date
    & "$hb\align_image_stack.exe" -l -m -C --use-given-order -a "$ad\al_" @($halves[$k]) 2>&1 |
        Out-File "$logs\align-$k.log" -Encoding utf8
    Say ("align-{0} exit={1} {2}s files={3}" -f $k, $LASTEXITCODE,
         [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
         (Get-ChildItem "$ad\al_*.tif" -ErrorAction SilentlyContinue).Count)
  }
  Say "enfuse-$k starting"
  $al = (Get-ChildItem "$ad\al_*.tif" | Sort-Object Name | ForEach-Object FullName)
  $t0 = Get-Date
  & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 `
      --hard-mask --output=$dst @al 2>&1 | Out-File "$logs\enfuse-$k.log" -Encoding utf8
  Say ("enfuse-{0} exit={1} {2}s bytes={3}" -f $k, $LASTEXITCODE,
       [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 }))
}

Say "HALVES DONE"
Get-ChildItem $out | Select-Object Name, Length
