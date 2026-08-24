# M104: independent verification of the M95 binning patch as applied at 56bd846.
#
# Compares the PRE binary (56bd846^ = 28e0b35) against the POST binary
# (56bd846) so the patch is isolated.  Comparing against HEAD would conflate
# it with M99/M103, which change merge output on purpose.
#
# D: is READ-ONLY.  Size and mtime of every entry are compared before and
# after, and STREHL_WARPMAP names the existing sidecar so no solve writes
# beside the captures.

$ErrorActionPreference = 'Continue'

$PRE  = 'C:\dev\strehl-verify\target-pre\release\strehl.exe'
$POST = 'C:\dev\strehl-verify\target-post\release\strehl.exe'
$OUT  = 'C:\dev\strehl-out\M104-verify'
$SRC  = $args[0]
$LIM  = $args[1]
# Alignment is orthogonal to a patch that only rewires a CLI boolean, and both
# arms run identically either way.  Default OFF because a --limit subset has a
# different bracket digest from the committed sidecar, and strehl correctly
# refuses to apply a warp map fitted on a different frame set -- so this keeps
# the run from needing any solve, and therefore from writing beside D:.
$env:STREHL_ALIGN = if ($args.Count -gt 2) { $args[2] } else { '0' }

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

function Snap($d) {
  Get-ChildItem -Path $d -File -Recurse | ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } | Sort-Object
}
$before = Snap $SRC

$wm = Join-Path $SRC 'warpmap.txt'
if ((Test-Path $wm) -and $env:STREHL_ALIGN -ne '0') { $env:STREHL_WARPMAP = $wm }
else { Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue }

$tag = (Split-Path $SRC -Leaf) + "-n$LIM-a$($env:STREHL_ALIGN)"

function Run($bin, $name, $extra, $gate = '2.0') {
  $o = Join-Path $OUT "$tag-$name.tif"
  if (Test-Path $o) { Remove-Item $o -Force }
  $a = @('stack', $SRC, '--limit', $LIM, '--gate', $gate, '-o', $o) + $extra
  $log = Join-Path $OUT "$tag-$name.log"
  & $bin @a 2>&1 | Out-File -FilePath $log -Encoding utf8
  if (-not (Test-Path $o)) { Write-Host "  $name : NO OUTPUT (see $log)"; return $null }
  $h = (Get-FileHash $o -Algorithm SHA256).Hash
  $dim = (Select-String -Path $log -Pattern 'wrote\s+:' | Select-Object -Last 1).Line
  if ($dim -match '\((\d+) x (\d+)') { $d = "$($matches[1]) x $($matches[2])" } else { $d = '?' }
  [pscustomobject]@{ name = $name; sha = $h; dims = $d; path = $o }
}

Write-Host "=== $tag ==="
$A = Run $PRE  'pre-measure'          @()
$B = Run $POST 'post-measure'         @()
$C = Run $POST 'post-srgb'            @('--srgb')
$D = Run $POST 'post-srgb-binned'     @('--srgb','--binned')
$E = Run $PRE  'pre-srgb'             @('--srgb')
$F = Run $POST 'post-binned-only'     @('--binned')
$G = Run $POST 'post-demosaic-binned' @('--demosaic','--binned')
# NEGATIVE CONTROL (rule 39).  The byte-freeze check is an equality on two
# hashes, and an equality that cannot fail proves nothing.  Plant a change the
# patch has nothing to do with -- one gate step -- and require CHECK 1's own
# comparison to report FAIL on it.  If this comes out identical, the harness
# is comparing something other than the merged bytes and CHECK 1 is void.
$N = Run $POST 'neg-gate-1.9'         @() 1.9

foreach ($r in @($A,$B,$C,$D,$E,$F,$G,$N)) {
  if ($r) { "{0,-22} {1,-14} {2}" -f $r.name, $r.dims, $r.sha | Write-Host }
}

Write-Host ""
Write-Host "CHECK 1  byte freeze (pre-measure vs post-measure):"
Write-Host ("  {0}" -f $(if ($A -and $B -and $A.sha -eq $B.sha) { 'PASS - identical' } else { 'FAIL' }))
Write-Host "CHECK 2  --srgb dims: $($C.dims)  |  --srgb --binned dims: $($D.dims)"
Write-Host "CHECK 3  THE GAP (post --srgb --binned vs pre --srgb):"
Write-Host ("  {0}" -f $(if ($D -and $E -and $D.sha -eq $E.sha) { 'PASS - identical' } else { 'FAIL - differs' }))
Write-Host "ATTACK A  --binned alone must not disturb the frozen path:"
Write-Host ("  {0}" -f $(if ($F -and $B -and $F.sha -eq $B.sha) { 'PASS - identical' } else { 'FAIL - differs' }))
Write-Host "ATTACK B  --demosaic --binned (contradictory) dims: $($G.dims)"
Write-Host "NEG CTRL  planted gate 1.9 must make CHECK 1's own comparison FAIL:"
Write-Host ("  {0}" -f $(if ($N -and $B -and $N.sha -ne $B.sha) { 'RED as required - differs' } else { 'HARNESS VOID - identical' }))

$after = Snap $SRC
if (Compare-Object $before $after) { Write-Host "READ-ONLY ASSERTION FAILED on $SRC" } else { Write-Host "read-only assertion on ${SRC}: PASS" }

@{ tag = $tag; runs = @($A,$B,$C,$D,$E,$F,$G,$N) | Where-Object { $_ } } | ConvertTo-Json -Depth 4 |
  Out-File -FilePath (Join-Path $OUT "$tag-results.json") -Encoding utf8
