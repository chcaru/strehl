# shippack.ps1 -- turn a finished finalpass arm into a gallery someone can open.
#
# WHAT THIS DOES
# --------------
# Ordering from the MASTERS, pixels from the GRADED files, and a notes file that
# states the limits of both. It is the last step of a render, not a separate
# activity, and it is a script rather than a checklist because every caveat it
# writes was at some point a thing an operator was supposed to remember and
# didn't.
#
# THE ONE INVARIANT THAT MATTERS
# ------------------------------
# The ordering is computed on the masters and NEVER on the presentation JPEGs.
# A graded file sits on the far side of a tone curve AND a per-image percentile
# normalisation, so a statistic fed one is partly measuring the grade -- and
# because the normalisation is per-image, it is measuring a DIFFERENT grade on
# every subject, which is worse than a constant error because it does not
# cancel in a comparison. rank.py reads *.tiff; contactsheet_ranked.py takes the
# resulting order and only then goes to the JPEGs for pixels.
#
# WHY THE NOTES FILE EXISTS
# -------------------------
# Two wrong conclusions were reached on this project in one night by inferring
# an artifact's provenance from its filename. A gallery gets copied, linked and
# screenshotted; whatever is not written inside it is lost the moment it moves.

[CmdletBinding()]
param(
    # A finished finalpass arm directory: masters + _faithful + _presentation.
    [Parameter(Mandatory = $true)][string]$ArmDir,

    # Where ranking.tsv / RANKING-CAVEATS.txt / the sheet are written.
    [string]$OutDir,

    # Encoding of the MASTERS, passed to rank.py so it can invert the curve
    # exactly before measuring. Wrong value here silently rescales every
    # number, so it is explicit rather than sniffed.
    [ValidateSet('srgb', 'linear')][string]$Encoded = 'srgb',

    [int]$Cols = 5,
    [int]$Tile = 440
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $repo 'Cargo.toml'))) { throw "repo root not found at $repo" }

if (-not (Test-Path $ArmDir)) { throw "no arm directory at $ArmDir" }
if (-not $OutDir) { $OutDir = Join-Path $ArmDir '_gallery' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# A partial arm must not be packaged as if it were a finished one. finalpass
# writes COMPLETE.txt last and INCOMPLETE.txt first precisely so this check can
# be made from the filesystem rather than from an operator's memory of how the
# run ended.
$complete = Test-Path (Join-Path $ArmDir 'COMPLETE.txt')
$incomplete = Test-Path (Join-Path $ArmDir 'INCOMPLETE.txt')

$masters = @(Get-ChildItem $ArmDir -Filter *.tiff -File)
$graded = Join-Path $ArmDir '_presentation'
$faithful = Join-Path $ArmDir '_faithful'
if (-not (Test-Path $graded)) { throw "no _presentation dir in $ArmDir (rendered with -NoPresent?)" }

Write-Host "arm        : $ArmDir"
Write-Host "masters    : $($masters.Count)"
Write-Host "complete   : $(if ($complete) { 'yes' } elseif ($incomplete) { 'NO -- INCOMPLETE.txt present' } else { 'UNKNOWN -- neither marker' })"

# --- ordering, from the masters -------------------------------------------
Write-Host "`nranking (from masters, linear light)..."
& python (Join-Path $repo 'scripts\rank.py') $ArmDir --encoded $Encoded --out $OutDir --strip-arm
if ($LASTEXITCODE -ne 0) { throw "rank.py failed ($LASTEXITCODE)" }

$ranking = Join-Path $OutDir 'ranking.tsv'
if (-not (Test-Path $ranking)) { throw "rank.py did not write $ranking" }

# --- contact sheet, ordered by that, drawn from the graded files ----------
$sheet = Join-Path $OutDir 'contactsheet-ranked.png'
Write-Host "`ncontact sheet (order from masters, pixels from graded)..."
& python (Join-Path $repo 'scripts\contactsheet_ranked.py') `
    --ranking $ranking --images $graded --out $sheet --cols $Cols --tile $Tile
if ($LASTEXITCODE -ne 0) { throw "contactsheet_ranked.py failed ($LASTEXITCODE)" }

# --- counts, partitioned so a gap cannot read as a pass -------------------
$ranked = @(Import-Csv $ranking -Delimiter "`t")
$gradedFiles = @(Get-ChildItem $graded -Filter *.jpg -File -ErrorAction SilentlyContinue)
$faithfulFiles = @(Get-ChildItem $faithful -Filter *.jpg -File -ErrorAction SilentlyContinue)
$sidecars = @(Get-ChildItem $ArmDir -Filter *.provenance.txt -File)

$missingGrade = @($ranked | Where-Object {
        -not (Test-Path (Join-Path $graded "$($_.subject).jpg")) })
$missingSidecar = @($masters | Where-Object {
        -not (Test-Path "$($_.FullName).provenance.txt") })

# --- the notes file --------------------------------------------------------
$run = Join-Path $ArmDir 'RUN.txt'
$runTxt = if (Test-Path $run) { Get-Content $run -Raw } else { '(no RUN.txt)' }
$binLine = ($runTxt -split "`n" | Where-Object { $_ -match 'sha256|binary|git commit|flags' }) -join "`n"

$notes = @"
READ THIS BEFORE DRAWING A CONCLUSION FROM THIS GALLERY
=======================================================

WHAT PRODUCED IT
$binLine

counts (these partition; a missing subject is NOT a passing one)
  masters rendered        : $($masters.Count)
  ranked in ranking.tsv   : $($ranked.Count)
  faithful JPEGs          : $($faithfulFiles.Count)
  graded JPEGs            : $($gradedFiles.Count)
  provenance sidecars     : $($sidecars.Count)
  ranked but NOT graded   : $($missingGrade.Count) $(if ($missingGrade) { '-- ' + ($missingGrade.subject -join ', ') })
  masters w/o sidecar     : $($missingSidecar.Count) $(if ($missingSidecar) { '-- ' + ($missingSidecar.Name -join ', ') })
  arm marked complete     : $(if ($complete) { 'yes' } elseif ($incomplete) { 'NO -- partial pass' } else { 'UNKNOWN' })

THREE THINGS THIS GALLERY CANNOT TELL YOU
-----------------------------------------
1. NOTHING HERE MAY BE MEASURED. Every file under _presentation/ has a tone
   curve and a PER-IMAGE percentile normalisation applied. Because the
   normalisation differs per subject, an error introduced by reading one does
   not cancel when two are compared -- it is worse than a constant bias. Measure
   the masters. `ranking.tsv` was computed from the masters for this reason.

2. A THUMBNAIL CANNOT CARRY A PRINT VERDICT. Measured by ORCH on this corpus:
   `highly-angled-ruler-mm-cpl` looks poor on every contact sheet produced so
   far and is genuinely sharp at 1:1 -- crisp graduations, 1364 DN, mid-pack.
   The sheet is a navigation aid and an ordering. Judge at 100%, from the
   masters, or do not judge.

3. THE ORDER HAS A RESOLUTION COARSER THAN ITS RANK NUMBERS. See
   RANKING-CAVEATS.txt next to this file: the default hull clamp costs a
   subject-dependent 84.6%-97.7% of microcontrast, so a subject's true place is
   an interval. Read a gap wider than the stated displacement as real and a
   narrower one as a tie.

ON THE EARLIER GALLERY (SHIP-V1)
--------------------------------
SHIP-V1's single-binary provenance is INFERENTIAL, not recorded. Its
`_render.log` does not name the binary that produced it; the claim that all 26
of its subjects came from one build rests on file mtimes showing a contiguous
27.6-minute pass with a largest inter-render gap of 2.5 minutes -- consistent
with one build, but not evidence of one. THIS arm does not have that problem:
every subject carries a .provenance.txt naming the binary, its sha256, the
commit, the full argv, and the run-time-chosen exposure gain.

That last item is the one that matters for reproducibility. `--auto-exposure`
picks gain FROM THE IMAGE, so the flag set does NOT determine the pixels. Each
sidecar therefore prints a REPRODUCE line with --auto-exposure replaced by the
gain it actually chose.

DIAGNOSIS IS NOT HERE
---------------------
Why a given subject is weak -- soft merge versus out-of-focus capture -- is
BUILD-TRIAGE's call, not this gallery's. A low rank is not an accusation
against the stacker. rank.py's --verdicts flag is the hook for their answer.
"@

$notesPath = Join-Path $OutDir 'GALLERY-NOTES.txt'
$notes | Out-File -Encoding utf8 $notesPath

Write-Host "`nwrote:"
Write-Host "  $ranking"
Write-Host "  $(Join-Path $OutDir 'RANKING-CAVEATS.txt')"
Write-Host "  $sheet"
Write-Host "  $notesPath"

if ($missingGrade.Count -or $missingSidecar.Count) {
    Write-Warning "gaps recorded in GALLERY-NOTES.txt: $($missingGrade.Count) ungraded, $($missingSidecar.Count) without sidecar"
}
if (-not $complete) {
    Write-Warning "this arm is NOT marked complete -- the gallery is of a partial pass"
}
