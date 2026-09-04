$ErrorActionPreference = 'Stop'
$src = 'C:\dev\blog\death-of-software\projects\strehl\docs\STATUS.md'
$ver = 'C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-verify\v2949b.ps1'
$raw = Get-Content $src -Raw

$controls = @(
  @{ n = 'NC1 restore the fabricated quotation as if real'
     a = 'same manoeuvre reads *"Narrowing rule 4 unlocks nothing today"*.'
     b = 'same manoeuvre reads *"it changes nothing measurable today."*'
     e = 'STATUS uses the REAL annotation' },
  @{ n = 'NC2 claim an axis was scored'
     a = '**Unchanged: `0 of 12`.** Four instruments got more trustworthy'
     b = '**Now: `1 of 12`.** Four instruments got more trustworthy'
     e = 'position still 0 of 12 (pinned to 2.9.49)' },
  @{ n = 'NC3 reinstate M154 defect 5'
     a = '* **M10 depth** — no depth product exists; and the ruler'
     b = '* **M10 depth** — no depth product exists; the ruler record says only x. The ruler'
     e = 'defect5: "says only" gone' },
  @{ n = 'NC4 soften the admission of authorship'
     a = 'and the careful reader was'
     b = 'and the careful reader was probably'
     e = 'admits the reader was me' },
  @{ n = 'NC5 drop the M146 citation'
     a = 'M146-unlock-audit.md'
     b = 'some-audit.md'
     e = 'STATUS cites M146 for the audit' }
)

$tmp = Join-Path $env:TEMP 'nc2949_status.md'
$red = 0; $green = 0
foreach ($c in $controls) {
  $count = ([regex]::Matches($raw, [regex]::Escape($c.a))).Count
  if ($count -lt 1) { throw "MUTATION TARGET NOT FOUND: $($c.n) -- anchor '$($c.a)'" }
  Set-Content -Path $tmp -Value ($raw.Replace($c.a, $c.b)) -Encoding UTF8 -NoNewline
  $out = & $ver -StatusPath $tmp 2>&1
  $rc = $LASTEXITCODE
  $hitExpected = ($out | Where-Object { $_ -match [regex]::Escape("FAIL  $($c.e)") }).Count -ge 1
  $verdict = if ($rc -ne 0 -and $hitExpected) { $red++; 'RED  (correct)' } else { $green++; 'GREEN (BAD)' }
  "{0,-46} anchors={1}  rc={2}  -> {3}" -f $c.n, $count, $rc, $verdict
  if ($rc -ne 0 -and -not $hitExpected) {
    "    !! went RED but NOT on the expected check '$($c.e)' -- verifier is failing for the wrong reason"
  }
}
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
""
"NEGATIVE CONTROLS: $red correctly RED, $green wrongly GREEN"
if ($green -gt 0) { exit 1 } else { exit 0 }
