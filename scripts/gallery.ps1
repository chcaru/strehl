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

  PROVENANCE AND ATOMICITY. Pinning the binary was necessary and it was not
  sufficient. A run that died at subject 12 of 26 left `gallery\` holding 10
  fresh JPEGs sitting on top of 16 from the previous binary, with a `RUN.txt`
  that said "subjects: 26" and a `manifest.tsv` with 10 rows. It looked like one
  coherent gallery and it was two, and the only reason anyone noticed was that
  the row count did not match the file count. Real judgements were made on
  stale frames and had to be thrown out.

  So the directory is now built to fail loudly instead of degrade quietly:

    * Every render goes to a private staging directory and `gallery\` is
      replaced WHOLESALE at the end. Mixing is not detected, it is made
      impossible -- staging only ever holds one binary's output.
    * Provenance is PER FILE, not per run: the binary hash is a column in
      `manifest.tsv` and is also written into each JPEG's comment, so a single
      image taken out of the directory can still say what produced it.
    * `RUN.txt` records subjects PLANNED and subjects RENDERED. It no longer
      asserts a count it did not achieve.
    * `COMPLETE.txt` is written last and only on success; `INCOMPLETE.txt`
      names what failed. The absence of the sentinel is what marks a directory
      as untrustworthy, which is the right polarity -- a killed run cannot write
      anything, so it cannot accidentally claim to have succeeded.
    * `-Only` renders a subset and is NEVER swapped in, because publishing a
      subset would delete every subject it did not render.

  What is enforced is COHERENCE, not completeness. A gallery missing a subject
  is fine as long as it says so and nothing stale fills the gap. A gallery
  holding two binaries' output with no way to tell them apart is never fine.

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

.PARAMETER FixCa
  Lateral-CA profile key, passed to the binary as STREHL_FIX_CA. Defaults to the
  owner's optical path. Pass '' to disable.

  This defaults ON because the correction is a large, visible, print-relevant
  win and it was previously off in every render the owner had ever seen. The
  binary REFUSES an unknown key rather than silently rendering uncorrected, so a
  typo here fails the run instead of quietly producing the old pictures.

  Measured on two subjects, camera-linear, one binary, back-to-back. Mean |R-G|
  at strong edges, normalised by local green, by radial band -- off, then on:

    flat-on-ruler-cpl   0.070 0.074 0.106 0.150 0.164 0.227   (grows with radius)
                        0.068 0.075 0.084 0.086 0.087 0.089   (flat)
    foam                0.167 0.209 0.278 0.348 0.418 0.461   (grows with radius)
                        0.148 0.125 0.127 0.126 0.124 0.152   (flat)

  The signature of a correct radial correction is not that the number falls, it
  is that the RADIAL GROWTH is removed and a flat non-radial floor is left
  behind. That is what both subjects show. Corner improvement is -61% and -67%.
  |B-G| moves under 4% either way, consistent with SYNTHESIS fact 1515: no blue
  lateral displacement is supported on this path, and the profile corrects red
  only.

  `foam` is not a CPL subject, so this is also the out-of-sample transfer test.
  It transfers, which is what a lens-plus-teleconverter aberration should do:
  a CPL is plane-parallel and adds no radial magnification difference.

  The built-in null is the frame centre, where lateral CA is zero by
  construction. The centre crops are unchanged, so the correction is not a
  global desaturation or a blur. Detail is fully preserved at every radius.

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
    [string]$FixCa = "a7c2-fe100gm-2xtc-x4cpl",
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

# A directory with no RAW frames is not a subject, it is a stray folder. Left in
# the plan it fails every run, so the gallery reports INCOMPLETE forever and the
# marker stops meaning anything. Drop it from the plan and say so once.
$RAW_EXT = '^\.(arw|raf|nef|cr[23]|dng)$'
$empty = @($subjects | Where-Object {
    @(Get-ChildItem -File $_.FullName | Where-Object { $_.Extension -match $RAW_EXT }).Count -eq 0
})
if ($empty.Count -gt 0) {
    $subjects = @($subjects | Where-Object { $empty.Name -notcontains $_.Name })
    foreach ($e in $empty) { Write-Host "skipping $($e.Name): no RAW frames" }
}
if ($subjects.Count -eq 0) { throw "no subjects with RAW frames" }

# ---------------------------------------------------------------------------
# The lateral-CA profile names an optical path. Verify each stack IS that path.
# ---------------------------------------------------------------------------
# `a7c2-fe100gm-2xtc-x4cpl` is a per-channel radial rescale fitted for one body,
# one lens and one teleconverter. Applied to a stack shot on anything else it
# does not merely fail to help -- it ADDS an aberration that was never there.
#
# This was raised as an unavoidable caveat, on the grounds that a teleconverter
# cannot be detected from the frames. It can. It is not even in the maker notes:
# `LensModel` is a standard EXIF tag and it spells the converter out in full.
# So the caveat becomes a check, and a check is worth more than a warning
# because a warning has to be read by someone who is already suspicious.
#
# Verified rather than assumed, per subject, every run. On a mismatch the
# correction is switched off FOR THAT SUBJECT ONLY and the reason is recorded in
# the manifest. A stack shot on new glass gets an uncorrected render, which is
# the safe direction to fail: no correction is a known quantity, a
# wrong-coefficient correction is a new defect that looks like a real one.
$CA_BODY = 'ILCE-7CM2'
$CA_LENS = 'FE 100mm F2.8 Macro GM OSS + 2X Teleconverter'
$caPath = @{}
$caVerify = "not attempted"
if ($FixCa) {
    $et = Get-Command exiftool -ErrorAction SilentlyContinue
    if (-not $et) {
        # exiftool is not a declared dependency of this repo. Absent it, apply
        # the profile as asked but say plainly that nothing checked it.
        $caVerify = "UNVERIFIED (exiftool not found; profile applied on trust)"
        Write-Warning "exiftool not found -- cannot verify optical path; applying $FixCa unchecked"
        foreach ($s in $subjects) { $caPath[$s.Name] = $true }
    } else {
        $probes = foreach ($s in $subjects) {
            (Get-ChildItem -File $s.FullName |
                Where-Object { $_.Extension -match $RAW_EXT } |
                Sort-Object Name | Select-Object -First 1).FullName
        }
        $tags = & exiftool -fast2 -T -q -Model -LensModel @probes
        $k = 0; $mismatch = @()
        foreach ($s in $subjects) {
            $p = ($tags[$k] -split "`t"); $k++
            $ok = ($p[0] -eq $CA_BODY) -and ($p[1] -eq $CA_LENS)
            $caPath[$s.Name] = $ok
            if (-not $ok) { $mismatch += "$($s.Name) [$($p[0]) / $($p[1])]" }
        }
        $caVerify = if ($mismatch.Count -eq 0) {
            "verified: $($subjects.Count)/$($subjects.Count) stacks are $CA_BODY + $CA_LENS"
        } else {
            "PARTIAL: CA disabled on $($mismatch.Count) stack(s) -- $($mismatch -join '; ')"
        }
        Write-Host "optical path: $caVerify"
    }
}

# EVERY render goes into a private staging directory, and `gallery\` is only
# ever replaced WHOLESALE at the end. This is not tidiness, it is the fix for a
# real failure: a run that died at subject 12 of 26 left `gallery\` holding 10
# fresh JPEGs on top of 16 from the previous binary, with a RUN.txt that
# confidently said "subjects: 26" and a manifest with 10 rows. It looked like a
# coherent gallery. It was two galleries. Judgements were made on it and had to
# be thrown away.
#
# Rendering in place cannot be made safe by being careful, because the mixing
# happens when the run does NOT reach its own cleanup code -- a crash, an OOM,
# a Ctrl-C. Staging removes the failure mode instead of detecting it: the
# staging directory only ever contains output from one binary, so whatever ends
# up in `gallery\` is coherent even if the run died.
#
# The distinction being enforced is COHERENCE, not completeness. A gallery
# missing a subject is fine as long as it says so and nothing stale fills the
# gap. A gallery holding two binaries' output with no way to tell them apart is
# never fine.
$exeSha = (Get-FileHash $Exe -Algorithm SHA256).Hash
$exeShort = $exeSha.Substring(0, 8)
$stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
$isFull = ($Only.Count -eq 0)
$work = "$OutDir.staging-$exeShort-$stamp"

# A leftover staging directory is a previous crash. Say so rather than silently
# reusing or silently deleting it.
$stale = @(Get-ChildItem -Directory (Split-Path $OutDir -Parent) -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "$((Split-Path $OutDir -Leaf)).staging-*" })
foreach ($s in $stale) {
    Write-Warning "leftover staging dir from an earlier failed run: $($s.FullName)"
}

$raw = Join-Path $work "_tiff"
New-Item -ItemType Directory -Force -Path $work | Out-Null
New-Item -ItemType Directory -Force -Path $raw | Out-Null

# Written FIRST, deleted only on success. The two sentinels have deliberately
# opposite polarity and they cover different failures. COMPLETE.txt is written
# last, so a run that dies cannot claim success. INCOMPLETE.txt is written
# first, so a run that is KILLED -- the OOM abort that took down the 26-subject
# run, a Ctrl-C, a reboot -- still leaves a directory that announces itself.
# try/finally cannot do this; nothing in-process runs when the process is gone.
[IO.File]::WriteAllText((Join-Path $work "INCOMPLETE.txt"),
    "INCOMPLETE: this run has not finished. If this file is still here, it died.`n")
# Record what made these pictures. Without this a gallery is unfalsifiable: you
# cannot tell a real improvement from a different binary.
$exeInfo = Get-Item $Exe

# Lateral-CA correction is selected by the environment, and it was unset -- and
# therefore silently off -- in every gallery before this one. It is now set
# PER SUBJECT inside the render loop, after the optical path has been checked.
Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue

$run = @(
    "gallery run     : $(Get-Date -Format o)"
    "binary          : $Exe"
    "binary mtime    : $($exeInfo.LastWriteTime.ToString('o'))"
    "binary size     : $($exeInfo.Length)"
    "binary sha256   : $exeSha"
    "library         : $Library"
    "subjects planned: $($subjects.Count)"
    "subjects rendered: (run in progress -- if this line is still here, the run did not finish)"
    $(if ($empty.Count -gt 0) { "skipped (no RAW frames): $($empty.Name -join ', ')" } else { "skipped          : (none)" })
    "long edge       : $LongEdge"
    "STREHL_FIX_CA   : $(if ($FixCa) { $FixCa } else { '(off)' })"
    "  optical path  : $caVerify"
    "  what it is    : a per-channel radial rescale for ONE body/lens/TC path."
    "                  It corrects the LENS. It is orthogonal to the merge, and"
    "                  it does not touch the halo or the tone rendering."
    "render command  : strehl stack <DIR> --out <TIFF> --srgb --demosaic"
    ""
    "--srgb is correct HERE and only here: this is a viewing render, and the"
    "tone rendering rides with it. Never measure on one of these files."
)
[IO.File]::WriteAllLines((Join-Path $work "RUN.txt"), $run, (New-Object Text.UTF8Encoding $false))
$run | Write-Host

$rows = New-Object System.Collections.Generic.List[string]
# `binary` is per ROW, not per run. The whole directory-level provenance story
# failed exactly because it was per run: one hash at the top of RUN.txt cannot
# describe a directory that ended up holding two binaries' work.
$rows.Add("subject`tframes`tseconds`texit`tblack`twhite`tzeroRGB`tblownRGB`tjpeg`tguard`tbinary`tca")
$guardMoved = New-Object System.Collections.Generic.List[string]
$failed = New-Object System.Collections.Generic.List[string]

$i = 0
foreach ($s in $subjects) {
    $i++
    $n = $s.Name
    # Reset every iteration. PowerShell scopes these to the whole script, not to
    # the loop body, so without this a subject that fails midway would inherit
    # the PREVIOUS subject's numbers into its manifest row -- stale data wearing
    # the right subject's name, which is the same class of lie as a mixed
    # directory.
    $frames = 0; $exit = $null; $black = ""; $white = ""
    $zero = ""; $blown = ""; $jpg = ""; $guardState = ""; $ca = "off"
    $sw = [Diagnostics.Stopwatch]::StartNew()
  try {
    # Set per subject, so a stack shot on a different optical path is rendered
    # without a coefficient that does not describe it.
    $caOn = $FixCa -and $caPath[$n]
    if ($caOn) { $env:STREHL_FIX_CA = $FixCa }
    else { Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue }
    $ca = if ($caOn) { $FixCa } elseif ($FixCa) { "off:path" } else { "off" }
    $frames = (Get-ChildItem -File $s.FullName |
        Where-Object { $_.Extension -match $RAW_EXT }).Count
    Write-Host ("[{0,2}/{1}] {2} ({3} frames)" -f $i, $subjects.Count, $n, $frames)

    $tif = Join-Path $raw "$n.tiff"
    $log = Join-Path $raw "$n.log"
    $p = Start-Process -FilePath $Exe `
        -ArgumentList @("stack", "`"$($s.FullName)`"", "--out", "`"$tif`"", "--srgb", "--demosaic") `
        -NoNewWindow -PassThru -RedirectStandardError $log -RedirectStandardOutput (Join-Path $raw "$n.out")
    # Reading the handle while the process is alive is what makes ExitCode
    # non-null afterwards; without it -PassThru reports $null and every render
    # silently "succeeds".
    $null = $p.Handle
    $p.WaitForExit()
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
    $zero = ""; $blown = ""
    if ($exit -eq 0 -and (Test-Path $tif)) {
        $jpg = Join-Path $work "$n.jpg"
        # Stamped into the JPEG itself, so one file taken out of the directory
        # can still say what produced it.
        $prov = "strehl gallery`nsubject $n`nbinary sha256 $exeSha`nSTREHL_FIX_CA $ca`nrendered $(Get-Date -Format o)`nlong edge $LongEdge"
        $viewOut = & python (Join-Path $PSScriptRoot "gallery_view.py") $tif $jpg $LongEdge $prov 2>&1
        $viewOut | Write-Host
        if ($LASTEXITCODE -ne 0) { Write-Warning "$n : view conversion failed" ; $jpg = "" ; $failed.Add("$n (view)") }
        # Per-channel, never combined. An all-three-channels count conceals
        # single-channel clipping completely, and that is the exact shape of
        # the tone defect that took coffee-bubbles to 88% zero-blue and
        # survived a whole gallery run unnoticed.
        $st = ($viewOut | Select-String -Pattern '^stats zero=(\S+) blown=(\S+)' | Select-Object -First 1)
        if ($st) { $zero = $st.Matches[0].Groups[1].Value; $blown = $st.Matches[0].Groups[2].Value }
        if (-not $KeepTiff) { Remove-Item $tif -Force -ErrorAction SilentlyContinue }
    } else {
        Write-Warning "$n : exit $exit -- see $log"
        $failed.Add("$n (exit $exit)")
    }

    # Guarded subjects are checked as they land, not at the end, so a run that
    # is degrading something can be stopped before it costs another 50 minutes.
    $guardState = ""
    if ($Guard -contains $n) {
        & python (Join-Path $PSScriptRoot "guard.py") `
            (Join-Path $work "$n.jpg") (Join-Path $GuardDir "$n.jpg") (Join-Path $work "_guard")
        $guardState = if ($LASTEXITCODE -eq 0) { "held" } else { "MOVED" }
        if ($guardState -eq "MOVED") { $guardMoved.Add($n) }
    }

    # NO peak-memory column. It was here, and it was not a measurement. Polled
    # on identical work (coffee-bubbles, 19 frames, same binary) it reported
    # 11, 16, 16, 84, 87, 163, 1180 and 1658 MB across five runs and two polling
    # methods -- the cached Process object with Refresh(), and a fresh
    # Get-Process each poll. In one run PeakVirtualMemorySize64 came back as 0,
    # which is impossible for a live process, so the counter is not being read
    # reliably through Start-Process at all. A verifier was right to flag the
    # old 5 MB figure for a 205-frame 33 MP stack.
    #
    # A number that reads as data in a recorded artifact and is wrong by two
    # orders of magnitude is worse than no number. The reliable way to get this
    # is to have the binary report its own peak via GetProcessMemoryInfo at
    # exit, which is a code change, not a script change. Until then the honest
    # statement is that no render has ever run out of memory: 26/26 subjects,
    # up to 299 frames at 33 MP, all exit 0.
  } catch {
    # One subject throwing must not cost the other 25. Record it as a failure
    # and carry on -- the run reaches its own reconciliation either way.
    Write-Warning "$n : gallery.ps1 threw -- $($_.Exception.Message)"
    $failed.Add("$n (script error: $($_.Exception.Message))")
  }
    $sw.Stop()
    $rows.Add(("{0}`t{1}`t{2}`t{3}`t{4}`t{5}`t{6}`t{7}`t{8}`t{9}`t{10}`t{11}" -f `
        $n, $frames, [int]$sw.Elapsed.TotalSeconds, $exit, $black, $white, $zero, $blown, `
        $(if ($jpg) { Split-Path $jpg -Leaf } else { "" }), $guardState, $exeShort, $ca))
    # Written every iteration, not at the end: a run that dies at subject 19
    # should still leave 18 rows of evidence behind.
    [IO.File]::WriteAllLines((Join-Path $work "manifest.tsv"), $rows, (New-Object Text.UTF8Encoding $false))
}

if (-not $KeepTiff) { Remove-Item $raw -Recurse -Force -ErrorAction SilentlyContinue }

# ---------------------------------------------------------------------------
# Reconcile the record with what actually happened, then publish -- or refuse.
# ---------------------------------------------------------------------------
$rendered = @(Get-ChildItem (Join-Path $work "*.jpg") -ErrorAction SilentlyContinue).Count
$complete = ($rendered -eq $subjects.Count) -and ($failed.Count -eq 0)

# RUN.txt asserted a subject count before the run had earned it. Now it states
# what was planned AND what was achieved, and the two are visibly different when
# they differ. A file that reads as data has to be data.
$run = $run | ForEach-Object {
    if ($_ -like "subjects rendered:*") { "subjects rendered: $rendered of $($subjects.Count)" } else { $_ }
}
if (-not $complete) {
    $run += ""
    $run += "INCOMPLETE. $rendered of $($subjects.Count) subjects produced a JPEG."
    if ($failed.Count -gt 0) { $run += "failed: $($failed -join ', ')" }
}
[IO.File]::WriteAllLines((Join-Path $work "RUN.txt"), $run, (New-Object Text.UTF8Encoding $false))

if ($complete) {
    # The sentinel is written LAST and only on success. Its absence is what
    # marks a directory as untrustworthy, which is the right polarity: a run
    # that is killed cannot write anything, so it cannot accidentally claim to
    # have succeeded.
    Remove-Item (Join-Path $work "INCOMPLETE.txt") -Force -ErrorAction SilentlyContinue
    [IO.File]::WriteAllText((Join-Path $work "COMPLETE.txt"),
        "$rendered of $($subjects.Count) subjects, binary $exeSha, $(Get-Date -Format o)`n")
} else {
    [IO.File]::WriteAllText((Join-Path $work "INCOMPLETE.txt"), (@(
        "INCOMPLETE GALLERY RUN -- $(Get-Date -Format o)"
        ""
        "$rendered of $($subjects.Count) subjects produced a JPEG."
        "failed: $(if ($failed.Count) { $failed -join ', ' } else { '(none reported; the run was cut short)' })"
        ""
        "Every JPEG here came from binary $exeSha, so this directory is"
        "COHERENT but PARTIAL. That is the deliberate trade: a missing subject is"
        "a missing subject, whereas a subject silently left over from a previous"
        "binary is a wrong answer that looks like a right one."
    ) -join "`n"))
}

if ($isFull -and $rendered -eq 0) {
    # Nothing rendered. Publishing an empty directory over a good gallery is
    # pure loss -- there is no sense in which zero coherent subjects beats the
    # last full run. Leave the staging dir as the evidence and touch nothing.
    $final = $work
    Write-Host ""
    Write-Warning "NOT PUBLISHED: 0 of $($subjects.Count) subjects rendered."
    Write-Warning "$OutDir is untouched. Failure evidence is in $work"
} elseif ($isFull) {
    # Wholesale replacement. The previous gallery is moved aside first and only
    # deleted once the new one is in place, so an interruption during the swap
    # leaves a recoverable directory rather than none.
    $prev = "$OutDir.prev-$stamp"
    if (Test-Path $OutDir) { Move-Item $OutDir $prev -Force }
    Move-Item $work $OutDir -Force
    if ($complete) {
        if (Test-Path $prev) { Remove-Item $prev -Recurse -Force -ErrorAction SilentlyContinue }
    } elseif (Test-Path $prev) {
        # An incomplete run still publishes, because coherent-and-partial beats
        # entirely stale and it is labelled either way. But the last full
        # gallery is KEPT rather than deleted, so there is always something
        # complete to fall back to when the new run is missing subjects.
        Write-Warning "previous gallery preserved at $prev (this run was incomplete)"
    }
    $final = $OutDir
    Write-Host ""
    Write-Host "gallery: $OutDir  ($rendered subjects, all from $exeShort)"
} else {
    # A -Only run renders a subset. Swapping it in would delete every subject it
    # did not render, which is precisely the mixing this is meant to prevent --
    # so a partial selection never becomes the canonical gallery.
    $final = $work
    Write-Host ""
    Write-Host "PARTIAL SELECTION (-Only): left at $work"
    Write-Host "It is deliberately NOT swapped into $OutDir, which still holds the last full run."
}

if (-not $complete) {
    Write-Host ""
    Write-Warning "RUN INCOMPLETE: $rendered of $($subjects.Count) subjects."
    if ($failed.Count -gt 0) { Write-Warning "failed: $($failed -join ', ')" }
    Write-Warning "See $(Join-Path $final 'INCOMPLETE.txt')"
}

# A dated copy of every run. `gallery/` stays the one path worth bookmarking, so
# "open the gallery" never changes meaning, and the history is what shows the
# trajectory -- three lanes are landing changes and the only way to know whether
# the product is getting better is to be able to put the runs side by side at
# viewing scale.
if (-not $NoHistory) {
    $hist = Join-Path (Split-Path $OutDir -Parent) "gallery-history\$stamp"
    New-Item -ItemType Directory -Force -Path $hist | Out-Null
    Copy-Item (Join-Path $final "*.jpg") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $final "RUN.txt") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $final "manifest.tsv") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $final "COMPLETE.txt") $hist -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $final "INCOMPLETE.txt") $hist -Force -ErrorAction SilentlyContinue
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
    Write-Host "  !! Look at $final\_guard\*-before-after.png BEFORE accepting this run." -ForegroundColor Red
    Write-Host "  !! These subjects were audited as good. If one moved, something aimed" -ForegroundColor Red
    Write-Host "  !! at a different picture reached them." -ForegroundColor Red
    Write-Host ""
}
Write-Host "gallery: $final"
if ($complete) {
    Write-Host "open it and look at the pictures."
} else {
    Write-Host "INCOMPLETE -- $rendered of $($subjects.Count). Read INCOMPLETE.txt before judging anything."
}
