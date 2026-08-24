# M97n: does a config-keyed cache stop the silent poisoning?
#
# MEASURED before the fix: `align --reference 40` then an IDENTICAL `stack`
# command line rendered DB43E708... or ADF81E01... depending only on whether
# the align had run first. check_stack cannot catch it -- both solves cover the
# same frames.
#
# Sharper still: `align`'s default --reference is 0 while the merge uses n/2,
# so a PLAIN `strehl align <dir>` with no flags at all is a poisoning run.
# This harness uses exactly that, no special flags.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\109MSDCF"
$o   = "C:\dev\strehl-out\M97\poison2"
$cache = "$o\cache"

Remove-Item $o -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $cache | Out-Null

# Hermetic cache: seven agents share the real one, and this must not touch it.
$env:STREHL_CACHE_DIR = $cache
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

function Hash($p) {
  if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0,16) } else { "ABSENT" }
}
function Entries { (Get-ChildItem $cache -Filter *.warpmap.txt -ErrorAction SilentlyContinue).Count }

function Stack($tag) {
  $out = & $exe stack $dir --limit 22 --gate 4.0 --out "$o\$tag.tiff" 2>&1
  $out | Out-File "$o\$tag.log" -Encoding utf8
  $al = ($out | Select-String "alignment" | Out-String).Trim() -replace "\s+", " "
  "  [$tag] $al"
}

"=== M97n: config-keyed warp cache ==="
"stack $dir  --limit 22 --gate 4.0   hermetic STREHL_CACHE_DIR"
""
"P0: clean cache, merge solves its own entry"
Stack "P0"
$e0 = Entries
"     cache entries: $e0"
""
"POISON A: plain 'strehl align' with NO flags"
$pout = & $exe align $dir --limit 22 2>&1
$pout | Out-File "$o\poisonA.log" -Encoding utf8
"  align exit=$LASTEXITCODE  " + (($pout | Select-String "reference frame" | Out-String).Trim())
$e1 = Entries
"     cache entries: $e1   (SAME config as the merge, so sharing one entry is correct)"
""
"POISON B: 'strehl align --reference 3' -- a genuinely different solve"
$pout2 = & $exe align $dir --limit 22 --reference 3 2>&1
$pout2 | Out-File "$o\poisonB.log" -Encoding utf8
"  align exit=$LASTEXITCODE  " + (($pout2 | Select-String "reference frame" | Out-String).Trim())
$e2 = Entries
"     cache entries: $e2"
""
"P1: the SAME stack command line again"
Stack "P1"
""
"PLANT: alignment disabled -- must move the bytes, or nothing here is live"
$env:STREHL_ALIGN = "0"
Stack "P2"
Remove-Item Env:\STREHL_ALIGN
""
$h0 = Hash "$o\P0.tiff"; $h1 = Hash "$o\P1.tiff"; $h2 = Hash "$o\P2.tiff"
"P0 (clean)        : $h0"
"P1 (after poison) : $h1"
"P2 (PLANT, no aln): $h2"
""
$fail = 0
function Bar($label, $ok) {
  if ($ok) { "PASS  $label" } else { "FAIL  $label"; $script:fail++ }
}
Bar "C1  a poisoning align does not move the render (P0 == P1)"       ($h0 -eq $h1 -and $h0 -ne "ABSENT")
Bar "C4a a no-flag align resolves to the merge's own config (1 entry)" ($e0 -eq 1 -and $e1 -eq 1)
Bar "C4b --reference 3 gets its OWN cache entry (1 -> 2)"             ($e2 -eq 2)
Bar "C2  PLANT: disabling alignment does move it (P0 != P2)"          ($h0 -ne $h2 -and $h2 -ne "ABSENT")
"" 
if ($fail -eq 0) { "ALL BARS PASS" } else { "$fail BAR(S) FAILED" }
"(C5 -- no thrash -- read the [P1] alignment line above: it must say 'sidecar', not 'solved'.)"
