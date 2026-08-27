# TIMING: strehl vs the patched focus-stack fork, same subject, same machine.
#
# WHAT THIS IS AND IS NOT
# -----------------------
# Wall clock, measured with a Stopwatch around the process, not CPU time and
# not a self-reported internal number.  Both tools also print their own
# internal timings; those are recorded in the logs but NOT used as the result,
# because they exclude process start, library load and final flush.
#
# THE ASYMMETRY IS THE POINT AND IS NOT NORMALISED AWAY
# ----------------------------------------------------
#   strehl reads  105 ARW  =  3.88 GB   directly from the camera files.
#   the fork reads 105 TIFF = 38.42 GB, which are Lightroom developments OF
#   THOSE SAME 105 ARW FILES.  That development is work the fork's pipeline
#   requires and strehl's does not, it happened before either tool started,
#   and it is not counted in either number below.  So every fork number here
#   is an UNDER-count of the work its pipeline actually needs, and the gap
#   reported is a LOWER BOUND on strehl's advantage.
#
# SCOPE, STATED RATHER THAN EQUALISED
# -----------------------------------
#   strehl writes one merged TIFF.
#   the fork can also write a depthmap and a 3D preview.  The archived run
#   that produced the file measured in V-HEADTOHEAD2 wrote all three.  Both
#   scopes are timed: FORK-MERGE (merged TIFF only, the apples-to-apples arm)
#   and FORK-FULL (all three, the arm that reproduces the archived artefact).
#
# ALIGNMENT IS INCLUDED ON BOTH SIDES
# -----------------------------------
#   `strehl stack --help`: "It ALIGNS BY DEFAULT (M86c)".  STREHL_WARPMAP is
#   deliberately NOT set here, so strehl solves its own alignment exactly as
#   the fork does.  The renders measured elsewhere in V-HEADTOHEAD2 DID use a
#   pre-solved sidecar and are therefore NOT valid timing runs; that is why
#   this script re-renders instead of reusing them.
#
# CACHE STATE
# -----------
#   Windows has no supported way to drop the filesystem cache from a script.
#   So this does not claim "cold": it runs each arm three times, records free
#   RAM before each, and reports run 1 (first touch this session) against runs
#   2-3 (warm) as measured, with the machine's RAM stated so the reader can
#   judge what could have been cached.  61.6 GB total: the fork's 38.42 GB of
#   input CAN largely cache, strehl's 3.88 GB certainly can.

$ErrorActionPreference = 'Continue'
$out  = 'C:\dev\strehl-out\V-H2H2\timing'
$logs = "$out\logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$fork = 'C:\dev\macro\focus-stack\build-msvc\focus-stack.exe'
$rawDir  = 'D:\personal\macro\coffee-bean'
$tifDir  = 'D:\edited\macro\coffee-bean'
$REPS = 3

function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1) }
function Busy {
  $p = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.CPU -gt 0 }
  ($p | Measure-Object).Count
}

$rows = @()
function Run($arm, $rep, $block, $logfile) {
  $free0 = FreeGB
  [System.GC]::Collect()
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $block
  $sw.Stop()
  $code = $LASTEXITCODE
  $secs = [math]::Round($sw.Elapsed.TotalSeconds, 2)
  $sz = 0
  if (Test-Path $logfile) { $sz = (Get-Item $logfile).Length }
  $script:rows += [pscustomobject]@{
    arm = $arm; rep = $rep; seconds = $secs; exit = $code
    freeGB_before = $free0; freeGB_after = (FreeGB); log_bytes = $sz
  }
  "{0,-12} rep {1}  {2,8:N2} s   exit {3}   freeRAM {4} -> {5} GB" -f `
      $arm, $rep, $secs, $code, $free0, (FreeGB) | Write-Host
}

Write-Host "=== environment ==="
Write-Host ("CPU        : " + (Get-CimInstance Win32_Processor | Select-Object -First 1).Name.Trim())
Write-Host ("logical    : $env:NUMBER_OF_PROCESSORS")
Write-Host ("RAM GB     : " + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1))
Write-Host ("free RAM   : " + (FreeGB) + " GB")
Write-Host ("processes with CPU time: " + (Busy))
$raw = Get-ChildItem "$rawDir\*.ARW"
$tif = Get-ChildItem "$tifDir\*.tif"
Write-Host ("strehl input: {0} ARW, {1:N2} GB" -f $raw.Count, (($raw|Measure-Object Length -Sum).Sum/1GB))
Write-Host ("fork   input: {0} TIF, {1:N2} GB" -f $tif.Count, (($tif|Measure-Object Length -Sum).Sum/1GB))
if ($raw.Count -ne $tif.Count) { throw "FRAME COUNT MISMATCH -- the arms are not the same stack" }
Write-Host ("frame-set equivalence: both {0} frames  OK" -f $raw.Count)

$files = $tif | ForEach-Object { $_.FullName }

for ($r = 1; $r -le $REPS; $r++) {
  # ---- strehl, end to end: decode + align + focus + merge + write ----------
  $lg = "$logs\strehl-cb-rep$r.log"
  $env:STREHL_FULLRES_GATHER = '1'
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
  Run 'STREHL' $r {
    & $exe stack $rawDir --out "$out\strehl-cb.tiff" --merge pyramid `
          --pyramid-gate 4.5 --linear-srgb --demosaic 2>&1 |
      Out-File -FilePath $lg -Encoding utf8
  } $lg

  # ---- fork, merged TIFF only: the apples-to-apples scope ------------------
  $lg = "$logs\fork-merge-cb-rep$r.log"
  Run 'FORK-MERGE' $r {
    & $fork --output="$out\fork-cb.tif" --output-colorspace=linear-rec2020 `
          --output-bitdepth=32 @files 2>&1 |
      Out-File -FilePath $lg -Encoding utf8
  } $lg
}

# ---- fork, full scope: reproduces the archived artefact -------------------
$lg = "$logs\fork-full-cb.log"
Run 'FORK-FULL' 1 {
  & $fork --output="$out\fork-cb-full.tif" --output-colorspace=linear-rec2020 `
        --output-bitdepth=32 --depthmap="$out\fork-cb-depth.png" `
        --3dview="$out\fork-cb-3d.png" @files 2>&1 |
    Out-File -FilePath $lg -Encoding utf8
} $lg

Write-Host "`n=== RESULT TABLE ==="
$rows | Format-Table -AutoSize | Out-String -Width 160 | Write-Host
$rows | Export-Csv -NoTypeInformation -Path "$out\timing.csv"
Write-Host "wrote $out\timing.csv"
