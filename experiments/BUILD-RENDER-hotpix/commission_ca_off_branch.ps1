# Commission the per-subject CA "off" branch after the default flip.
#
# THE BUG THIS EXISTS TO CATCH. gallery.ps1 used to express "CA off for this
# subject" by REMOVING $env:STREHL_FIX_CA. That was correct while unset meant
# off. Since 96571ee unset means "let the binary's own gear guard decide", so a
# subject rejected by the script's EXIF check would have been rendered WITH the
# correction and recorded `off:path` beside it. The label would have been a lie,
# which is the exact failure the per-subject check exists to prevent.
#
# THE DESIGN. Two subject directories holding BYTE-IDENTICAL frames. One is left
# alone; in the other, the first frame's EXIF LensModel is rewritten to a
# different lens. gallery.ps1 probes only the first frame, so it sees a mismatch
# on `planted` and a match on `genuine`, while the pixels and the maker-note
# LensType3 the BINARY reads are unchanged in both.
#
# Identical input, different label. So:
#   outputs DIFFER    -> the off branch really disabled the correction   PASS
#   outputs IDENTICAL -> both arms got CA; the label is decorative       FAIL
#
# That is a positive and a negative control in one comparison, and it cannot be
# satisfied by a run that does nothing.

param(
    [string]$Exe  = 'C:\dev\strehl-out\BUILD-RENDER-target\release\strehl.exe',
    [string]$Src  = 'D:\personal\macro\coffee-bubbles',
    [string]$Root = 'C:\dev\strehl-out\BUILD-RENDER-caoff',
    [int]$Frames  = 4
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$galleryScript = Join-Path $repo 'scripts\gallery.ps1'
# Asserted rather than assumed: a wrong path here made the run limp on to a
# null-array error four steps later instead of stopping at the real cause.
if (-not (Test-Path $galleryScript)) { throw "gallery.ps1 not found at $galleryScript" }

if (Test-Path $Root) { Remove-Item $Root -Recurse -Force }
$lib = Join-Path $Root 'lib'
New-Item -ItemType Directory -Force -Path (Join-Path $lib 'genuine') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $lib 'planted') | Out-Null

# D:\ is read-only: copy out, never modify in place.
$srcFrames = Get-ChildItem -File $Src -Filter *.ARW | Sort-Object Name | Select-Object -First $Frames
foreach ($f in $srcFrames) {
    Copy-Item $f.FullName (Join-Path $lib 'genuine') -Force
    Copy-Item $f.FullName (Join-Path $lib 'planted') -Force
}
Write-Host "copied $($srcFrames.Count) frames into two identical subjects"

$first = (Get-ChildItem -File (Join-Path $lib 'planted') -Filter *.ARW | Sort-Object Name)[0]
& exiftool -q -overwrite_original -LensModel="FE 90mm F2.8 Macro G OSS" $first.FullName
$now = & exiftool -fast2 -T -q -LensModel $first.FullName
Write-Host "planted first frame LensModel -> $now"
if ($now -notmatch '90mm') { throw "PLANT DID NOT LAND -- refusing to run a control that may be inert" }

# The frames must still be byte-identical apart from that one probe file, or the
# comparison below would be confounded by the input rather than by the branch.
$g = Get-ChildItem -File (Join-Path $lib 'genuine') -Filter *.ARW | Sort-Object Name
$p = Get-ChildItem -File (Join-Path $lib 'planted') -Filter *.ARW | Sort-Object Name
$same = 0
for ($i = 1; $i -lt $g.Count; $i++) {
    if ((Get-FileHash $g[$i]).Hash -eq (Get-FileHash $p[$i]).Hash) { $same++ }
}
Write-Host "frames 2..$($g.Count) identical across the two subjects: $same/$($g.Count - 1)"
if ($same -ne $g.Count - 1) { throw "inputs differ beyond the planted probe frame" }

$out = Join-Path $Root 'gallery'
pwsh -File $galleryScript -Exe $Exe -Library $lib -OutDir $out |
    Tee-Object -FilePath (Join-Path $Root 'gallery.log') | Out-Host

$run = Get-Content (Join-Path $out 'RUN.txt') -Raw -ErrorAction SilentlyContinue
$man = Get-Content (Join-Path $out 'manifest.tsv') -ErrorAction SilentlyContinue

Write-Host "`n--- manifest ca column ---"
$hdr = ($man[0] -split "`t"); $ci = [array]::IndexOf($hdr, 'ca')
$rows = @{}
foreach ($l in $man[1..($man.Count - 1)]) {
    $f = $l -split "`t"
    if ($f[0]) { $rows[$f[0]] = $f[$ci]; "  {0,-9} ca={1}" -f $f[0], $f[$ci] }
}

$gj = Join-Path $out 'genuine.jpg'
$pj = Join-Path $out 'planted.jpg'
$gh = if (Test-Path $gj) { (Get-FileHash $gj).Hash } else { '(missing)' }
$ph = if (Test-Path $pj) { (Get-FileHash $pj).Hash } else { '(missing)' }
Write-Host "`n  genuine.jpg $($gh.Substring(0,[Math]::Min(16,$gh.Length)))"
Write-Host "  planted.jpg $($ph.Substring(0,[Math]::Min(16,$ph.Length)))"

$checks = @(
    @{ n = 'both subjects rendered'                              ; ok = ((Test-Path $gj) -and (Test-Path $pj)) }
    @{ n = 'genuine labelled CA on'                              ; ok = ($rows['genuine'] -notmatch '^off') }
    @{ n = 'planted labelled off:path'                           ; ok = ($rows['planted'] -eq 'off:path') }
    @{ n = 'RUN.txt names the rejected stack'                    ; ok = ($run -match 'planted') }
    @{ n = 'OUTPUTS DIFFER => the off branch really disabled CA' ; ok = ($gh -ne $ph -and $gh -ne '(missing)') }
)
Write-Host ''
$fail = 0
foreach ($c in $checks) {
    if (-not $c.ok) { $fail++ }
    Write-Host ("  [{0}] {1}" -f $(if ($c.ok) { 'PASS' } else { 'FAIL' }), $c.n)
}
Write-Host ''
if ($fail -eq 0) {
    Write-Host "COMMISSIONED: identical frames, different label, different pixels." -ForegroundColor Green
} else {
    Write-Host "NOT COMMISSIONED: $fail check(s) failed." -ForegroundColor Red
}
exit $fail
