param()

# Negative controls for v-owner0906.ps1.
#
# Owner-facing defects are the expensive kind: the owner acts on this file with
# his own time and money. Each control plants one such defect into a COPY in
# $env:TEMP and requires the verifier to fail the SPECIFIC named check that
# defect targets. Merely going RED is not enough -- a checker that fails for an
# unrelated reason would look identical.
#
# Anchors are single-line by construction and asserted unique before use. An
# anchor that does not land makes a control silently GREEN, which is the worst
# outcome a control can have; two controls elsewhere today failed exactly that
# way by spanning a line break.
#
# Benign controls perturb the file in ways that must NOT trip the verifier,
# because a checker that fails on everything would otherwise sweep.

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$src = Resolve-Path "$here\..\..\docs\OWNER-ACTIONS.md"
$orig = Get-Content -LiteralPath $src -Raw -Encoding UTF8
# Second mutable input. A control may target either document; the verifier reads
# both, so a control that can only reach OWNER-ACTIONS would leave the
# evidence-reading half of the verifier uncommissioned.
$srcM157 = Resolve-Path "$here\..\..\docs\research\M157-comparator-viability.md"
$origM157 = Get-Content -LiteralPath $srcM157 -Raw -Encoding UTF8

$controls = @(
  @{ n = 'NC1 corrupt the measured reproduction ratio'
     a = '> measured rig the conservative converter-on ratio is `2.7015`, so a nominal'
     b = '> measured rig the conservative converter-on ratio is `2.9015`, so a nominal'
     e = 'owner note states 2.7015 at its canonical site'; benign = $false },

  @{ n = 'NC2 restore my nominal-label error as fact'
     a = '> **One correction, and it is mine.** I wrote that this yields `2.8/1.4 = 2.0`'
     b = '> **Confirmed.** The route yields `2.8/1.4 = 2.0`'
     e = 'owner note owns the label error'; benign = $false },

  @{ n = 'NC3 claim the failing nominal state clears the bar'
     a = '> `1.40x` scored state gives `1.9296` — **below the bar, not at it.** The route'
     b = '> `1.40x` scored state gives `1.9296` — comfortably above the bar. The route'
     e = 'owner note says below the bar'; benign = $false },

  @{ n = 'NC4 delete the do-not-shoot-yet warning'
     a = '> `BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE`. **Do not shoot'
     b = '> `READY`. **Go ahead and shoot'
     e = 'owner note quotes the revised state'; benign = $false },

  @{ n = 'NC5 oversell the burned session (delete its limitation)'
     a = 'its own: the four stacks lack the'
     b = 'its own, and in fact it can score the axis outright: the four stacks lack the'
     e = 'Ask 5 limitation stated at its canonical site'; benign = $false },

  @{ n = 'NC6 corrupt a frame count the owner would reshoot from'
     a = 'frames across `tilted-sw4` (182), `tilted-sw10` (92), `flat-sw4` (186) and'
     b = 'frames across `tilted-sw4` (128), `tilted-sw10` (92), `flat-sw4` (186) and'
     e = 'Ask 5 states every per-stack count'; benign = $false },

  @{ n = 'NC7 quietly change the Zerene price'
     a = '## Ask 3 — buy Zerene **Professional, $289**.'
     b = '## Ask 3 — buy Zerene **Professional, $389**.'
     e = 'Zerene ask still says Professional $289'; benign = $false },

  @{ n = 'NC8 reinstate the Helicon purchase'
     a = '### Do not buy Helicon yet'
     b = '### Buy Helicon now'
     e = 'Helicon still not recommended for purchase'; benign = $false },

  @{ n = 'NC9 miscount the licensed axes to the owner'
     a = '> so it licenses **seven**: M1, M2, M3, M8, M9, M10, M11. It names no instrument'
     b = '> so it licenses **seven**: M1, M2, M3, M8, M9, M10, M12. It names no instrument'
     e = 'owner note states seven axes'; benign = $false },

  @{ n = 'NC10 disown the error (blame the owner plan)'
     a = '> anyway, and separately had made **Helicon mandatory** where your plan says'
     b = '> anyway, because your plan required it. Your plan also says'
     e = 'owner note attributes Helicon requirement to ME'; benign = $false },

  @{ n = 'NC11 hide that the five axes stay publishable'
     a = '> and their results will still be published; they no longer gate your claim.**'
     b = '> and they are dropped from the program entirely.**'
     e = 'owner note keeps the five publishable'; benign = $false },

  # ---- 2026-09-06, M157: the purchase gate vs the technical gate ----
  @{ n = 'NC12 claim the purchase closes the technical gate'
     a = 'So the honest position is: **a Zerene purchase clears the licence gate but'
     b = 'So the honest position is: **a Zerene purchase closes every gate at once and'
     e = 'owner note states purchase != gate closed'; benign = $false },

  @{ n = 'NC13 drop linearity from the vendor email'
     a = '>    the data is **linear**, or whether a gamma or tone curve is applied on the'
     b = '>    the data is acceptable, or whether some curve is applied on the'
     e = 'owner email asks all five sub-questions'; benign = $false },

  @{ n = 'NC14 let him buy anyway on a bad answer'
     a = '"gamma-encoded" or "8-bit only", tell me before buying; the comparison protocol'
     b = '"gamma-encoded" or "8-bit only", go ahead and buy; the comparison protocol'
     e = 'owner note tells him to stop if 8-bit'; benign = $false },

  @{ n = 'NC15 put a price on the free ask'
     a = '## Ask 1 — send one email. **$0, five minutes.** No deadline, but do it before any purchase.'
     b = '## Ask 1 — send one email. **$40, five minutes.** No deadline, but do it before any purchase.'
     e = 'Ask 1 still costs nothing'; benign = $false },

  @{ n = 'NC18 let the page go stale about its own currency'
     a = 'Maintained by the orchestrator. Last updated after lanes M157, M159, M160, M161.'
     b = 'Maintained by the orchestrator. Last updated after lanes M147, M149, M150.'
     e = 'page names the lanes it now reflects'; benign = $false },

  # Commissions the CROSS-FILE lookup: citing a section that does not exist must
  # be caught by reading STATUS, not by pattern-matching this page.
  @{ n = 'NC19 cite a STATUS section that does not exist'
     a = 'in `docs/STATUS.md` §2.9.28-2.9.52 and the lane reports named below.'
     b = 'in `docs/STATUS.md` §2.9.28-2.9.99 and the lane reports named below.'
     e = 'STATUS actually has the section cited'; benign = $false },

  # ---- SOURCE-SIDE controls: mutate the LANE REPORT, not this document. ----
  @{ n = 'NC16 [source] upgrade NOT FOUND to a verified contract'
     f = 'm157'
     a = '**[NOT FOUND]** Neither statement is explicitly attached to'
     b = '**[VERIFIED]** The linear 16-bit contract is explicitly attached to'
     e = 'M157 rules the linear contract NOT FOUND'; benign = $false },

  @{ n = 'NC17 [source] corrupt an edition price in the brief'
     f = 'm157'
     a = 'Prosumer Edition, $189 USD'
     b = 'Prosumer Edition, $289 USD'
     e = 'M157 records both edition prices'; benign = $false },

  # ---- benign: must stay GREEN ----
  @{ n = 'BENIGN-A reword prose carrying no checked claim'
     a = 'I spent it, and I would make the same call again.'
     b = 'I spent it, and on the same evidence I would decide identically.'
     e = ''; benign = $true },

  @{ n = 'BENIGN-B insert a heading-adjacent blank line'
     a = '## Ask 5 — reshoot the calibration slide, eventually.'
     b = "`r`n## Ask 5 — reshoot the calibration slide, eventually."
     e = ''; benign = $true }
)

$pass = 0; $wrong = 0
foreach ($c in $controls) {
  $which = if ($c.ContainsKey('f')) { $c.f } else { 'owner' }
  $base = if ($which -eq 'm157') { $origM157 } else { $orig }
  $tmp = Join-Path $env:TEMP ("ncown-" + ($c.n -replace '[^A-Za-z0-9]', '') + ".md")
  $cnt = ([regex]::Matches($base, [regex]::Escape($c.a))).Count
  if ($cnt -ne 1) { throw "MUTATION TARGET NOT UNIQUE: $($c.n) -- anchor occurs $cnt time(s): '$($c.a)'" }
  $mut = $base.Replace($c.a, $c.b)
  if ($mut -eq $base) { throw "MUTATION DID NOT ALTER THE FILE: $($c.n)" }
  Set-Content -LiteralPath $tmp -Value $mut -Encoding UTF8 -NoNewline

  $out = if ($which -eq 'm157') {
    & "$here\v-owner0906.ps1" -M157 $tmp 2>&1 | Out-String
  } else {
    & "$here\v-owner0906.ps1" -Owner $tmp 2>&1 | Out-String
  }
  $rc = $LASTEXITCODE

  if ($c.benign) {
    $ok = ($rc -eq 0)
    if ($ok) { $pass++ } else { $wrong++ }
    "{0,-52} rc={1}  -> {2}" -f $c.n, $rc, $(if ($ok) { 'GREEN  (correct)' } else { 'RED    ** WRONGLY RED **' })
  }
  else {
    $named = $out -match ("FAIL\s+" + [regex]::Escape($c.e))
    $ok = ($rc -ne 0) -and $named
    if ($ok) { $pass++ } else { $wrong++ }
    $why = if ($rc -eq 0) { '** WRONGLY GREEN **' } elseif (-not $named) { "** RED but not on '$($c.e)' **" } else { 'RED    (correct)' }
    "{0,-52} rc={1}  -> {2}" -f $c.n, $rc, $why
  }
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$neg = ($controls | Where-Object { -not $_.benign }).Count
$ben = ($controls | Where-Object { $_.benign }).Count
Write-Output ''
Write-Output "CONTROLS: $pass/$($controls.Count) correct  (negative=$neg, benign=$ben, wrong=$wrong)"
if ($wrong -gt 0) { exit 1 } else { exit 0 }
