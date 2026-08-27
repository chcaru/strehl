# TIMING v2 -- strehl vs the patched focus-stack fork, same subject, same
# machine, wall clock.  v1 is `timing.ps1`; it is kept because it FAILED and the
# way it failed is a result.
#
# WHAT v1 GOT WRONG (read this before trusting any number in this file)
# --------------------------------------------------------------------
# D1  v1 unset STREHL_WARPMAP and believed that made the run end-to-end.  It did
#     not.  `strehl stack` discovers a CACHED sidecar under $STREHL_CACHE_DIR
#     (default %LOCALAPPDATA%\strehl\warpmaps, align_cmd.rs:1176) and v1's runs
#     printed, in their own logs:
#         alignment       : ON (sidecar), reference frame 52, 105 placed, 0.0 s
#     Alignment cost ZERO in both v1 strehl runs, while the fork solves its
#     alignment every time.  v1's strehl number was not comparable to the fork's
#     and would have overstated strehl by the whole solve.  Caught by READING
#     the tool's own printed line, which is why it is printed.
#     Fixed here by pointing STREHL_CACHE_DIR at a private directory and wiping
#     it before every SOLVE rep -- and then ASSERTING the mode strehl reports,
#     so a silent regression to the cache fails the run instead of flattering it.
#
# D2  v1 ran both tools through a PowerShell pipeline (`| Out-File`), which
#     forbids reading exit state cleanly and gives no access to peak memory or
#     CPU time.  Fixed with Start-Process + file redirection: no pipeline, and
#     PeakWorkingSet64 / TotalProcessorTime come off the Process object.
#
# D3  Not a defect but a finding v1 produced: the fork at its DEFAULT
#     --hdr-preserve=auto (which resolves ON for 32-bit float linear-rec2020,
#     "costs ~3.6 GB extra peak RAM per 32 MP frame" per its own --help) ran
#     521.52 s and then DIED:
#         OpenCV(4.13.0) ... (-4:Insufficient memory) Failed to allocate
#         146800640 bytes in function 'cv::OutOfMemoryError'
#     at task 716/860, exit code 1.  That log is kept.  This file times the
#     --hdr-preserve=off path instead, which the fork's own help describes as
#     the legacy path for "bit-identity regression against pre-Phase-4 builds"
#     -- i.e. the closest reachable match to the build that actually produced
#     the comparator artefact measured in V-HEADTOHEAD2.
#
# THE ASYMMETRY IS THE POINT AND IS NOT NORMALISED AWAY
# ----------------------------------------------------
#   strehl reads  105 ARW  =  3.88 GB straight off the camera files.
#   the fork reads 105 TIFF = 38.42 GB, which are Lightroom developments OF
#   THOSE SAME 105 ARW.  That development is work the fork's route requires and
#   strehl's does not; it happened before either tool started and is counted in
#   NEITHER number below.  Every fork number here is therefore an UNDER-count of
#   its route's true cost, and the gap is a LOWER BOUND on strehl's advantage.
#   (The fork CAN read ARW directly -- it has a whole --raw-* flag family -- but
#   the comparator artefact this project measured was made from the TIFFs, so
#   the TIFFs are what is timed.)
#
# SCOPE, STATED RATHER THAN EQUALISED
# -----------------------------------
#   strehl writes one merged TIFF.  The fork here also writes one merged TIFF
#   (no --depthmap, no --3dview), though it computes a depth map internally
#   either way -- its own progress lines say "Construct depthmap layer N" in a
#   run that was never asked for one.  The archived comparator run wrote all
#   three artefacts and its internal clock separates them: merged TIFF saved at
#   93.739 s, last artefact at 143.458 s.
#
# CACHE STATE
# -----------
#   Windows has no supported script-level way to drop the filesystem cache, so
#   nothing here claims "cold".  Each arm is repeated and free RAM is recorded
#   before and after every run, with the machine's 61.6 GB stated, so a reader
#   can see what could have been cached.  The one genuine eviction event that
#   occurred is reported as measured rather than manufactured: the fork streams
#   38.42 GB through the page cache, which evicts strehl's 3.88 GB of ARW.

$ErrorActionPreference = 'Continue'
$out   = 'C:\dev\strehl-out\V-H2H2\timing'
$logs  = "$out\logs"
$cache = "$out\cache"
New-Item -ItemType Directory -Force -Path $logs  | Out-Null
New-Item -ItemType Directory -Force -Path $cache | Out-Null

$exe    = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$fork   = 'C:\dev\macro\focus-stack\build-msvc\focus-stack.exe'
$rawDir = 'D:\personal\macro\coffee-bean'
$tifDir = 'D:\edited\macro\coffee-bean'

function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1) }

# Peak working set and CPU time are read while the process is ALIVE, once every
# 2 s.  Reading them after exit returns 0 -- measured: the probe run of the fork
# reported "peak WS = 0.00 GB" post-exit while a live sample of the same process
# read 50,770,456,576 bytes.  PeakWorkingSet64 is itself a running maximum kept
# by the OS, so a 2 s poll cannot miss a spike, only the final instant.
$rows = @()
function RunProc($arm, $rep, $exePath, $argList, $stem) {
  $o = "$logs\$stem.out"; $e = "$logs\$stem.err"
  $free0 = FreeGB
  $peakB = 0L; $cpuS = 0.0
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $p = Start-Process -FilePath $exePath -ArgumentList $argList -NoNewWindow -PassThru `
         -RedirectStandardOutput $o -RedirectStandardError $e
  while (-not $p.HasExited) {
    try {
      $p.Refresh()
      if ($p.PeakWorkingSet64 -gt $peakB) { $peakB = $p.PeakWorkingSet64 }
      $cpuS = $p.TotalProcessorTime.TotalSeconds
    } catch {}
    Start-Sleep -Milliseconds 2000
  }
  $p.WaitForExit()
  $sw.Stop()
  $secs = [math]::Round($sw.Elapsed.TotalSeconds, 2)
  $peak = [math]::Round($peakB/1GB, 2)
  $cpu  = [math]::Round($cpuS, 1)
  try { if ($p.TotalProcessorTime.TotalSeconds -gt $cpu) { $cpu = [math]::Round($p.TotalProcessorTime.TotalSeconds,1) } } catch {}
  $script:rows += [pscustomobject]@{
    arm = $arm; rep = $rep; seconds = $secs; exit = $p.ExitCode
    peakWS_GB = $peak; cpu_s = $cpu
    freeGB_before = $free0; freeGB_after = (FreeGB); stem = $stem
  }
  "{0,-14} rep {1}  {2,8:N2} s  exit {3}  peakWS {4,6:N2} GB  cpu {5,7:N1} s  freeRAM {6} -> {7} GB" -f `
      $arm, $rep, $secs, $p.ExitCode, $peak, $cpu, $free0, (FreeGB) | Write-Host
  return @($o, $e)
}

Write-Host "=== environment ==="
Write-Host ("CPU        : " + (Get-CimInstance Win32_Processor | Select-Object -First 1).Name.Trim())
Write-Host ("logical    : $env:NUMBER_OF_PROCESSORS")
Write-Host ("RAM GB     : " + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1))
Write-Host ("free RAM   : " + (FreeGB) + " GB")
Write-Host ("strehl exe : " + (Get-FileHash $exe -Algorithm SHA256).Hash)
Write-Host ("fork   exe : " + (Get-FileHash $fork -Algorithm SHA256).Hash + "  built " + (Get-Item $fork).LastWriteTime)

$raw = Get-ChildItem "$rawDir\*.ARW"
$tif = Get-ChildItem "$tifDir\*.tif"
Write-Host ("strehl input: {0} ARW, {1:N2} GB" -f $raw.Count, (($raw|Measure-Object Length -Sum).Sum/1GB))
Write-Host ("fork   input: {0} TIF, {1:N2} GB" -f $tif.Count, (($tif|Measure-Object Length -Sum).Sum/1GB))
if ($raw.Count -ne $tif.Count) { throw "FRAME COUNT MISMATCH -- the arms are not the same stack" }
Write-Host ("frame-set equivalence: both {0} frames  OK" -f $raw.Count)

$env:STREHL_FULLRES_GATHER = '1'
$env:STREHL_CACHE_DIR      = $cache
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

$strehlArgs = @('stack', $rawDir, '--out', "$out\strehl-cb.tiff", '--merge', 'pyramid',
                '--pyramid-gate', '4.5', '--linear-srgb', '--demosaic')

# ---- print-then-TEST: strehl prints its alignment mode; we read it and fail on it.
function AssertAlign($stem, $want) {
  $line = (Select-String -Path "$logs\$stem.out","$logs\$stem.err" -Pattern '^alignment ' |
           Select-Object -First 1).Line
  if (-not $line) { throw "$stem : strehl printed no alignment line -- cannot certify the arm" }
  Write-Host ("    " + $line.Trim())
  if ($line -notmatch [regex]::Escape($want)) {
    throw "$stem : expected alignment '$want' but strehl reported: $line"
  }
}

# =============== ARM 1: strehl, END TO END, alignment SOLVED ================
for ($r = 1; $r -le 3; $r++) {
  Get-ChildItem $cache -File -ErrorAction SilentlyContinue | Remove-Item -Force
  $stem = "v2-strehl-solve-$r"
  RunProc 'STREHL-SOLVE' $r $exe $strehlArgs $stem | Out-Null
  AssertAlign $stem 'ON (solved)'
}

# =============== ARM 2: strehl, sidecar already cached =====================
# The cache now holds the sidecar ARM 1 solved.  Do not wipe it.
for ($r = 1; $r -le 3; $r++) {
  $stem = "v2-strehl-cached-$r"
  RunProc 'STREHL-CACHED' $r $exe $strehlArgs $stem | Out-Null
  AssertAlign $stem 'ON (sidecar)'
}

# =============== ARM 3: the fork, merged TIFF only =========================
# One rep here.  Rep 1 with byte-identical flags and the same binary was run as
# a standalone probe before this script existed and is logged at
#   logs\probe-fork-hdroff.log / .err   ->  1604.15 s wall, exit 0,
#   CPU 6430.6 s, live-sampled peak working set 50,770,456,576 B = 47.28 GiB.
# The fork takes ~27 minutes per rep on this stack, so the second rep is this
# one rather than a third.
$files = $tif | ForEach-Object { $_.FullName }
for ($r = 2; $r -le 2; $r++) {
  $fa = @("--output=$out\fork-cb.tif", '--output-colorspace=linear-rec2020',
          '--output-bitdepth=32', '--hdr-preserve=off') + $files
  $stem = "v2-fork-merge-$r"
  RunProc 'FORK-MERGE' $r $fork $fa $stem | Out-Null
  $tail = Get-Content "$logs\$stem.out" -Tail 1
  Write-Host ("    last progress line: " + $tail)
}

Write-Host "`n=== RESULT TABLE ==="
$rows | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
$rows | Export-Csv -NoTypeInformation -Path "$out\timing2.csv"
Write-Host "wrote $out\timing2.csv"

# ---- counted partition: every run lands in exactly one bucket --------------
$ok   = ($rows | Where-Object { $_.exit -eq 0 }).Count
$fail = ($rows | Where-Object { $_.exit -ne 0 }).Count
Write-Host ("runs: completed {0} + nonzero-exit {1} = {2} of {2}" -f $ok, $fail, $rows.Count)
if (($ok + $fail) -ne $rows.Count) { throw "partition does not sum" }
