# finalpass.ps1 -- ONE ARM of the acceptance corpus, from ONE pinned binary.
#
# WHAT THIS IS FOR
# ----------------
# ORCH's deciding artifact is a full-subject render from a single pinned binary
# with identical flags, scored by ORCH-CLAMP\accept.py and inspected as
# rule-sited 100% crops. accept.py compares ARMS of the same subject, so the
# natural unit of work is exactly this: one arm = one full-corpus pass. Run it
# once per candidate binary and point accept.py at the resulting directories.
#
# The current gallery cannot attribute anything because its arms differ in more
# than one way at once. Everything below exists to make that impossible here.
#
# THE FOUR RULES IT ENFORCES, rather than relies on an operator to remember
# ------------------------------------------------------------------------
#  1. ONE BINARY. Built from `git archive <sha>` into a private tree, so it
#     cannot contain another agent's uncommitted work -- five lanes share this
#     working tree and four files were dirty the last time I checked. The SHA
#     and the binary's own sha256 go in RUN.txt and in every arm's sidecar.
#  2. IDENTICAL FLAGS. One $Flags string is used for every subject and recorded
#     verbatim. accept.py's own docstring warns that absolute DN is comparable
#     only between arms rendered identically, and a camera-linear arm scored
#     against an sRGB reference read 82.6% acuity in ORCH's commissioning -- an
#     instrument correctly detecting a colour-space mismatch. Mixing flags
#     produces a table that looks fine and means nothing.
#  3. NAMING accept.py CAN PARSE. `<subject>--<arm>.tiff`. Asserted, because a
#     subject whose name contains `--` would silently split in the wrong place
#     and be scored as a different subject.
#  4. NO PARTIAL PASS EVER LOOKS COMPLETE. A killed run leaves INCOMPLETE.txt
#     (written first, survives a hard kill, which try/finally cannot) and a
#     finished run leaves COMPLETE.txt (written last, so a dead run cannot claim
#     success). Same discipline as gallery.ps1.
#
# WHY IT IS RESUMABLE, WHICH IS NOT TIDINESS
# ------------------------------------------
# A full pass is ~2 hours (see -WhatIfTiming). The last 26-subject run on this
# machine died to an OOM -- `allocation of 33003520 bytes failed`, 0xC0000409 --
# because stack.rs budgets a 6 GiB working set on the assumption that it owns
# the machine, which is false with five agents rendering. That constant is read
# at nineteen sites across stack.rs and merge_cmd.rs, so making it a knob is a
# real change in a file another agent holds tonight; it is logged for routing,
# not half-built here.
#
# What IS done here is refusing to let one dead subject cost the other 25:
# every subject is independent, an existing complete .tiff is skipped, and a
# failed subject is retried once at the END of the pass rather than immediately
# -- by then the run's own peak demand is over and a transient shortage caused
# by a neighbouring agent has had time to clear. Failures are recorded with
# their exit code so an OOM is distinguishable from a crash.
#
# SUBJECT ORDER IS LARGEST-FIRST, on purpose. The 299-frame stacks are the ones
# that fail on memory, and finding that out at minute 4 rather than minute 95 is
# the difference between losing a pass and losing a subject.

[CmdletBinding()]
param(
    # The commit to render from. Built into a private tree via `git archive`.
    [string]$Sha,

    # Arm label. Becomes the `--<arm>` suffix accept.py groups on.
    [Parameter(Mandatory = $true)][string]$Arm,

    # Flags applied to EVERY subject.
    #
    # --linear-srgb is the project's own stated answer to "what space is this
    # measured in": it applies the camera colour matrix to sRGB/BT.709 primaries
    # at D65 and then STOPS, before the transfer curve. Its help text is
    # unambiguous -- "THIS IS THE MODE TO MEASURE IN" -- and the reason is that
    # the only alternative, the bare default, uses the sensor's own primaries,
    # which are stated nowhere. A measurement was therefore either taken through
    # a curve or in an undeclared space. accept.py reads absolute DN, so the
    # space has to be declared for its table to mean anything.
    #
    # CAVEAT worth carrying: the colour matrix has negative off-diagonal terms,
    # so it can move a pixel across zero in either direction. clip% measured
    # here is therefore "negative after the matrix", not "negative at
    # blend-render.rs:572". To isolate the pre-matrix clamp, run a second arm
    # with -Flags '--demosaic' -- one flag apart, and this harness makes an
    # extra arm cheap. Do not put both in one arm.
    #
    # For print JUDGEMENT rather than measurement use '--srgb', in its own arm
    # with its own name. Never mix: a tone-mapped arm and a linear arm are not
    # two arms of one experiment.
    [string]$Flags = '--linear-srgb --demosaic',

    [string]$Library = 'D:\personal\macro',
    [string]$OutRoot = 'C:\dev\strehl-out\acceptance',
    [string]$PinRoot = 'C:\dev\strehl-out\acceptance-pins',

    # Render only these subjects. Diagnostic; a partial arm is marked as such.
    [string[]]$Only = @(),

    # Print the plan and the projected wall time, render nothing.
    [switch]$WhatIfTiming,

    # Use an existing binary instead of building a pin. For iterating on the
    # harness itself; a run made this way is recorded as UNPINNED.
    [string]$Exe,

    # WHICH LANDED FIXES THIS RENDER ENABLES.
    #
    #   none  (default)  every render-affecting variable cleared, nothing set.
    #                    This is the arm the byte-freeze registry pins, and it
    #                    must stay the default for that reason.
    #   ship             the integrated corpus render: every fix that has been
    #                    measured and accepted, switched on together, declared
    #                    once in $ShipRecipe below and carried into the
    #                    manifest, the sidecar and the reproduction command
    #                    from that single declaration.
    #
    # A third value is deliberately absent. An arm assembled ad hoc at the
    # command line is how C:\dev\strehl-out\ORCH-FAITHFUL\faithful\ came to
    # exist without a record of what produced it, and that directory is the
    # reason this parameter exists.
    [ValidateSet('none', 'ship')]
    [string]$Fixes = 'none',

    # Skip the graded presentation outputs and emit masters only.
    #
    # The presentation files exist because a faithful --srgb master is flat by
    # construction -- it applies the colour matrix and the transfer curve and
    # nothing else, which is correct for a master and is not what any raw
    # developer ships. A viewer judging the tool on unGRADED masters is judging
    # a rendering choice, not the stacking.
    #
    # They are written to a SEPARATE directory with its own warning file, and
    # they carry no provenance sidecar, deliberately: a sidecar would imply
    # they are reproducible measurement artifacts and they are not. Nothing
    # numeric may ever be computed from them -- they sit on the far side of both
    # a tone curve and a per-image percentile normalisation, so a gate fed one
    # would be measuring the grade.
    [switch]$NoPresent,

    # Long edge of the presentation JPEGs.
    #
    # THIS DEFAULT WAS 1400 AND THAT WAS A DELIVERY DEFECT. The masters are
    # 7032x4688, so a 1400px gallery is 19.9% of master width -- a 1.3 MP
    # thumbnail of a 33 MP focus stack, and the only file a viewer naturally
    # double-clicks. Every property this project is judged on lives above that
    # resolution: reconstruction gain is measured on 1:1 patches, the blur
    # budget closes to 2.6% at full scale, and halo absence was confirmed on
    # 1:1 grids. A 5x downscale puts all of it inside the resampling kernel.
    #
    # It is worse than merely uninformative. A 5x box-down of a correctly sharp
    # image looks SOFTER than a 5x box-down of an oversharpened one, so the
    # thumbnail inverts the very judgement it was being used to make.
    #
    # 0 means "full resolution, no resize", which is what a deliverable should
    # be. `scripts/deliver.py` writes the full-resolution gallery plus measured
    # 1:1 crops and is the thing to hand a viewer.
    [int]$PresentWidth = 0
)

$ErrorActionPreference = 'Stop'
# scripts/ is ONE level below the repo root. Asserted rather than assumed: the
# same mistake made from experiments/<dir>/ (which is two) surfaced four steps
# later as a null-array error with nothing pointing at the cause.
$repo = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $repo 'Cargo.toml'))) { throw "repo root not found at $repo" }

$RAW_EXT = '\.(ARW|arw)$'

# Measured on this machine, five agents live: 79 frames / 117 s and 100 frames /
# 148 s, both ~1.48 s/frame. Used only to project wall time; nothing depends on
# it being right.
$SECS_PER_FRAME = 1.48

# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
$subjects = Get-ChildItem -Directory $Library | ForEach-Object {
    $n = (Get-ChildItem -File $_.FullName | Where-Object { $_.Extension -match $RAW_EXT }).Count
    [pscustomobject]@{ Name = $_.Name; Path = $_.FullName; Frames = $n }
} | Where-Object { $_.Frames -gt 0 }

if ($Only.Count) {
    # `powershell -File ... -Only a,b` delivers ONE string "a,b", while an
    # in-process call delivers two. Splitting on commas makes both work; without
    # it the filter matches nothing and the script throws "no subjects found",
    # which points at the library rather than at the argument.
    $Only = $Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $missing = $Only | Where-Object { $_ -notin $subjects.Name }
    if ($missing) { throw "-Only names no such subject: $($missing -join ', ')" }
    $subjects = $subjects | Where-Object { $Only -contains $_.Name }
}

# accept.py splits on the FIRST '--', so a subject containing one would be
# filed under a truncated name and silently compared against nothing.
$bad = $subjects | Where-Object { $_.Name -like '*--*' }
if ($bad) { throw "subject name(s) contain '--' and would break accept.py parsing: $($bad.Name -join ', ')" }
if ($Arm -like '*--*') { throw "arm name must not contain '--': $Arm" }
if (-not $subjects) { throw "no subjects with frames found under $Library" }

# Largest first: the stacks that fail on memory fail early, not at minute 95.
# @() is not decoration: a single-subject -Only run makes Where-Object return a
# scalar, and $subjects.Count then read 0, which printed "[ 1/0]".
$subjects = @($subjects | Sort-Object Frames -Descending)
$nSubjects = $subjects.Count

$totalFrames = ($subjects | Measure-Object Frames -Sum).Sum
$projSecs = $totalFrames * $SECS_PER_FRAME

Write-Host ("subjects        : {0}" -f $nSubjects)
Write-Host ("frames          : {0:N0}" -f $totalFrames)
Write-Host ("projected wall  : {0:N0} min at {1} s/frame (measured under load)" -f ($projSecs / 60), $SECS_PER_FRAME)
Write-Host ("arm             : {0}" -f $Arm)
Write-Host ("flags           : {0}" -f $Flags)

if ($WhatIfTiming) {
    Write-Host ''
    Write-Host ("{0,-42}{1,7}{2,10}" -f 'subject', 'frames', 'proj s')
    foreach ($s in $subjects) { "{0,-42}{1,7}{2,10:N0}" -f $s.Name, $s.Frames, ($s.Frames * $SECS_PER_FRAME) }
    Write-Host ''
    Write-Host ("TOTAL {0:N0} frames, {1:N1} h projected" -f $totalFrames, ($projSecs / 3600))
    exit 0
}

# ---------------------------------------------------------------------------
# The pinned binary
# ---------------------------------------------------------------------------
if ($Exe) {
    if (-not (Test-Path $Exe)) { throw "no binary at $Exe" }
    $pinDesc = "UNPINNED (operator supplied $Exe)"
    $pinSha = 'UNPINNED'
} else {
    if (-not $Sha) { throw "-Sha is required unless -Exe is given" }
    Push-Location $repo
    $pinSha = (git rev-parse --short $Sha).Trim()
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "cannot resolve $Sha" }
    Pop-Location

    $pin = Join-Path $PinRoot $pinSha
    $Exe = Join-Path $pin 'target\release\strehl.exe'
    if (Test-Path $Exe) {
        Write-Host "pin             : reusing $pin"
    } else {
        Write-Host "pin             : building $pinSha (git archive; cannot contain uncommitted work)"
        if (Test-Path $pin) { Remove-Item $pin -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $pin | Out-Null
        Push-Location $repo
        # `git archive $sha | tar -x` CORRUPTS THE ARCHIVE on this machine.
        # PowerShell pipelines are streams of .NET objects, not bytes: the tar
        # is decoded to text and re-encoded on its way to tar.exe, so every
        # byte >= 0x80 is mangled. It fails as ~100 lines of "Damaged tar
        # archive (bad header checksum)" followed by cargo reporting no
        # Cargo.toml -- which reads like a git problem and is not one.
        #
        # Same defect class as `git show HEAD:path > tmp`, which silently
        # re-encodes and has already produced a false measurement here. The
        # rule is: NEVER move binary data through a PowerShell pipeline or
        # redirect. Write a real file with -o and let tar read it.
        $tarPath = Join-Path $PinRoot "$pinSha.tar"
        git archive --format=tar -o $tarPath $pinSha
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw "git archive failed for $pinSha" }
        Pop-Location
        tar -x -f $tarPath -C $pin
        if ($LASTEXITCODE -ne 0) { throw "tar extract failed for $pinSha" }
        Remove-Item $tarPath -Force
        # An extraction that silently produced nothing usable must fail HERE,
        # where the cause is legible, and not four steps later inside cargo.
        if (-not (Test-Path (Join-Path $pin 'Cargo.toml'))) {
            throw "pin $pinSha extracted no Cargo.toml -- the archive did not land"
        }
        Push-Location $pin
        $env:CARGO_TARGET_DIR = Join-Path $pin 'target'
        # cargo writes its progress to STDERR, and `2>&1 |` turns every one of
        # those lines into a PowerShell ERROR RECORD. With the file-level
        # $ErrorActionPreference = 'Stop' in force, the very first "Compiling
        # proc-macro2" then ABORTS the pass -- and it aborts with the compile
        # line as the message, so it reads as a compiler failure rather than as
        # the redirect it actually is. This only ever surfaced on a COLD pin,
        # because a warm one is reused and never runs cargo at all, which is
        # why a working harness could carry the bug for its whole life.
        #
        # Log to a file instead of a pipeline: no error records, and a cold
        # build's output survives for diagnosis instead of being truncated to
        # its last three lines.
        $buildLog = Join-Path $PinRoot "$pinSha.build.log"
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release -p strehl-cli --bin strehl `
            > $buildLog 2>&1
        $buildExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        Pop-Location
        Remove-Item Env:\CARGO_TARGET_DIR -ErrorAction SilentlyContinue
        if ($buildExit -ne 0) {
            Get-Content $buildLog -Tail 25 | Out-Host
            throw "pin build for $pinSha failed (exit $buildExit); full log at $buildLog"
        }
        if (-not (Test-Path $Exe)) { throw "pin build produced no binary at $Exe" }
        Write-Host "pin             : built, log at $buildLog"
    }
    $pinDesc = "$pinSha (git archive + clean release build)"
}
$binHash = (Get-FileHash $Exe -Algorithm SHA256).Hash
Write-Host ("binary sha256   : {0}" -f $binHash)

# Full 40-char commit, resolved once. With -Exe the operator supplied a binary
# we cannot attribute to a commit, and that must be SAID rather than left to
# read as "some commit": an unattributable binary is exactly the case where
# provenance matters most.
if ($pinSha -eq 'UNPINNED') {
    Push-Location $repo
    $head = (git rev-parse HEAD 2>$null)
    $dirty = (git status --porcelain 2>$null)
    Pop-Location
    $gitFull = "UNATTRIBUTED -- operator-supplied binary; tree HEAD was $($head.Trim())" +
    $(if ($dirty) { " WITH UNCOMMITTED CHANGES (the binary may not match any commit)" } else { "" })
} else {
    Push-Location $repo
    $gitFull = (git rev-parse $pinSha).Trim()
    Pop-Location
}
Write-Host ("git commit      : {0}" -f $gitFull)

# ---------------------------------------------------------------------------
# Output directory. One per arm, so accept.py can be handed several at once.
# ---------------------------------------------------------------------------
$out = Join-Path $OutRoot $Arm
New-Item -ItemType Directory -Force -Path $out | Out-Null

# Written FIRST. A hard kill leaves this behind; try/finally cannot help,
# because nothing in-process runs when the process is gone.
@(
    "THIS ARM IS INCOMPLETE."
    "If this file is still here, the pass did not finish and the arm must not"
    "be scored -- accept.py cannot tell a missing subject from a passing one."
    "started : $(Get-Date -Format o)"
    "arm     : $Arm"
    "pin     : $pinDesc"
) | Out-File -Encoding utf8 (Join-Path $out 'INCOMPLETE.txt')
Remove-Item (Join-Path $out 'COMPLETE.txt') -ErrorAction SilentlyContinue

$manifest = Join-Path $out 'manifest.tsv'
if (-not (Test-Path $manifest)) {
    "subject`tframes`tsecs`texit`tbytes`tstatus`texposure_stops`tviewable`tgraded" |
        Out-File -Encoding utf8 $manifest
}

# Presentation outputs live apart from the masters and say so on the tin, so a
# graded JPEG can never be picked up by a glob that meant to find a master.
$presentDir = Join-Path $out '_presentation'
$faithfulDir = Join-Path $out '_faithful'
if (-not $NoPresent) {
    New-Item -ItemType Directory -Force -Path $presentDir, $faithfulDir | Out-Null
    @(
        "PRESENTATION ONLY -- DO NOT MEASURE ANYTHING FROM THESE FILES."
        ''
        'These JPEGs are GRADED: a percentile black point, a filmic S-curve and'
        'a saturation lift have been applied on top of the master. They exist so'
        'a photographer can judge the pictures, because a faithful --srgb master'
        'is flat by construction and reads as poor work when it is not.'
        ''
        'They sit on the far side of BOTH a tone curve and a per-image'
        'percentile normalisation. Two consequences:'
        '  - No gate, metric or A/B comparison may be fed one. The standing'
        '    project rule is that nothing numeric crosses a tone curve, and the'
        '    percentile step additionally makes each file scaled differently'
        '    from every other, so even comparing two of these to each other is'
        '    measuring the grade rather than the render.'
        '  - They are 8-bit and JPEG. Fine detail and rim artifacts are exactly'
        '    what JPEG discards; judge those on the masters at 100%.'
        ''
        'The faithful, measurable artifacts are the .tiff masters beside this'
        'directory, each with a .provenance.txt sidecar. ../_faithful holds an'
        '8-bit UNgraded reduction of each master, for seeing what the master'
        'itself looks like; it is still 8-bit JPEG and still not a measurement'
        'surface.'
    ) | Out-File -Encoding utf8 (Join-Path $presentDir 'DO-NOT-MEASURE.txt')
}

# STREHL_FIX_CA is set EXPLICITLY in both directions. Since 96571ee an absent
# variable no longer means off -- it means "let the binary's gear guard decide"
# -- so leaving it unset would make the arm's colour path depend on the calling
# shell. Every other variable that re-routes a render is cleared for the same
# reason.
#
# THIS LIST USED TO BE TYPED OUT HERE, with a comment saying it mirrored
# byte-freeze.rs's RENDER_ENV. It did not. Measured 2026-08-27: RENDER_ENV held
# 23 names and this list held 15, so EIGHT variables that re-route a render were
# never cleared --
#
#   STREHL_GATE_FLOOR      moves the noise floor, and so moves which
#                          coefficients are averaged rather than selected
#   STREHL_DEFECT          )
#   STREHL_DEFECT_MAP      ) the sensor defect correction, which rewrites
#   STREHL_DEFECT_ARM      ) photosites BEFORE the warp
#   STREHL_DEFECT_HOT_FLOOR)
#   STREHL_ACUITY
#   STREHL_FULLRES_GATHER  selects what every output pixel is interpolated FROM
#   STREHL_PHOTOMETRIC
#
# -- which means an operator with any of them exported rendered a different
# image from the one this harness reports, and nothing in the run would say so.
# That is precisely the STREHL_ALIGN=0 defect the byte-freeze registry header
# documents, committed a third time, in the file whose job is provenance.
#
# A duplicated list is a claim that has to be re-checked by hand every time
# somebody else edits the original, and this one silently stopped being true.
# So it is PARSED from the freeze registry instead. If the parse fails, or
# returns fewer names than the smallest plausible list, this script refuses to
# render rather than clearing a subset and reporting confidence.
function Get-RenderEnv {
    $src = Join-Path $repo 'crates\strehl-cli\tests\byte-freeze.rs'
    if (-not (Test-Path $src)) { return @() }
    $t = Get-Content $src -Raw
    $m = [regex]::Match($t, 'const RENDER_ENV: &\[&str\] = &\[(.*?)\n\];', 'Singleline')
    if (-not $m.Success) { return @() }
    return [regex]::Matches($m.Groups[1].Value, '"(STREHL_[A-Z_0-9]+)"') |
        ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
}
$ClearedSwitches = @(Get-RenderEnv)
if ($ClearedSwitches.Count -lt 15) {
    throw ("REFUSING TO RENDER: parsed only $($ClearedSwitches.Count) name(s) from " +
        "RENDER_ENV in crates/strehl-cli/tests/byte-freeze.rs. That list is the " +
        "project's record of which environment variables change a render, and this " +
        "harness clears it so that a render does not depend on the calling shell. " +
        "A short parse means the guard is partial, and a partial guard reports the " +
        "same confidence as a whole one.")
}
foreach ($v in $ClearedSwitches) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# THE SHIP RECIPE: ONE DECLARATION OF WHAT THE INTEGRATED RENDER ENABLES.
#
# Everything downstream reads this table and nothing re-states it: the
# environment is set from it, the liveness preflight probes it, the per-subject
# manifest records it, and the sidecar's reproduction command is generated from
# it. That is the point. A recipe written in one place and re-typed in a second
# is the defect that was sitting in this very file -- $ClearedSwitches claimed
# in a comment to mirror byte-freeze.rs's RENDER_ENV and had silently stopped
# doing so, eight variables short, including all four of the ones below.
#
# `Bad` is a value the binary must REJECT. It is not decoration: it is how the
# preflight proves the running binary can still see the variable at all. See
# Assert-RecipeIsLive.
$ShipRecipe = @(
    [pscustomobject]@{
        Name  = 'STREHL_DEFECT'
        Value = 'on'
        Bad   = 'xyzzy-not-a-setting'
        Why   = 'master switch for sensor defect correction; off by default because a stale map manufactures the defect it removes'
    }
    [pscustomobject]@{
        Name  = 'STREHL_DEFECT_MAP'
        Value = (Join-Path $repo 'experiments\BUILD-DEFECT\out\defect-map-ILCE-7CM2-photo.txt')
        Bad   = 'C:\no-such-defect-map-xyzzy.txt'
        Why   = 'the photograph-derived map. NOT defect-map-ILCE-7CM2.txt, which is headered SUPERSEDED: three of its four motes read POSITIVE on real subjects'
    }
    [pscustomobject]@{
        Name  = 'STREHL_DEFECT_ARM'
        Value = 'dust'
        Bad   = 'dsut'
        Why   = 'dust only. The hot arm is a separately measured 14626-site census and ships OFF: M101 measured it immaterial on this body, and 14626 corrections that change nothing are 14626 chances to change something'
    }
)

# ---------------------------------------------------------------------------
# LIVENESS: REFUSE TO RENDER A FIX THE BINARY CANNOT SEE.
#
# The failure this prevents, stated concretely because it has happened twice on
# this project: a variable is exported, the render runs, the manifest records
# the variable as set, and the binary never read it -- because it was renamed,
# because the build predates it, or because it is gated behind another
# variable. Every artifact then says the fix was on. Nothing measured whether
# it was reachable.
#
# TWO MEASUREMENTS SHAPE THIS CHECK, AND NEITHER IS OBVIOUS.
#
# 1. A NON-ZERO EXIT IS NOT EVIDENCE. Handing the binary a bad subject path
#    with STREHL_DEFECT_ARM="dsut" set exits 1 in 0.45 s -- with
#    `Error: reading C:\no-such-dir-xyz`. The arm was never parsed. A liveness
#    probe that only tested the exit code would have passed on a dead variable
#    with a message about something else entirely. So the probe uses a REAL
#    subject, and requires the failure text to quote the sentinel value back.
#    Echoing the value is what proves the parse was reached.
#
# 2. THE ORIGINAL PATTERN IS CONDITIONAL. `STREHL_DEFECT_ARM="dsut"` on a real
#    subject with STREHL_DEFECT unset exits **0** and renders normally: the arm
#    is only parsed once the master switch is on. A probe that set one variable
#    at a time would therefore have found STREHL_DEFECT_ARM dead on a binary
#    where it is perfectly alive. Each probe applies the WHOLE recipe and
#    corrupts exactly one entry.
#
# The detector is commissioned in both directions, because a probe that always
# reports LIVE and a fix that is genuinely live give the identical green:
#   positive : the intact recipe must render (exit 0). If it cannot, the recipe
#              is broken and every LIVE verdict below is meaningless.
#   negative : STREHL_NOT_A_REAL_VARIABLE, corrupted the same way, must read
#              NOT LIVE. If a name the binary has never heard of reads LIVE,
#              the probe is measuring nothing.
function Invoke-Probe {
    param([hashtable]$Env, [string]$Subject, [string]$Tag)

    $tmp = Join-Path ([IO.Path]::GetTempPath()) "finalpass-probe-$Tag.tiff"
    $errf = Join-Path ([IO.Path]::GetTempPath()) "finalpass-probe-$Tag.err"
    $outf = "$errf.out"
    $saved = @{}
    foreach ($k in $Env.Keys) {
        $saved[$k] = [Environment]::GetEnvironmentVariable($k)
        Set-Item "Env:\$k" $Env[$k]
    }
    try {
        $p = Start-Process -FilePath $Exe -NoNewWindow -PassThru `
            -ArgumentList @('stack', "`"$Subject`"", '--out', "`"$tmp`"", '--limit', '2',
            '--linear-srgb', '--demosaic') `
            -RedirectStandardError $errf -RedirectStandardOutput $outf
        $null = $p.Handle
        $p.WaitForExit()
        $text = ''
        foreach ($f in @($errf, $outf)) {
            if (Test-Path $f) { $text += (Get-Content $f -Raw -ErrorAction SilentlyContinue) }
        }
        return [pscustomobject]@{ Exit = $p.ExitCode; Text = $text }
    }
    finally {
        foreach ($k in $Env.Keys) {
            if ($null -eq $saved[$k]) { Remove-Item "Env:\$k" -ErrorAction SilentlyContinue }
            else { Set-Item "Env:\$k" $saved[$k] }
        }
        Remove-Item $tmp, $errf, $outf -ErrorAction SilentlyContinue
    }
}

function Assert-RecipeIsLive {
    param([object[]]$Recipe, [string]$Subject)

    Write-Host "  preflight: probing $($Recipe.Count) recipe switch(es) against the binary that will render"
    $base = @{}
    foreach ($e in $Recipe) { $base[$e.Name] = $e.Value }

    # POSITIVE CONTROL. The intact recipe must render.
    $ok = Invoke-Probe -Env $base -Subject $Subject -Tag 'positive'
    if ($ok.Exit -ne 0) {
        $why = ($ok.Text -split "`n" | Where-Object { $_ -match 'Error|Caused' } | Select-Object -First 3) -join ' / '
        throw ("REFUSING TO RENDER: the intact ship recipe does not render. exit $($ok.Exit). $why`n" +
            "  Every liveness verdict is measured by CORRUPTING this recipe, so if the " +
            "uncorrupted form cannot run, a 'not live' reading would be indistinguishable " +
            "from a recipe that is simply wrong.")
    }
    Write-Host "    positive control  : intact recipe renders (exit 0)"

    # NEGATIVE CONTROL. A name the binary never heard of must NOT read live.
    $fakeEnv = $base.Clone()
    $fakeEnv['STREHL_NOT_A_REAL_VARIABLE'] = 'xyzzy-sentinel-nonexistent'
    $fake = Invoke-Probe -Env $fakeEnv -Subject $Subject -Tag 'negative'
    $fakeLive = ($fake.Exit -ne 0 -and $fake.Text -match [regex]::Escape('xyzzy-sentinel-nonexistent'))
    if ($fakeLive) {
        throw ("REFUSING TO RENDER: the liveness probe reported a variable the binary has " +
            "never heard of (STREHL_NOT_A_REAL_VARIABLE) as LIVE. The probe is not " +
            "measuring reachability and its verdicts below cannot be trusted.")
    }
    Write-Host "    negative control  : STREHL_NOT_A_REAL_VARIABLE reads NOT LIVE, as it must"

    $verdicts = @()
    $live = 0; $dead = 0
    foreach ($e in $Recipe) {
        $env2 = $base.Clone()
        $env2[$e.Name] = $e.Bad
        $r = Invoke-Probe -Env $env2 -Subject $Subject -Tag $e.Name
        $echoed = ($r.Text -match [regex]::Escape($e.Bad))
        $isLive = ($r.Exit -ne 0 -and $echoed)
        if ($isLive) { $live++ } else { $dead++ }
        $err = (($r.Text -split "`r?`n" | Where-Object { $_ -match '^Error|^\s+' -and $_ -match [regex]::Escape($e.Bad) } |
                Select-Object -First 1) -replace '\s+', ' ').Trim()
        $verdicts += [pscustomobject]@{
            Name = $e.Name; Value = $e.Value; Live = $isLive
            Exit = $r.Exit; Echoed = $echoed
            Evidence = $(if ($err) { $err } else { "(no line quoted $($e.Bad); exit $($r.Exit))" })
        }
        Write-Host ("    {0,-24} {1}  exit {2}" -f $e.Name, $(if ($isLive) { 'LIVE    ' } else { 'NOT LIVE' }), $r.Exit)
    }

    if ($live + $dead -ne $Recipe.Count) {
        throw "REFUSING TO RENDER: liveness partition does not sum -- $live live + $dead dead != $($Recipe.Count) probed."
    }
    if ($dead -gt 0) {
        $names = ($verdicts | Where-Object { -not $_.Live } | ForEach-Object { $_.Name }) -join ', '
        throw ("REFUSING TO RENDER: $dead of $($Recipe.Count) recipe switch(es) are NOT REACHABLE " +
            "in this binary -- $names.`n" +
            "  This render would have produced masters whose manifest said the fix was on " +
            "while the binary ignored it. Rebuild, or correct the recipe.")
    }
    Write-Host "    $live of $($Recipe.Count) live, 0 dead -- recipe is reachable in this binary"
    return $verdicts
}

$RecipeApplied = @()
$RecipeLiveness = @()
if ($Fixes -eq 'ship') {
    foreach ($e in $ShipRecipe) {
        if ($e.Name -eq 'STREHL_DEFECT_MAP' -and -not (Test-Path $e.Value)) {
            throw ("REFUSING TO RENDER: -Fixes ship names a defect map that does not exist:`n" +
                "  $($e.Value)`n" +
                "  Rendering without it would silently produce the uncorrected corpus while " +
                "the manifest recorded the correction as enabled.")
        }
    }
    $probeSubject = ($subjects | Sort-Object Frames | Select-Object -First 1).Path
    Write-Host "SHIP RECIPE: $($ShipRecipe.Count) switch(es); probe subject $(Split-Path $probeSubject -Leaf)"
    $RecipeLiveness = Assert-RecipeIsLive -Recipe $ShipRecipe -Subject $probeSubject
    foreach ($e in $ShipRecipe) {
        Set-Item "Env:\$($e.Name)" $e.Value
        $RecipeApplied += $e
    }
}
else {
    Write-Host "FIXES: none -- every render-affecting variable cleared, nothing set (byte-freeze arm)"
}

# ---------------------------------------------------------------------------
# RESOLVED SWITCH STATE, EMITTED AGAINST THE REGISTRY.
#
# Provenance that lists argv alone is a partial record wearing the word
# "verbatim". Most of this product's quality switches are ENVIRONMENT
# VARIABLES, not flags: STREHL_FIX_CA, STREHL_FIX_HALO, STREHL_EDGE_AWARE,
# STREHL_PHOTOMETRIC, STREHL_WINDOW_RADIUS and the rest never appear in argv
# however they are set, so an argv-only sidecar cannot distinguish a run with
# the halo fix on from one with it off, and its "REPRODUCE THIS EXACT FILE"
# line is not sufficient to reproduce the file: someone with a different
# environment gets different pixels and a sidecar saying they should not have.
#
# On 2026-08-26 that silence cost real time. A reviewer read a sidecar, saw no
# --fix-ca in the argv, and concluded -- correctly, from the evidence the
# sidecar offered -- that the owner's final masters had been rendered with
# lateral-CA correction switched off. They had not been. The binary's gear
# guard defaults it ON when the gear matches, and the binary's own banner said
# `lateral CA: CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (gear matched;
# default on)` on all 26 subjects. Nothing in the sidecar could show that, so
# the absence of a flag read as the absence of a correction.
#
# Two things follow, and this block does both. Record the RESOLVED state of
# every registry switch INCLUDING THE UNSET ONES, because unset is exactly the
# case that has burned this project -- an omitted line is indistinguishable
# from a switch nobody thought about. And record what the BINARY ITSELF said
# it did, because only the binary knows the outcome of a gear guard: the
# environment says "unset" in both the corrected and uncorrected cases.
#
# The registry is parsed from scripts/check-defaults.py rather than duplicated
# here, so a switch added there is covered here without anyone remembering to.
function Get-SwitchRegistry {
    $src = Join-Path $PSScriptRoot 'check-defaults.py'
    $reg = [ordered]@{}
    if (-not (Test-Path $src)) { return $reg }
    $lines = Get-Content $src
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\s{4}"(STREHL_[A-Z_0-9]+)":\s*Declared\(') {
            $key = $Matches[1]
            $def = '(not declared)'
            $bk = '(unclassified)'
            for ($j = $i + 1; $j -lt [Math]::Min($i + 60, $lines.Count); $j++) {
                if ($lines[$j] -match '^\s{4}"STREHL_') { break }
                if ($def -eq '(not declared)' -and $lines[$j] -match '^\s*default\s*=\s*"([^"]*)"') {
                    $def = $Matches[1]
                }
                if ($lines[$j] -match '^\s*backend\s*=\s*"([^"]*)"') { $bk = $Matches[1] }
            }
            $reg[$key] = [pscustomobject]@{ Default = $def; Backend = $bk }
        }
    }
    return $reg
}
$RegistrySwitches = Get-SwitchRegistry
if ($RegistrySwitches.Count -eq 0) {
    throw "REFUSING TO RENDER: could not parse the switch registry from check-defaults.py. Provenance would silently omit every environment switch, which is the exact defect this block exists to prevent."
}

function New-Presentation {
    # Master -> faithful 8-bit viewable -> GRADED presentation JPEG.
    #
    # Idempotent, and called from the resume path as well as the render path.
    # Without that a subject whose grading failed on the first pass could never
    # be repaired by re-running, because the master would then exist and the
    # whole subject would be skipped -- the failure would become permanent and
    # invisible.
    param($Name, [string]$Tif)

    if ($NoPresent) { return @{ Viewable = 'off'; Graded = 'off' } }
    if (-not (Test-Path $Tif)) { return @{ Viewable = 'nomaster'; Graded = 'nomaster' } }

    $fj = Join-Path $faithfulDir "$Name.jpg"
    $gj = Join-Path $presentDir "$Name.jpg"
    if ((Test-Path $fj) -and (Test-Path $gj)) { return @{ Viewable = 'skip'; Graded = 'skip' } }

    $vlog = Join-Path $out "$Name--$Arm.present.log"
    $viewState = '-'; $gradeState = '-'
    try {
        # Redirected to a file rather than piped: captured `& $exe 2>&1` yields
        # ErrorRecord objects that stringify unpredictably downstream, which is
        # a trap already live elsewhere in this project's own scripts.
        & python (Join-Path $repo 'scripts\viewable.py') $Tif $fj --maxw $PresentWidth *> $vlog
        $viewState = $(if (Test-Path $fj) { 'ok' } else { 'fail' })
        if ($viewState -eq 'ok') {
            & python (Join-Path $repo 'experiments\ORCH-drift-check\grade.py') `
                $fj $gj --single --maxw $PresentWidth --label 'PRESENTATION' *>> $vlog
            $gradeState = $(if (Test-Path $gj) { 'ok' } else { 'fail' })
        } else { $gradeState = 'skip' }
    } catch {
        Write-Warning "present ${Name}: $_"
        if ($viewState -eq '-') { $viewState = 'threw' }
        if ($gradeState -eq '-') { $gradeState = 'threw' }
    }
    return @{ Viewable = $viewState; Graded = $gradeState }
}

function Invoke-Subject {
    param($S, [int]$Index, [int]$Total, [string]$Note)

    $tif = Join-Path $out "$($S.Name)--$Arm.tiff"
    $log = Join-Path $out "$($S.Name)--$Arm.log"

    if ((Test-Path $tif) -and ((Get-Item $tif).Length -gt 0) -and (Test-Path "$tif.ok")) {
        $pr = New-Presentation -Name $S.Name -Tif $tif
        Write-Host ("[{0,2}/{1}] {2} -- already rendered, skipping{3}" -f $Index, $Total, $S.Name,
            $(if ($pr.Graded -eq 'ok') { ' (graded now)' } else { '' }))
        return [pscustomobject]@{ Name = $S.Name; Frames = $S.Frames; Secs = 0; Exit = 0
            Bytes = (Get-Item $tif).Length; Status = 'skip'
            Viewable = $pr.Viewable; Graded = $pr.Graded
        }
    }
    Remove-Item "$tif.ok" -ErrorAction SilentlyContinue

    Write-Host ("[{0,2}/{1}] {2} ({3} frames){4}" -f $Index, $Total, $S.Name, $S.Frames, $Note)
    $argv = @('stack', "`"$($S.Path)`"", '--out', "`"$tif`"") + ($Flags -split '\s+' | Where-Object { $_ })

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $Exe -ArgumentList $argv -NoNewWindow -PassThru `
        -RedirectStandardError $log -RedirectStandardOutput "$log.out"
    # Reading .Handle while it is alive is what makes ExitCode non-null after;
    # without it -PassThru reports $null and every render "succeeds".
    $null = $p.Handle
    $p.WaitForExit()
    $sw.Stop()

    $exit = $p.ExitCode
    $bytes = if (Test-Path $tif) { (Get-Item $tif).Length } else { 0 }
    $status = if ($exit -eq 0 -and $bytes -gt 0) { 'ok' }
    elseif ($exit -eq -1073740791 -or $exit -eq 3221226356) { 'OOM/abort' }
    else { "fail($exit)" }

    # PROVENANCE, BESIDE THE ARTIFACT.
    #
    # A central _render.log answers "what produced this?" only while the log and
    # the TIFF stay together. They do not: masters get copied into galleries and
    # crop directories, and twice tonight an agent inferred a render's backend
    # from its FILENAME and reached a wrong conclusion. So every master carries
    # its own sidecar, and the reproduction command is written out in full
    # rather than left to be reassembled.
    #
    # The exposure line is not decoration -- but it is an OBSERVATION, not an
    # INSTRUCTION, and this script used to confuse the two.
    #
    # --auto-exposure chooses the gain FROM THE IMAGE, so the flags alone do not
    # determine the pixels, and the binary quantises the choice to 1/100 stop
    # precisely "so that the printed number reproduces the file exactly". That
    # much is true and is why the number is still captured below.
    #
    # What was wrong was the conclusion drawn from it: that the reproduction
    # command should therefore SUBSTITUTE `--exposure <stops>` for
    # `--auto-exposure`. Measured (78-crossbinary.py, commissioned RED at 31,792
    # DN on a planted --limit 8 -> 6 and GREEN at 0 DN on a null):
    #
    #   verbatim flags, binary named in the sidecar : 0 DN over 98,898,048
    #       samples, both subjects. Bit-exact. The substitution was never
    #       load-bearing for the case it was written for.
    #   substituted flags, later binary : 109MSDCF 85.5637% of pixels clipped
    #       and a pure-white median 65535, against this file's 0.0012% and
    #       61007. foam 15.0839% against 0.0839%.
    #   verbatim flags, later binary : 109MSDCF 0.0013% clipped, median 61091.
    #       foam 0.0840%, median 26973. The exposure survives the binary change.
    #
    # The substitution was correct only because `--exposure` happened to be
    # inert in the binary that emitted the sidecars. A command that is right for
    # a reason unrelated to what it says is one binary away from being wrong,
    # and surviving a binary change is the entire purpose of the sidecar. So the
    # flags are now emitted VERBATIM and the chosen gain is reported beside them
    # as something the run observed. See docs/research/BUILD-DEFECT.md section 22.
    $binaryOut = @()
    foreach ($f in @("$log.out", $log)) {
        if (Test-Path $f) { $binaryOut += Get-Content $f -ErrorAction SilentlyContinue }
    }
    $expo = ($binaryOut | Where-Object { $_ -match '^\s*exposure\s*:' } | Select-Object -First 1)
    $expoStops = if ($expo -match '([+-]?\d+\.\d+)\s*stops') { $Matches[1] } else { $null }
    $backend = if ($Flags -match '--merge\s+(\S+)') { $Matches[1] } else { 'pyramid (default)' }
    $gate = if ($Flags -match '--pyramid-gate\s+(\S+)') { "--pyramid-gate $($Matches[1])" }
    elseif ($Flags -match '--gate\s+(\S+)') { "--gate $($Matches[1])" }
    else { '(backend default)' }
    $space = if ($Flags -match '--linear-srgb') { 'linear sRGB -- MEASURABLE' }
    elseif ($Flags -match '--srgb') { 'sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY' }
    else { 'camera-native binned linear -- MEASURABLE (primaries are the sensor''s own)' }

    # Emitted VERBATIM. See the measurement in the comment block above: pinning
    # the chosen gain into the command destroys the image on any binary where
    # `--exposure` is load-bearing, and buys nothing on the binary that wrote
    # it. $repro is kept as a distinct name so that any future transform has one
    # place to live and one place to be tested.
    $repro = $Flags

    # THE REPRODUCTION COMMAND MUST CARRY THE ENVIRONMENT, NOT JUST THE ARGV.
    #
    # The line above is the flag half and it used to be the whole of it. That
    # was sound only while this harness set nothing: the moment -Fixes ship
    # exports STREHL_DEFECT, an argv-only command reproduces a DIFFERENT image
    # -- the uncorrected one -- while claiming to be exact. The sidecar's own
    # RESOLVED SWITCH STATE block has said for weeks that "environment
    # variables never appear in argv however they are set"; the reproduction
    # line was the one place that had not acted on it.
    #
    # Both halves are emitted, and in this order, because either alone is
    # wrong:
    #   CLEAR  every render-affecting variable, so an operator with something
    #          exported in their shell does not silently get a third image.
    #          The names come from the same parsed RENDER_ENV the harness
    #          itself clears, so this cannot drift from what actually ran.
    #   SET    exactly the recipe entries this render applied -- nothing if the
    #          run was -Fixes none, which then reads as a positive statement
    #          that nothing was set rather than as an omission.
    $reproEnv = @()
    $reproEnv += "  # clear every render-affecting variable ($($ClearedSwitches.Count) from RENDER_ENV):"
    $reproEnv += "  @('" + (($ClearedSwitches | Sort-Object) -join "','") + "') |"
    $reproEnv += "      ForEach-Object { Remove-Item `"Env:\`$_`" -ErrorAction SilentlyContinue }"
    if ($RecipeApplied.Count -gt 0) {
        $reproEnv += "  # then set the $($RecipeApplied.Count) switch(es) this render applied:"
        foreach ($e in $RecipeApplied) {
            $reproEnv += "  `$env:$($e.Name) = '$($e.Value)'"
        }
    }
    else {
        $reproEnv += "  # this render applied NO switches (-Fixes none); set nothing."
    }

    # Resolved state of every registry switch, set and unset alike.
    #
    # A switch is reported against THE BACKEND THIS RENDER ACTUALLY RAN. The
    # registry classifies some switches as estimator-only, and the shipping
    # backend is the pyramid, which never reaches them. Printing those as
    # "default: off" invites exactly the inference that cost this project an
    # evening: an absent stage read as a disabled one. They are marked
    # INAPPLICABLE instead, which is a different fact from being switched off.
    $renderBackend = if ($backend -match 'pyramid') { 'pyramid' }
    elseif ($backend -match 'estimator') { 'estimator' }
    else { 'unknown' }
    $switchSet = 0
    $switchNA = 0
    $switchOK = 0
    $switchUnk = 0
    $switchLines = @()
    foreach ($k in $RegistrySwitches.Keys) {
        $d = $RegistrySwitches[$k]
        $unk = ($d.Backend -eq '(unclassified)')
        $na = (-not $unk -and $d.Backend -ne 'any' -and $renderBackend -ne 'unknown' -and $d.Backend -ne $renderBackend)
        $val = [Environment]::GetEnvironmentVariable($k)
        if ($na) { $switchNA++ } elseif ($unk) { $switchUnk++ } else { $switchOK++ }
        $tail = if ($unk) { '; backend applicability UNCLASSIFIED in the registry' } else { '' }
        if ($null -ne $val -and $val -ne '') {
            $switchSet++
            $src = if ($ClearedSwitches -contains $k) {
                'ENVIRONMENT -- set AFTER the harness cleared it'
            }
            else {
                'ENVIRONMENT -- and this harness does not clear it'
            }
            if ($na) { $src += "; INAPPLICABLE -- $($d.Backend)-only, this render was $renderBackend" }
            $switchLines += ('  {0,-26} = {1,-18} [{2}{3}]' -f $k, $val, $src, $tail)
        }
        elseif ($na) {
            $switchLines += ('  {0,-26} = {1,-18} [INAPPLICABLE -- {2}-only stage; this render was {3}, which never reaches it]' -f
                $k, '(n/a)', $d.Backend, $renderBackend)
        }
        else {
            $how = if ($ClearedSwitches -contains $k) { 'cleared by harness' } else { 'not set' }
            $switchLines += ('  {0,-26} = {1,-18} [{2}; built-in default: {3}{4}]' -f
                $k, '(unset)', $how, $d.Default, $tail)
        }
    }

    # What the BINARY said it resolved to. The environment cannot answer this:
    # STREHL_FIX_CA is unset both when CA is corrected and when it is not, and
    # only the gear guard's own line distinguishes them.
    #
    # This was a whitelist of six keys and it dropped 21 of the binary's 27
    # reported settings, including `alignment : ON ... N placed / N refused`,
    # the resampler, the colour transform, and -- worst -- `not applied : ...
    # outlier rejection, halo correction`, which is the binary stating its own
    # ABSENT stages. That last line is exactly the fact this project spent an
    # evening inferring wrongly from an argv. A whitelist silently drops
    # whatever nobody thought to enumerate, which is the same defect as an
    # omitted switch, so the whole self-report is now carried VERBATIM and the
    # extract below is only an index into it.
    $resolvedKeys = 'merge backend|camera|lateral CA|alignment|not applied|base band|colour|noise model|bands|selection|iso'
    $binaryState = $binaryOut |
        Where-Object { $_ -match "^\s*($resolvedKeys)\s*:" } |
        ForEach-Object { '  ' + $_.Trim() }
    $binaryVerbatim = @($binaryOut | ForEach-Object { '  | ' + $_ })
    $binaryKeyCount = @($binaryOut | Where-Object { $_ -match '^\s*[a-z][a-z0-9 /_+-]{2,20}\s*:\s*\S' }).Count

    # PER-SUBJECT DEFECT ACCOUNTING, PARSED FROM THE BINARY'S OWN PARTITION.
    #
    # The binary prints `--- defect correction (MEASURED) ---` with a counted
    # partition per arm. It is lifted into the sidecar and the manifest rather
    # than summarised, for the reason the partition exists at all: `corrected 0`
    # and `examined 0` are different facts and a single "0 corrected" line
    # reports them identically. One means the map was applied and this frame had
    # nothing to fix. The other means nothing ran.
    #
    # `Applied = $false` is therefore recorded as its own state, distinct from
    # both. If the block is absent the sidecar says the correction did not run,
    # which is the honest reading of a missing measurement.
    $defectLines = @($binaryOut | Where-Object {
            $_ -match '^\s*(hot|dust)\s*:\s*examined' -or
            $_ -match '^\s*(defect map|samples changed|sites)\s*:' -or
            $_ -match '^\s*site\s*\(' })
    $defectCounts = [ordered]@{}
    foreach ($ln in $defectLines) {
        if ($ln -match '^\s*(hot|dust)\s*:\s*(.+)$') {
            $arm = $Matches[1]
            foreach ($m in [regex]::Matches($Matches[2], '([a-z][a-z ]*?)\s+(\d+)')) {
                $defectCounts["$arm.$(($m.Groups[1].Value).Trim() -replace ' ','_')"] = [int]$m.Groups[2].Value
            }
        }
    }
    $defectApplied = ($defectLines | Where-Object { $_ -match 'examined' }).Count -gt 0

    @(
        "strehl render provenance"
        "artifact      : $(Split-Path $tif -Leaf)"
        "rendered      : $(Get-Date -Format o)"
        "status        : $status   (exit $exit, $bytes bytes)"
        ""
        "binary        : $Exe"
        "sha256        : $binHash"
        "git commit    : $gitFull"
        "pin           : $(if ($Sha) { $Sha } else { 'UNPINNED (operator-supplied -Exe)' })"
        ""
        "source        : $($S.Path)"
        "frames        : $($S.Frames)"
        "backend       : $backend"
        "gate          : $gate"
        "colour space  : $space"
        "exposure      : $(if ($expo) { ($expo -replace '^\s*exposure\s*:\s*','').Trim() } else { '(not printed by the binary)' })"
        ""
        "ARGV (verbatim, as executed -- NOT the whole switch state; see below):"
        "  $Exe $($argv -join ' ')"
        ""
        "FIXES ENABLED BY THIS RENDER (-Fixes $Fixes)"
        $(if ($RecipeApplied.Count -eq 0) {
            "  none. Every render-affecting variable was cleared and none was set."
            "  This is a POSITIVE STATEMENT, not an omission: the $($ClearedSwitches.Count) names parsed"
            "  from byte-freeze.rs's RENDER_ENV were removed from the environment"
            "  before this render, so no ambient value in the calling shell reached it."
        }
        else {
            "  $($RecipeApplied.Count) switch(es), each PROVEN REACHABLE in this binary before the"
            "  render started -- the recipe was re-run with each entry corrupted in"
            "  turn and the binary had to reject the corrupt value by quoting it back."
            "  A switch the binary silently ignores would have aborted the run."
            foreach ($e in $RecipeApplied) {
                $lv = $RecipeLiveness | Where-Object { $_.Name -eq $e.Name } | Select-Object -First 1
                $lvTxt = if ($lv -and $lv.Live) { "LIVE -- rejected '$($e.Bad)' with exit $($lv.Exit)" } else { 'NOT PROBED' }
                "    $($e.Name) = $($e.Value)"
                "        liveness: $lvTxt"
                "        why     : $($e.Why)"
                if ($e.Name -eq 'STREHL_DEFECT_MAP' -and (Test-Path $e.Value)) {
                    "        sha256  : $((Get-FileHash $e.Value -Algorithm SHA256).Hash)"
                    "        bytes   : $((Get-Item $e.Value).Length)"
                }
            }
        })
        ""
        "DEFECT ACCOUNTING (the binary's own partition, not this script's summary)"
        $(if (-not $defectApplied) {
            "  NOT APPLIED -- the binary printed no '--- defect correction (MEASURED) ---'"
            "  partition, so no site was examined. This is a different fact from a"
            "  partition reading `corrected 0`, which would mean the map ran and found"
            "  nothing to do. Neither is reported as the other."
        }
        else {
            "  Counted so that a zero is readable: 'examined' is what the map offered,"
            "  and every site leaves through exactly one of the outcomes beside it."
            $defectLines | ForEach-Object { '  ' + $_.Trim() }
        })
        ""
        "RESOLVED SWITCH STATE ($($RegistrySwitches.Count) registry switches; $switchSet set)"
        "  backend applicability: $switchOK applicable, $switchNA INAPPLICABLE, $switchUnk unclassified"
        "  Environment variables never appear in argv however they are set, so"
        "  the argv line above cannot show them. Unset switches are listed too:"
        "  an omitted line is indistinguishable from a switch nobody considered."
        "  INAPPLICABLE means the stage does not exist on the backend that ran;"
        "  that is NOT the same fact as a stage that exists and is switched off."
        "  UNCLASSIFIED means the registry declares no backend for it, so this"
        "  block cannot tell you whether it could act. It is not a clean bill."
        $switchLines
        ""
        "BINARY-REPORTED RESOLVED STATE (the binary's own banner, not inferred)"
        "  A gear-guarded switch reads '(unset)' above whether or not it acted."
        "  This is an INDEX of $binaryKeyCount reported settings, not a filter:"
        "  the binary's complete self-report follows verbatim below, so a key"
        "  missing from this index is still present in the record."
        $(if ($binaryState) { $binaryState } else { '  (binary printed no recognised state lines)' })
        ""
        "BINARY SELF-REPORT, VERBATIM ($($binaryOut.Count) lines, nothing filtered)"
        "  The binary states its ABSENT stages here too (see 'not applied'),"
        "  which no environment variable and no argv can express."
        $binaryVerbatim
        ""
        "REPRODUCE THIS EXACT FILE:"
        $reproEnv
        "  $Exe stack `"$($S.Path)`" --out <OUT> $repro"
        $(if ($switchSet -eq 0) {
            "  ...with all $($RegistrySwitches.Count) registry switches UNSET, as listed above."
        }
        else {
            "  ...the $switchSet non-default switch(es) above are set by the lines shown."
        })
        $(if ($expoStops) {
            "  OBSERVED, NOT AN INSTRUCTION: --auto-exposure chose $expoStops stops"
            "   for this file. It is recorded so the choice is auditable; it is"
            "   deliberately NOT substituted into the command above. Replaying"
            "   this file's own chosen gain as --exposure $expoStops on a binary"
            "   where --exposure is load-bearing clips 85% of the frame to white"
            "   (measured, docs/research/BUILD-DEFECT.md section 22). The command"
            "   above is bit-exact with the binary it names, and preserves this"
            "   file's exposure on binaries that post-date it."
        })
    ) | Where-Object { $null -ne $_ } | Out-File -Encoding utf8 "$tif.provenance.txt"

    # MACHINE-READABLE MANIFEST, BESIDE THE PROSE ONE.
    #
    # The text sidecar is for a human reading one master. This is for anyone
    # asking a question across the corpus -- "which of these 26 had the defect
    # map on, and which map" -- which is exactly the question nobody could
    # answer about C:\dev\strehl-out\ORCH-FAITHFUL\faithful\. Prose is a poor
    # substrate for that and re-parsing it is how the wrong answer gets given.
    #
    # It carries hashes, not paths alone. A path records where a file was; a
    # hash records WHICH file it was, and the map at that path has already been
    # rewritten once during this project (v1 -> v2) without its name changing.
    $manifest = [ordered]@{
        artifact      = Split-Path $tif -Leaf
        rendered      = (Get-Date -Format o)
        status        = $status
        exit          = $exit
        bytes         = $bytes
        sha256        = $(if ($status -eq 'ok') { (Get-FileHash $tif -Algorithm SHA256).Hash } else { $null })
        subject       = $S.Name
        source        = $S.Path
        frames        = $S.Frames
        binary        = $Exe
        binary_sha256 = $binHash
        git_commit    = $gitFull
        pin           = $(if ($Sha) { $Sha } else { 'UNPINNED' })
        argv          = @('stack', $S.Path, '--out', $tif) + @($Flags -split '\s+' | Where-Object { $_ })
        flags         = $Flags
        fixes_arm     = $Fixes
        exposure      = $expoStops
        backend       = $backend
        cleared_env   = @($ClearedSwitches | Sort-Object)
        fixes         = @(foreach ($e in $RecipeApplied) {
                $lv = $RecipeLiveness | Where-Object { $_.Name -eq $e.Name } | Select-Object -First 1
                [ordered]@{
                    name         = $e.Name
                    value        = $e.Value
                    why          = $e.Why
                    liveness     = $(if ($lv.Live) { 'LIVE' } else { 'NOT PROBED' })
                    probe_exit   = $lv.Exit
                    probe_value  = $e.Bad
                    file_sha256  = $(if ($e.Name -eq 'STREHL_DEFECT_MAP' -and (Test-Path $e.Value)) {
                            (Get-FileHash $e.Value -Algorithm SHA256).Hash
                        } else { $null })
                }
            })
        defect        = [ordered]@{
            applied = $defectApplied
            counts  = $defectCounts
            lines   = @($defectLines | ForEach-Object { $_.Trim() })
        }
    }
    $manifest | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 "$tif.manifest.json"

    # A sentinel beside the file, not the file's mere existence: a killed render
    # leaves a partial TIFF on disk that is the right name and the wrong image.
    # It is written LAST, after provenance, so a resumed run can never skip a
    # subject whose provenance failed to write.
    if ($status -eq 'ok') { "$binHash" | Out-File -Encoding ascii "$tif.ok" }

    # Presentation outputs. Deliberately AFTER the sentinel and reported in
    # their own manifest columns: a grading failure is a presentation defect,
    # not a render defect, and must not mark a good master bad. The converse
    # also holds -- these are only attempted for a master that actually
    # rendered, so a graded JPEG can never exist for a failed subject and be
    # mistaken for evidence that it worked.
    $pr = $(if ($status -eq 'ok') { New-Presentation -Name $S.Name -Tif $tif }
        else { @{ Viewable = 'norender'; Graded = 'norender' } })
    $viewState = $pr.Viewable; $gradeState = $pr.Graded

    Write-Host ("        {0}  {1:N0}s  {2:N0} MB{3}{4}" -f $status, $sw.Elapsed.TotalSeconds, ($bytes / 1MB),
        $(if ($expoStops) { "  exp $expoStops st" } else { '' }),
        $(if ($gradeState -notin @('-', 'off', 'ok')) { "  graded:$gradeState" } else { '' }))
    [pscustomobject]@{ Name = $S.Name; Frames = $S.Frames; Secs = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        Exit = $exit; Bytes = $bytes; Status = $status; Exposure = $expoStops
        Viewable = $viewState; Graded = $gradeState
    }
}

$runSw = [Diagnostics.Stopwatch]::StartNew()
$results = @()
$i = 0
foreach ($s in $subjects) {
    $i++
    try { $results += Invoke-Subject -S $s -Index $i -Total $nSubjects -Note '' }
    catch {
        Write-Warning "$($s.Name): $_"
        $results += [pscustomobject]@{ Name = $s.Name; Frames = $s.Frames; Secs = 0; Exit = -1
            Bytes = 0; Status = 'threw'; Viewable = '-'; Graded = '-'
        }
    }
}

# One retry pass at the END. A transient shortage caused by a neighbouring
# agent has had time to clear by now, and this run's own peak is over.
$retry = $results | Where-Object { $_.Status -ne 'ok' -and $_.Status -ne 'skip' }
if ($retry) {
    Write-Host ''
    Write-Host ("retrying {0} failed subject(s) now the pass's own peak is over" -f $retry.Count)
    foreach ($r in $retry) {
        $s = $subjects | Where-Object Name -eq $r.Name
        try {
            $again = Invoke-Subject -S $s -Index 0 -Total $nSubjects -Note '  [retry]'
            $results = @($results | Where-Object Name -ne $r.Name) + $again
        } catch { Write-Warning "retry $($s.Name): $_" }
    }
}
$runSw.Stop()

foreach ($r in $results) {
    "{0}`t{1}`t{2}`t{3}`t{4}`t{5}`t{6}`t{7}`t{8}" -f $r.Name, $r.Frames, $r.Secs, $r.Exit, $r.Bytes, $r.Status,
    $(if ($r.Exposure) { $r.Exposure } else { '-' }),
    $(if ($r.Viewable) { $r.Viewable } else { '-' }),
    $(if ($r.Graded) { $r.Graded } else { '-' }) |
        Out-File -Encoding utf8 -Append $manifest
}

$ok = @($results | Where-Object { $_.Status -in @('ok', 'skip') })
$bad = @($results | Where-Object { $_.Status -notin @('ok', 'skip') })

@(
    "acceptance arm  : $Arm"
    "finished        : $(Get-Date -Format o)"
    "pin             : $pinDesc"
    "binary          : $Exe"
    "binary sha256   : $binHash"
    "git commit      : $gitFull"
    "library         : $Library"
    "flags           : $Flags   (IDENTICAL on every subject)"
    "fixes arm       : $Fixes"
    # The recipe and its liveness belong in the RUN-level provenance, not only
    # in the per-subject manifests. An arm directory that does not carry which
    # fixes were active is the same failure class as the flats map that had to
    # be headered SUPERSEDED: whoever finds it next re-adopts it without
    # knowing what produced it. `NOT APPLIED` is printed as a positive
    # statement so that an empty recipe cannot read as an omitted field.
    if ($RecipeApplied.Count) {
        foreach ($f in $RecipeApplied) {
            $lv = @($RecipeLiveness | Where-Object { $_.Name -eq $f.Name })
            $tag = if ($lv.Count -eq 1) { if ($lv[0].Live) { 'LIVE' } else { 'NOT LIVE' } }
                   else { 'LIVENESS NOT PROBED' }
            "fix             : {0}={1}  [{2}]" -f $f.Name, $f.Value, $tag
        }
        $nLive = @($RecipeLiveness | Where-Object { $_.Live }).Count
        "liveness        : $nLive of $($RecipeLiveness.Count) probed live, $($RecipeLiveness.Count - $nLive) dead"
    }
    else { "fix             : NOT APPLIED -- this arm set no switches" }
    "cleared env     : $($ClearedSwitches.Count) names parsed from byte-freeze.rs RENDER_ENV"
    "subjects        : $($ok.Count)/$($nSubjects) rendered"
    "frames          : $totalFrames"
    "wall clock      : $([math]::Round($runSw.Elapsed.TotalMinutes,1)) min"
    if ($Only.Count) { "PARTIAL ARM     : -Only was used -- $($Only -join ', ')" }
    if ($bad.Count) { "FAILED          : $(($bad | ForEach-Object { "$($_.Name) [$($_.Status)]" }) -join '; ')" }
    ""
    "score it with:"
    "  python C:\dev\strehl-out\ORCH-CLAMP\accept.py $out <other-arm-dir> --ref <arm>"
    ""
    "Arms are comparable ONLY if rendered with these same flags in this same"
    "colour space. accept.py reads absolute DN; a tone-mapped arm and a"
    "camera-linear arm are not two arms of one experiment."
) | Where-Object { $_ -ne $null } | Out-File -Encoding utf8 (Join-Path $out 'RUN.txt')

Write-Host ''
Write-Host ("wall clock      : {0:N1} min for {1:N0} frames ({2:N2} s/frame)" -f `
        $runSw.Elapsed.TotalMinutes, $totalFrames, ($runSw.Elapsed.TotalSeconds / [math]::Max($totalFrames, 1)))

if ($bad.Count -eq 0 -and -not $Only.Count) {
    # Written LAST, so a dead run cannot claim success.
    @(
        "arm     : $Arm"
        "pin     : $pinDesc"
        "sha256  : $binHash"
        "flags   : $Flags"
        "subjects: $($ok.Count)"
        "wall    : $([math]::Round($runSw.Elapsed.TotalMinutes,1)) min"
    ) | Out-File -Encoding utf8 (Join-Path $out 'COMPLETE.txt')
    Remove-Item (Join-Path $out 'INCOMPLETE.txt') -ErrorAction SilentlyContinue
    Write-Host "ARM COMPLETE    : $out" -ForegroundColor Green
} else {
    # Distinguish the two reasons, because "INCOMPLETE" alone reads as "something
    # broke" when a -Only run is incomplete BY CONSTRUCTION and nothing failed.
    $why = @()
    if ($bad.Count) { $why += "$($bad.Count) failed" }
    if ($Only.Count) { $why += "-Only run: partial by construction, nothing failed" }
    Write-Host "ARM INCOMPLETE  : $out  ($($why -join '; '); INCOMPLETE.txt kept)" -ForegroundColor Yellow
}
exit $bad.Count
