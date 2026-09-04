param()

# Negative controls for v2950.ps1.
#
# Each control plants ONE specific defect into a COPY of STATUS.md in $env:TEMP
# and requires the forward verifier to (a) exit non-zero and (b) fail the
# *named* check that defect targets. A control that merely goes RED proves
# nothing -- it could be failing for an unrelated reason.
#
# Every mutation anchor is asserted to occur exactly once before it is applied.
# An anchor that does not land makes a control silently GREEN, which is the
# worst failure mode a control can have. One anchor in the sibling nc-scope.ps1
# did exactly that earlier today by spanning a line break, which is why anchors
# here are single-line by construction and hard-error when they miss.
#
# Two BENIGN controls are included. They perturb the document in ways that must
# NOT trip the verifier. Without them a checker that simply fails on everything
# would score a perfect sweep.

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$src = Resolve-Path "$here\..\..\docs\STATUS.md"
$orig = Get-Content -LiteralPath $src -Raw -Encoding UTF8

$controls = @(
  @{ n = 'NC1 inflate a frame count'
     a = 'the amendment''s account: `tilted-sw4-cpl` at 182 frames, `tilted-sw10-cpl` at 92,'
     b = 'the amendment''s account: `tilted-sw4-cpl` at 191 frames, `tilted-sw10-cpl` at 92,'
     e = '2.9.50 states each count'; benign = $false },

  @{ n = 'NC2 quietly retract the M8 FAIL'
     a = 'amendment lowers no bar and retracts no FAIL. M8 still'
     b = 'amendment clears M8 pending re-measurement. M8 formerly'
     e = '2.9.50 states M8 still reads FAIL'; benign = $false },

  @{ n = 'NC3 fabricate a plan quotation'
     a = '> Under assessment is an inversion -- score a 1.4x TC-off stack and use 2.8x bursts as'
     b = '> Under assessment is an inversion -- score a 1.0x TC-off stack and use 4.0x bursts as'
     e = '...and 2.9.50 quotes it'; benign = $false },

  @{ n = 'NC4 break the inversion arithmetic'
     a = 'magnification be the truth — yields `2.8/1.4 = 2.0x` **exactly**'
     b = 'magnification be the truth — yields `2.8/1.4 = 2.4x` **exactly**'
     e = 'the inversion arithmetic is stated'; benign = $false },

  @{ n = 'NC5 drop the may-not-score limit on the burned session'
     a = 'commission on it and **may not report any number from it as a score**'
     b = 'commission on it and **may use it as needed for any purpose**'
     e = 'the may-not-score limit is stated'; benign = $false },

  @{ n = 'NC6 misattribute a phrase to 2.9.49.7'
     a = '§2.9.49.7 named "M136''s disease at program scale" as the standing risk'
     b = '§2.9.49.7 named "M136''s pathology at program scale" as the standing risk'
     e = '2.9.50 attributes it to 2.9.49.7'; benign = $false },

  @{ n = 'NC7 miscount the licensed axes'
     a = 'so it licenses **seven**: M1, M2, M3, M8, M9, M10, M11.'
     b = 'so it licenses **seven**: M1, M2, M3, M8, M9, M10, M12.'
     e = 'section names all seven axes'; benign = $false },

  @{ n = 'NC8 delete the section that records my own errors'
     a = '#### 2.9.50.6 Two errors of my own, recorded'
     b = '#### 2.9.50.6 Notes'
     e = 'records own errors'; benign = $false },

  @{ n = 'NC9 structural: delete the section 3 heading'
     a = '## 3. Gaps, ranked by what stands between here and print-worthy'
     b = ''
     e = 'section 2.9.50 terminates'; benign = $false },

  @{ n = 'NC10 misquote the gate partition'
     a = '`total=141 passed=141 failed=0 skipped=0 accounted=141`'
     b = '`total=141 passed=141 failed=0 skipped=3 accounted=141`'
     e = '2.9.50 quotes the partition verbatim'; benign = $false },

  # ---- benign: must stay GREEN ----
  @{ n = 'BENIGN-A reword prose that carries no checked claim'
     a = 'cost of not checking is not merely a wasted message'
     b = 'price of skipping that check is not merely a wasted message'
     e = ''; benign = $true },

  @{ n = 'BENIGN-B insert a blank line inside the section'
     a = '#### 2.9.50.4 I burned a capture session on purpose'
     b = "`r`n#### 2.9.50.4 I burned a capture session on purpose"
     e = ''; benign = $true }
)

$pass = 0; $wrong = 0
foreach ($c in $controls) {
  $tmp = Join-Path $env:TEMP ("nc2950-" + ($c.n -replace '[^A-Za-z0-9]', '') + ".md")
  $cnt = ([regex]::Matches($orig, [regex]::Escape($c.a))).Count
  if ($cnt -ne 1) {
    throw "MUTATION TARGET NOT UNIQUE: $($c.n) -- anchor occurs $cnt time(s): '$($c.a)'"
  }
  $mut = $orig.Replace($c.a, $c.b)
  if ($mut -eq $orig) { throw "MUTATION DID NOT ALTER THE FILE: $($c.n)" }
  Set-Content -LiteralPath $tmp -Value $mut -Encoding UTF8 -NoNewline

  $out = & "$here\v2950.ps1" -Status $tmp 2>&1 | Out-String
  $rc = $LASTEXITCODE

  if ($c.benign) {
    $ok = ($rc -eq 0)
    if ($ok) { $pass++ } else { $wrong++ }
    "{0,-58} rc={1}  -> {2}" -f $c.n, $rc, $(if ($ok) { 'GREEN  (correct)' } else { 'RED    ** WRONGLY RED **' })
  }
  else {
    $named = $out -match ("FAIL\s+" + [regex]::Escape($c.e))
    $ok = ($rc -ne 0) -and $named
    if ($ok) { $pass++ } else { $wrong++ }
    $why = if ($rc -eq 0) { '** WRONGLY GREEN **' } elseif (-not $named) { "** RED but not on '$($c.e)' **" } else { 'RED    (correct)' }
    "{0,-58} rc={1}  -> {2}" -f $c.n, $rc, $why
  }
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$neg = ($controls | Where-Object { -not $_.benign }).Count
$ben = ($controls | Where-Object { $_.benign }).Count
Write-Output ''
Write-Output "CONTROLS: $pass/$($controls.Count) correct  (negative=$neg, benign=$ben, wrong=$wrong)"
if ($wrong -gt 0) { exit 1 } else { exit 0 }
