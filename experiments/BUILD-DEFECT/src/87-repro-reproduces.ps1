<#
.SYNOPSIS
Does the sidecar's reproduction command actually reproduce the master?

.DESCRIPTION
THE CLAIM UNDER TEST, AND WHY READING IT IS NOT ENOUGH.

Every master written by scripts/finalpass.ps1 carries a `.provenance.txt`
sidecar ending in a block headed "REPRODUCE THIS EXACT FILE:". That block is an
INSTRUCTION. This project has already shipped 26 sidecars whose instruction was
wrong -- it substituted `--exposure <stops>` for `--auto-exposure`, which on a
binary where `--exposure` is load-bearing clips 85.5% of the frame to white --
and the defect survived review because everyone who checked it READ it. It
looked right. It was verified by argument.

So this script does not read the block. It extracts the lines a naive user
would copy, runs them, and compares the resulting file to the original AS
BYTES.

THE NEGATIVE CONTROL IS THE POINT, NOT AN EXTRA.

A test that only runs the correct form and sees it pass cannot distinguish
"the reproduction command is right" from "any command reproduces this file" --
and the second is not absurd: if the fix under test changed nothing, an
env-less command would match too, and the test would read green while
certifying nothing.

So the ARGV-ONLY arm runs FIRST and must FAIL. It is the previous contract
exactly: the flags alone, in a shell where every render-affecting variable has
been cleared. That is what a user got before this change. If it produces the
same bytes, this script says so and exits non-zero, because then it has not
demonstrated that the environment half of the command is load-bearing and the
green from the verbatim arm is unearned.

  ARGV-ONLY  (must differ)  the old contract: flags, no environment.
  VERBATIM   (must match)   the whole block, exactly as printed.

Both arms write to their own scratch file and neither touches the original.

.EXAMPLE
pwsh -File 87-repro-reproduces.ps1 -Master D:\strehl-out\BUILD-DEFECT\ship-validate\coffee-bubbles--ship-validate.tiff
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Master,
    [string]$Scratch = 'D:\strehl-out\BUILD-DEFECT\repro-check'
)

$ErrorActionPreference = 'Stop'

function Get-ReproBlock {
    <#
      Extract the copyable lines from the sidecar.

      Anchored on the header and terminated by the trailing prose line, which
      begins with "...". Every kept line is indented exactly two spaces by the
      emitter, so exactly two are stripped -- not `TrimStart()`, which would
      also eat the deliberate indentation of the continuation line and change
      what is executed.
    #>
    param([string]$Sidecar)

    $lines = Get-Content $Sidecar
    $start = ($lines | Select-String -SimpleMatch 'REPRODUCE THIS EXACT FILE:' | Select-Object -First 1)
    if (-not $start) { throw "no 'REPRODUCE THIS EXACT FILE:' header in $Sidecar" }
    $i = $start.LineNumber   # 1-based; this IS the index of the line after the header

    $body = @()
    while ($i -lt $lines.Count) {
        $ln = $lines[$i]
        if ($ln -match '^\s*\.\.\.') { break }
        if ($ln -match '^\s*OBSERVED, NOT AN INSTRUCTION') { break }
        if ($ln.Trim() -eq '' -and $body.Count -gt 0) { break }
        $body += $(if ($ln.StartsWith('  ')) { $ln.Substring(2) } else { $ln })
        $i++
    }
    if (-not $body) { throw "reproduction block in $Sidecar is empty" }
    return $body
}

function Invoke-Arm {
    param([string[]]$Body, [string]$OutFile, [switch]$ArgvOnly, [string]$Tag)

    # The invocation is the line naming the executable. Everything else in the
    # block is environment setup or a comment.
    $exeIdx = -1
    for ($j = 0; $j -lt $Body.Count; $j++) {
        if ($Body[$j] -match 'strehl\.exe\s') { $exeIdx = $j; break }
    }
    if ($exeIdx -lt 0) { throw "no strehl.exe invocation in the reproduction block" }

    $script = if ($ArgvOnly) {
        # The OLD contract, reconstructed honestly: a clean shell and the flags.
        # The clearing lines are kept because without them this arm would
        # inherit whatever the caller had set and would be measuring the
        # caller's shell rather than the contract.
        @($Body[0..($exeIdx - 1)] | Where-Object { $_ -notmatch '^\s*\$env:' }) + @($Body[$exeIdx])
    }
    else {
        $Body
    }
    $script = $script | ForEach-Object { $_ -replace '<OUT>', $OutFile }

    $f = Join-Path ([IO.Path]::GetTempPath()) "87-repro-$Tag.ps1"
    $script -join "`r`n" | Set-Content $f -Encoding UTF8
    Remove-Item $OutFile -ErrorAction SilentlyContinue

    $log = Join-Path ([IO.Path]::GetTempPath()) "87-repro-$Tag.log"
    & pwsh -NoProfile -File $f *> $log
    $code = $LASTEXITCODE
    return [pscustomobject]@{
        Exit   = $code
        Out    = $OutFile
        Sha    = $(if (Test-Path $OutFile) { (Get-FileHash $OutFile -Algorithm SHA256).Hash } else { $null })
        Bytes  = $(if (Test-Path $OutFile) { (Get-Item $OutFile).Length } else { 0 })
        Script = $f
        Log    = $log
    }
}

New-Item -ItemType Directory -Force -Path $Scratch | Out-Null
$rows = @()
$nPass = 0; $nFail = 0; $nInconclusive = 0

foreach ($m in $Master) {
    $name = Split-Path $m -LeafBase
    Write-Host "=== $name"
    if (-not (Test-Path $m)) { throw "no master at $m" }
    $orig = (Get-FileHash $m -Algorithm SHA256).Hash
    $body = Get-ReproBlock "$m.provenance.txt"
    Write-Host "    original sha256 : $orig"
    Write-Host "    repro block     : $($body.Count) line(s)"

    # NEGATIVE CONTROL FIRST. It must differ, or the verbatim green is unearned.
    $neg = Invoke-Arm -Body $body -OutFile (Join-Path $Scratch "$name.argvonly.tiff") -ArgvOnly -Tag "$name-neg"
    $negDiffers = ($neg.Sha -ne $orig)
    Write-Host ("    ARGV-ONLY       : exit {0} sha {1} -> {2}" -f $neg.Exit,
        $(if ($neg.Sha) { $neg.Sha.Substring(0, 12) } else { '(no file)' }),
        $(if ($negDiffers) { 'DIFFERS, as required' } else { 'MATCHES -- control did not bite' }))

    $pos = Invoke-Arm -Body $body -OutFile (Join-Path $Scratch "$name.verbatim.tiff") -Tag "$name-pos"
    $posMatches = ($pos.Sha -eq $orig)
    Write-Host ("    VERBATIM        : exit {0} sha {1} -> {2}" -f $pos.Exit,
        $(if ($pos.Sha) { $pos.Sha.Substring(0, 12) } else { '(no file)' }),
        $(if ($posMatches) { 'BYTE-IDENTICAL' } else { 'DIFFERS -- THE SIDECAR DOES NOT REPRODUCE' }))

    $verdict = if (-not $negDiffers) {
        $nInconclusive++
        'INCONCLUSIVE -- the argv-only control produced the same bytes, so this subject cannot demonstrate that the environment half of the command matters'
    }
    elseif ($posMatches) { $nPass++; 'PASS -- reproduces byte-for-byte, and the control proves the test could have failed' }
    else { $nFail++; 'FAIL -- the printed command does not reproduce the file it sits beside' }
    Write-Host "    VERDICT         : $verdict"

    $rows += [pscustomobject]@{
        Subject = $name; Original = $orig
        ArgvOnlySha = $neg.Sha; ArgvOnlyExit = $neg.Exit; ArgvOnlyDiffers = $negDiffers
        VerbatimSha = $pos.Sha; VerbatimExit = $pos.Exit; VerbatimMatches = $posMatches
        Verdict = $verdict
    }
    Remove-Item $neg.Out, $pos.Out -ErrorAction SilentlyContinue
}

$total = $rows.Count
Write-Host ""
Write-Host "$total master(s) = $nPass pass + $nFail fail + $nInconclusive inconclusive"
if ($nPass + $nFail + $nInconclusive -ne $total) { throw "partition does not sum" }

$dst = Join-Path (Split-Path $PSScriptRoot -Parent) 'out\87-repro-reproduces.json'
$rows | ConvertTo-Json -Depth 4 | Out-File -Encoding utf8 $dst
Write-Host "wrote $dst"

if ($nFail -gt 0) { exit 1 }
if ($nInconclusive -gt 0) { exit 2 }
exit 0
