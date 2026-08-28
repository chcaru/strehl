# ORCH item 3: does verify.py catch a CONCLUSION flip, or only a number?
#
# V-NEVERWORSE's verifier tested for the PRESENCE of "refuted" and passed 712
# green checks after that section's verdict was flipped to "confirmed" with
# every number intact.  verify.py is a different shape -- it RE-DERIVES each
# headline row from the raw JSONL -- so a numeric mutation is caught by
# construction.  The open question is whether a mutation that leaves every
# number correct but reverses what the document CONCLUDES also goes RED.
#
# Regression discipline: the file is copied to $env:TEMP first and restored
# from that copy.  `git checkout --` reverts to HEAD and has destroyed
# uncommitted work on this machine before.
$ErrorActionPreference = 'Stop'
Set-Location C:\dev\blog\death-of-software\projects\strehl

$doc  = 'docs\research\V-SPEED.md'
$safe = Join-Path $env:TEMP 'V-SPEED.md.preflip'
Copy-Item $doc $safe -Force
"saved pristine copy -> $safe"

function Run-Verify {
  $o = & python -u experiments\V-SPEED\verify.py 2>&1
  $line = ($o | Select-String 're-derived rows matched').Line
  if (-not $line) { $line = ($o | Select-Object -Last 1) }
  return @{ rc = $LASTEXITCODE; line = "$line".Trim() }
}

$b = Run-Verify
"BASELINE          rc=$($b.rc)  $($b.line)"

# The flip: every number in this sentence stays correct.  Only the direction
# of the claim reverses -- the headline of the whole report.
$from = 'strehl is **22.6x faster than Hugin align_image_stack + enfuse**'
$to   = 'strehl is **22.6x SLOWER than Hugin align_image_stack + enfuse**'
$src  = [System.IO.File]::ReadAllText((Resolve-Path $doc))
# ASCII 'x' above will not match the document's Unicode multiplication sign,
# so build the anchor with the real character rather than guessing.
$from = $from -replace 'x faster', ([char]0x00D7 + ' faster')
$to   = $to   -replace 'x SLOWER', ([char]0x00D7 + ' SLOWER')

$n = ([regex]::Matches($src, [regex]::Escape($from))).Count
"anchor occurrences: $n"
if ($n -ne 1) {
  "MUTATION TARGET NOT FOUND -- refusing to report a result from a plant that did not land"
  Remove-Item $safe -Force
  exit 2
}

[System.IO.File]::WriteAllText((Resolve-Path $doc), $src.Replace($from, $to))
"planted conclusion flip (all numbers intact)"

$m = Run-Verify
"AFTER FLIP        rc=$($m.rc)  $($m.line)"

Copy-Item $safe $doc -Force
Remove-Item $safe -Force
$r = Run-Verify
"AFTER RESTORE     rc=$($r.rc)  $($r.line)"
"doc clean in git : " + ((git --no-pager status --porcelain -- $doc) -eq $null)

""
if ($m.rc -eq $b.rc -and $m.line -eq $b.line) {
  "RESULT: BLIND -- verify.py certifies the NUMBERS and does not certify the CONCLUSION."
} else {
  "RESULT: CAUGHT -- verify.py went RED on a pure conclusion flip."
}
