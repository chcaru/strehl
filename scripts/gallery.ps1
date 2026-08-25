<#
.SYNOPSIS
  Render every subject in the library, full frame, developed, CLEAN, into one
  directory the owner can open.

.DESCRIPTION
  This is the artifact. Not crops, not scores, not overlays -- photographs, at a
  size you can actually look at, in one folder, produced by one command.

  It exists because of a specific failure. For weeks this project reported on
  its own output through 100% crops and scalar metrics, and every deliverable
  image had debug ROI rectangles burned into it. The owner had never once been
  shown a clean render of his own photographs. Two defects that were obvious in
  three seconds of looking at a full frame -- a milky veil over everything, and
  the boxes themselves -- survived 1786 recorded facts, because nobody looked at
  a picture. So:

    * NO ANNOTATIONS. Diagnosis overlays are useful and they go in the sibling
      `annotated/` directory that `crop_set.py full` writes. Never here.
    * FULL FRAME, downsampled to a viewing size. Crop-level judgement is how a
      halo tracing every occluding edge got called "a tight bright rim".
    * ONE BINARY for every subject in a run, recorded next to the images, so
      the arms of a comparison cannot drift. Three renders of one command once
      produced three different files because other agents landed builds in the
      middle of the run.

  Judge the result by looking at it. When the pictures and the number disagree,
  the pictures are right.

.PARAMETER Exe
  The strehl binary. Build it from a pinned `git archive` of an explicit SHA
  when the tree has other agents working in it, and pass it here.

.PARAMETER OutDir
  Where the gallery lands. A `manifest.tsv` and `RUN.txt` are written beside the
  images so a picture can always be traced back to the binary that made it.

.PARAMETER Library
  Root of the subject folders. Read-only: this script never writes to it.

.PARAMETER LongEdge
  Long edge of the emitted JPEG, in pixels. ~2400 is a size you can judge a
  photograph at on a normal screen without opening a 7032 x 4688 TIFF.

.PARAMETER KeepTiff
  Keep the intermediate 16-bit TIFF. Off by default: 26 subjects at ~200 MB each
  fills a disk for no benefit, since the JPEG is the deliverable and the TIFF is
  reproducible from the recorded command.

.PARAMETER Only
  Render just these subjects (comma-separated, or a substring match). For
  iterating on one image without paying for the whole library.

.PARAMETER Guard
  Subjects treated as do-no-harm controls. Each is compared against a stored
  reference and flagged loudly if it moved. The default is couch-fibers-cpl,
  which was audited and found genuinely good, which is exactly why it is the
  one most likely to be degraded silently by work aimed at a different subject.

.PARAMETER GuardDir
  Where the guard references live. Delete a file here to re-establish it.

.PARAMETER NoHistory
  Skip the dated copy. The history is what lets anyone see the trajectory at
  viewing scale instead of trusting a sequence of agent reports.

.EXAMPLE
  pwsh -File scripts\gallery.ps1 -Exe C:\dev\strehl-out\pin\target\release\strehl.exe
#>
[CmdletBinding()]
param(
    [string]$Exe = "C:\dev\strehl-out\target-render\release\strehl.exe",
    [string]$OutDir = "C:\dev\strehl-out\gallery",
    [string]$Library = "D:\personal\macro",
    [int]$LongEdge = 2400,
    [switch]$KeepTiff,
    [string[]]$Only = @(),
    [string[]]$Guard = @('couch-fibers-cpl'),
    [string]$GuardDir = "C:\dev\strehl-out\gallery-guard",
    [switch]$NoHistory
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe)) { throw "no binary at $Exe -- build one first" }
if (-not (Test-Path $Library)) { throw "no library at $Library" }

# `flat-fields` is a calibration campaign, not a photograph. Everything else in
# the library is a subject the owner shot and wants to look at.
$skip = @('flat-fields')

$subjects = Get-ChildItem -Directory $Library |
    Where-Object { $skip -notcontains $_.Name } |
    Sort-Object Name

if ($Only.Count -gt 0) {
    # Substring match, so `-Only flower` picks up every flower variant without
    # having to spell out the CPL suffixes.
    $subjects = $subjects | Where-Object {
        $name = $_.Name
        ($Only | Where-Object { $name -like "*$_*" }).Count -gt 0
    }
}
if ($subjects.Count -eq 0) { throw "no subjects matched" }

$raw = Join-Path $OutDir "_tiff"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $raw | Out-Null

# Record what made these pictures. Without this a gallery is unfalsifiable: you
# cannot tell a real improvement from a different binary.
$exeInfo = Get-Item $Exe
$run = @(
    "gallery run     : $(Get-Date -Format o)"
    "binary          : $Exe"
    "binary mtime    : $($exeInfo.LastWriteTime.ToString('o'))"
    "binary size     : $($exeInfo.Length)"
    "binary sha256   : $((Get-FileHash $Exe -Algorithm SHA256).Hash)"
    "library         : $Library"
    "subjects        : $($subjects.Count)"
    "long edge       : $LongEdge"
    "render command  : strehl stack <DIR> --out <TIFF> --srgb --demosaic"
    ""
    "--srgb is correct HERE and only here: this is a viewing render, and the"
    "tone rendering rides with it. Never measure on one of these files."
)
[IO.File]::WriteAllLines((Join-Path $OutDir "RUN.txt"), $run, (New-Object Text.UTF8Encoding $false))
$run | Write-Host

$rows = New-Object System.Collections.Generic.List[string]
$rows.Add("subject`tframes`tseconds`tpeak_mb`texit`tblack`twhite`tjpeg`tguard")
$guardMoved = New-Object System.Collections.Generic.List[string]

$i = 0
foreach ($s in $subjects) {
    $i++
    $n = $s.Name
    $frames = (Get-ChildItem -File $s.FullName |
        Where-Object { $_.Extension -match '^\.(arw|ARW|raf|RAF|nef|NEF|cr[23]|CR[23]|dng|DNG)$' }).Count
    Write-Host ("[{0,2}/{1}] {2} ({3} frames)" -f $i, $subjects.Count, $n, $frames)

    $tif = Join-Path $raw "$n.tiff"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = Join-Path $raw "$n.log"
    $p = Start-Process -FilePath $Exe `
        -ArgumentList @("stack", "`"$($s.FullName)`"", "--out", "`"$tif`"", "--srgb", "--demosaic") `
        -NoNewWindow -PassThru -RedirectStandardError $log -RedirectStandardOutput (Join-Path $raw "$n.out")
    # Reading the handle while the process is alive is what makes ExitCode
    # non-null afterwards; without it -PassThru reports $null and every render
    # silently "succeeds".
    $null = $p.Handle
    $peak = 0
    while (-not $p.HasExited) {
        # Refresh() is required: the Process object caches its counters at the
        # moment it was created, so without this every render reports the
        # startup working set and peak memory silently becomes a constant.
        try { $p.Refresh(); $peak = [Math]::Max($peak, $p.PeakWorkingSet64) } catch {}
        Start-Sleep -Milliseconds 250
    }
    try { $peak = [Math]::Max($peak, $p.PeakWorkingSet64) } catch {}
    $sw.Stop()
    $exit = $p.ExitCode

    $tone = ""
    if (Test-Path $log) {
        $t = Select-String -Path $log -Pattern '^tone\s+:' | Select-Object -First 1
        if ($t) { $tone = $t.Line }
    }
    $black = ""; $white = ""
    if ($tone -match 'black ([\d.]+), white ([\d.]+)') { $black = $matches[1]; $white = $matches[2] }

    $jpg = ""
    if ($exit -eq 0 -and (Test-Path $tif)) {
        $jpg = Join-Path $OutDir "$n.jpg"
        & python (Join-Path $PSScriptRoot "gallery_view.py") $tif $jpg $LongEdge
        if ($LASTEXITCODE -ne 0) { Write-Warning "$n : view conversion failed" ; $jpg = "" }
        if (-not $KeepTiff) { Remove-Item $tif -Force -ErrorAction SilentlyContinue }
    } else {
        Write-Warning "$n : exit $exit -- see $log"
    }

    # Guarded subjects are checked as they land, not at the end, so a run that
    # is degrading something can be stopped before it costs another 50 minutes.
    $guardState = ""
    if ($Guard -contains $n) {
        & python (Join-Path $PSScriptRoot "guard.py") `
            (Join-Path $OutDir "$n.jpg") (Join-Path $GuardDir "$n.jpg") (Join-Path $OutDir "_guard")
        $guardState = if ($LASTEXITCODE -eq 0) { "held" } else { "MOVED" }
        if ($guardState -eq "MOVED") { $guardMoved.Add($n) }
    }

    $rows.Add(("{0}`t{1}`t{2}`t{3}`t{4}`t{5}`t{6}`t{7}`t{8}" -f `
        $n, $frames, [int]$sw.Elapsed.TotalSeconds, [int]($peak / 1MB), $exit, $black, $white, (Split-Path $jpg -Leaf), $guardState))
    # Written every iteration, not at the end: a run that dies at subject 19
    # should still leave 18 rows of evidence behind.
    [IO.File]::WriteAllLines((Join-Path $OutDir "manifest.tsv"), $rows, (New-Object Text.UTF8Encoding $false))
}

if (-not $KeepTiff) { Remove-Item $raw -Recurse -Force -ErrorAction SilentlyContinue }

# A dated copy of every run. `gallery/` stays the one path worth bookmarking, so
# "open the gallery" never changes meaning, and the history is what shows the
# trajectory -- three lanes are landing changes and the only way to know whether
# the product is getting better is to be able to put the runs side by side at
# viewing scale.
if (-not $NoHistory) {
    $stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
    $hist = Join-Path (Split-Path $OutDir -Parent) "gallery-history\$stamp"
    New-Item -ItemType Directory -Force -Path $hist | Out-Null
    Copy-Item (Join-Path $OutDir "*.jpg") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $OutDir "RUN.txt") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $OutDir "manifest.tsv") $hist -Force -ErrorAction SilentlyContinue
    Write-Host "history: $hist"

    # Subtract this run from the previous one. The gallery answers "is this
    # good"; this answers "is this getting better", and the first time it ran
    # it found 17 of 26 subjects had silently lost sharpness in two hours.
    # Pass both directories explicitly: trend.py orders runs by their recorded
    # time, but naming this run's directory here is one less thing to infer.
    $prevRuns = @(Get-ChildItem -Directory (Split-Path $hist -Parent) |
        Where-Object { $_.FullName -ne $hist -and (Test-Path (Join-Path $_.FullName "RUN.txt")) })
    if ($prevRuns.Count -gt 0) {
        $prior = $prevRuns | Sort-Object {
            $l = Select-String -Path (Join-Path $_.FullName "RUN.txt") -Pattern '^gallery run' | Select-Object -First 1
            if ($l) { [datetime]::Parse(($l.Line -split ':', 2)[1].Trim()) } else { $_.CreationTime }
        } | Select-Object -Last 1
        Write-Host ""
        & python (Join-Path $PSScriptRoot "trend.py") $hist $prior.FullName
    }
}

Write-Host ""
if ($guardMoved.Count -gt 0) {
    Write-Host ""
    Write-Host "  !! REGRESSION GUARD MOVED: $($guardMoved -join ', ')" -ForegroundColor Red
    Write-Host "  !! Look at $OutDir\_guard\*-before-after.png BEFORE accepting this run." -ForegroundColor Red
    Write-Host "  !! These subjects were audited as good. If one moved, something aimed" -ForegroundColor Red
    Write-Host "  !! at a different picture reached them." -ForegroundColor Red
    Write-Host ""
}
Write-Host "gallery: $OutDir"
Write-Host "open it and look at the pictures."
