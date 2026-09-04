$ErrorActionPreference = 'Stop'
$src = 'C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-09-sota-scorecard.md'
$ver = 'C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-verify\v-scope.ps1'
$raw = Get-Content $src -Raw

$controls = @(
  @{ n = 'NC1 silently restore mandatory Helicon'
     a = 'licensed Zerene Stacker plus the fork at its best-known build'
     b = 'licensed Zerene Stacker and Helicon Focus, both mandatory'
     e = 'required set = Zerene + fork' },
  @{ n = 'NC2 drop two axes from the seven'
     a = '`M1`, `M2`, `M3`, `M8`, `M9`, `M10`, `M11`'
     b = '`M1`, `M2`, `M3`, `M8`, `M9`'
     e = 'seven listed in pub rule' },
  @{ n = 'NC3 quietly retract the M8 FAIL'
     a = 'M8 still reads `FAIL`, on M8-R at'
     b = 'M8 is provisionally cleared pending re-measurement, formerly at'
     e = 'M8 FAIL explicitly preserved' },
  @{ n = 'NC4 make the five additions fatal again'
     a = 'they are not prerequisites for the owner'
     b = 'they remain prerequisites for the owner'
     e = 'additions not prerequisites' },
  @{ n = 'NC5 un-withdraw the old text (leave it operative)'
     a = 'satisfies every clause of that sentence against the licensed'
     b = 'passes every primary bar below against licensed Zerene Stacker and more'
     e = 'old text occurs exactly once' },
  @{ n = 'NC6 delete the independent-verification claim'
     a = 'rather than accepting the audit'
     b = 'as reported by the audit'
     e = 'verified independently, stated' }
)

$tmp = Join-Path $env:TEMP 'nc_scope_scorecard.md'
$red = 0; $green = 0
foreach ($c in $controls) {
  $count = ([regex]::Matches($raw, [regex]::Escape($c.a))).Count
  if ($count -lt 1) { throw "MUTATION TARGET NOT FOUND: $($c.n) -- anchor '$($c.a)'" }
  Set-Content -Path $tmp -Value ($raw.Replace($c.a, $c.b)) -Encoding UTF8 -NoNewline
  $out = & $ver -ScorecardPath $tmp 2>&1
  $rc = $LASTEXITCODE
  $hit = ($out | Where-Object { $_ -match [regex]::Escape("FAIL  $($c.e)") }).Count -ge 1
  $verdict = if ($rc -ne 0 -and $hit) { $red++; 'RED  (correct)' } else { $green++; 'GREEN (BAD)' }
  "{0,-52} anchors={1}  rc={2}  -> {3}" -f $c.n, $count, $rc, $verdict
  if ($rc -ne 0 -and -not $hit) { "    !! RED but not on '$($c.e)' -- failing for the wrong reason" }
}
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
""
"NEGATIVE CONTROLS: $red correctly RED, $green wrongly GREEN"
if ($green -gt 0) { exit 1 } else { exit 0 }
