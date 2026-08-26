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
    [int]$PresentWidth = 1400
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
        git archive $pinSha | tar -x -C $pin
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw "git archive failed for $pinSha" }
        Pop-Location
        Push-Location $pin
        $env:CARGO_TARGET_DIR = Join-Path $pin 'target'
        & "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release -p strehl-cli --bin strehl 2>&1 |
            Select-Object -Last 3 | Out-Host
        Pop-Location
        Remove-Item Env:\CARGO_TARGET_DIR -ErrorAction SilentlyContinue
        if (-not (Test-Path $Exe)) { throw "pin build produced no binary at $Exe" }
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
# reason; this list mirrors byte-freeze.rs's RENDER_ENV.
$ClearedSwitches = @(
    'STREHL_ALIGN', 'STREHL_WARPMAP', 'STREHL_CACHE_DIR',
    'STREHL_FIX_HALO', 'STREHL_FIX_HALO_DELTA',
    'STREHL_EDGE_AWARE', 'STREHL_EDGE_TAU', 'STREHL_EDGE_CONF',
    'STREHL_ONLY_FRAME', 'STREHL_MERGE', 'STREHL_PYRAMID_WORKERS',
    'STREHL_VEIL', 'STREHL_VEIL_MARGIN', 'STREHL_VEIL_FLOOR',
    'STREHL_FIX_CA')
foreach ($v in $ClearedSwitches) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
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
            $bk = 'any'
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
    # The exposure line is not decoration. --auto-exposure chooses the gain FROM
    # THE IMAGE, so the flags alone do not determine the pixels; the binary
    # quantises it to 1/100 stop precisely "so that the printed number
    # reproduces the file exactly". Without it captured, an --auto-exposure
    # render cannot be reproduced at all -- not approximately, at all.
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

    $repro = if ($expoStops -and $Flags -match '--auto-exposure') {
        # --auto-exposure is image-dependent; pin it to the printed number.
        ($Flags -replace '--auto-exposure', "--exposure $expoStops")
    }
    else { $Flags }

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
    $switchLines = @()
    foreach ($k in $RegistrySwitches.Keys) {
        $d = $RegistrySwitches[$k]
        $na = ($d.Backend -ne 'any' -and $renderBackend -ne 'unknown' -and $d.Backend -ne $renderBackend)
        $val = [Environment]::GetEnvironmentVariable($k)
        if ($na) { $switchNA++ }
        if ($null -ne $val -and $val -ne '') {
            $switchSet++
            $src = if ($ClearedSwitches -contains $k) {
                'ENVIRONMENT -- set AFTER the harness cleared it'
            }
            else {
                'ENVIRONMENT -- and this harness does not clear it'
            }
            if ($na) { $src += "; INAPPLICABLE -- $($d.Backend)-only, this render was $renderBackend" }
            $switchLines += ('  {0,-26} = {1,-18} [{2}]' -f $k, $val, $src)
        }
        elseif ($na) {
            $switchLines += ('  {0,-26} = {1,-18} [INAPPLICABLE -- {2}-only stage; this render was {3}, which never reaches it]' -f
                $k, '(n/a)', $d.Backend, $renderBackend)
        }
        else {
            $how = if ($ClearedSwitches -contains $k) { 'cleared by harness' } else { 'not set' }
            $switchLines += ('  {0,-26} = {1,-18} [{2}; built-in default: {3}]' -f
                $k, '(unset)', $how, $d.Default)
        }
    }

    # What the BINARY said it resolved to. The environment cannot answer this:
    # STREHL_FIX_CA is unset both when CA is corrected and when it is not, and
    # only the gear guard's own line distinguishes them.
    $resolvedKeys = 'merge backend|camera|lateral CA|bands|selection|iso'
    $binaryState = $binaryOut |
        Where-Object { $_ -match "^\s*($resolvedKeys)\s*:" } |
        ForEach-Object { '  ' + $_.Trim() }

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
        "RESOLVED SWITCH STATE ($($RegistrySwitches.Count) registry switches, $switchSet set, $switchNA inapplicable to this backend)"
        "  Environment variables never appear in argv however they are set, so"
        "  the argv line above cannot show them. Unset switches are listed too:"
        "  an omitted line is indistinguishable from a switch nobody considered."
        "  INAPPLICABLE means the stage does not exist on the backend that ran;"
        "  that is NOT the same fact as a stage that exists and is switched off."
        $switchLines
        ""
        "BINARY-REPORTED RESOLVED STATE (the binary's own banner, not inferred)"
        "  A gear-guarded switch reads '(unset)' above whether or not it acted."
        "  These are the lines where the binary states what it actually did:"
        $(if ($binaryState) { $binaryState } else { '  (binary printed no recognised state lines)' })
        ""
        "REPRODUCE THIS EXACT FILE:"
        "  $Exe stack `"$($S.Path)`" --out <OUT> $repro"
        $(if ($switchSet -eq 0) {
            "  ...with all $($RegistrySwitches.Count) registry switches UNSET, as listed above."
        }
        else {
            "  ...with the $switchSet non-default switch(es) above exported first."
        })
        $(if ($repro -ne $Flags) {
            "  (--auto-exposure replaced by the gain it CHOSE; re-running with"
            "   --auto-exposure on a different binary may choose differently)"
        })
    ) | Where-Object { $null -ne $_ } | Out-File -Encoding utf8 "$tif.provenance.txt"

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
