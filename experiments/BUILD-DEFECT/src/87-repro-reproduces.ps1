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
    [string]$Scratch = 'D:\strehl-out\BUILD-DEFECT\repro-check',
    [string]$OutJson,
    [switch]$Commission
)

$ErrorActionPreference = 'Stop'
if (-not $OutJson) {
    $OutJson = Join-Path (Split-Path $PSScriptRoot -Parent) 'out\87-repro-reproduces.json'
}

function Edit-Anchored {
    <#
      Mutate a file on ONE anchored, counted site, or refuse.

      A commissioning plant that silently fails to land produces a second null
      arm wearing the plant's name, and reads as a pass. This lane has already
      been bitten by exactly that: 86-coords-control's first run reported "both
      arms identical" while a PowerShell -replace had not landed and both arms
      held the same file. So the occurrence count is asserted BEFORE the write
      and the result is re-read FROM DISK afterwards.
    #>
    param([string]$Path, [string]$Old, [string]$New, [int]$Expect = 1)
    $t = [IO.File]::ReadAllText($Path)
    $n = ([regex]::Matches($t, [regex]::Escape($Old))).Count
    if ($n -ne $Expect) {
        throw ("MUTATION TARGET NOT FOUND in ${Path}: expected $Expect occurrence(s) of " +
            "'$Old', found $n. A plant that does not land is a second null, not a pass.")
    }
    [IO.File]::WriteAllText($Path, $t.Replace($Old, $New))
    $v = [IO.File]::ReadAllText($Path)
    if ($v.Contains($Old)) { throw "MUTATION DID NOT PERSIST in $Path" }
    if ($New -and -not $v.Contains($New)) { throw "MUTATION NOT PRESENT ON DISK in $Path" }
}

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

if ($Commission) {
    <#
      COMMISSION THE FOUR OUTCOMES.

      Section 23.9's drift finding arrived as an accident -- a neighbouring lane
      rebuilt the binary under this lane's feet. An accident is not an
      instrument. These arms reproduce each verdict on demand, from a copy, and
      require the one that is due.

      The arms are deliberately not all degradations. B_DRIFT and C_WRONGCMD are
      two DIFFERENT defects that the old three-outcome instrument collapsed into
      one, so the pair is what proves the split is real: if the drift check were
      over-eager it would swallow C_WRONGCMD and report DRIFTED for a genuinely
      broken command, which is the exact failure mode that makes a verifier
      useless. A_NULL is the clean read, without which a check that always says
      DRIFTED would score three of three.

      D_IMPLIED exists because C_WRONGCMD's first form was INERT. It deleted the
      `$env:STREHL_DEFECT = 'on'` line, expecting the correction to switch off,
      and the arm reported PASS. The instrument was right and the plant was
      wrong: `stack.rs:897` reads `STREHL_DEFECT_MAP` first and it *implies* on,
      documented at `stack.rs:864-867` -- "naming a map is asking for it". So
      that mutation removes a line the command does not need. Rather than delete
      the arm, it is kept with the verdict it actually earns: a mutation that
      must NOT move the outcome. Paired with C_WRONGCMD, which must, it is the
      discrimination test -- an instrument that fires on any edit passes C and
      fails D, and one that fires on none passes D and fails C.
    #>
    $src = $Master[0]
    $croot = Join-Path $Scratch 'commission'
    Remove-Item -Recurse -Force $croot -ErrorAction SilentlyContinue
    $arms = @(
        @{ Name = 'A_NULL'; Why = 'untouched copy'
           Mutate = $null; Want = 'PASS'; WantExit = 0 }
        @{ Name = 'B_DRIFT'; Why = "sidecar's recorded binary sha256 changed"
           Mutate = 'binary'; Want = 'BINARY-DRIFTED'; WantExit = 3 }
        @{ Name = 'C_WRONGCMD'; Why = "the repro block's arm becomes 'none' -- valid, runs clean, renders a different image"
           Mutate = 'command'; Want = 'FAIL'; WantExit = 1 }
        @{ Name = 'D_IMPLIED'; Why = "the repro block loses STREHL_DEFECT='on'; _MAP implies it, so the outcome must NOT move"
           Mutate = 'implied'; Want = 'PASS'; WantExit = 0 }
    )
    $caught = 0; $missed = 0
    Write-Host "=== COMMISSIONING: require each outcome on an arm built to deserve it ==="
    Write-Host "    source master   : $(Split-Path $src -Leaf)"
    foreach ($a in $arms) {
        $d = Join-Path $croot $a.Name
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        $mCopy = Join-Path $d (Split-Path $src -Leaf)
        Copy-Item $src $mCopy
        Copy-Item "$src.provenance.txt" "$mCopy.provenance.txt"
        $side = "$mCopy.provenance.txt"

        if ($a.Mutate -eq 'binary') {
            $line = (Get-Content $side | Where-Object { $_ -match '^sha256\s*:' } | Select-Object -First 1)
            if (-not $line) { throw "no 'sha256 :' line in $side to anchor on" }
            Edit-Anchored -Path $side -Old $line -New ($line -replace '[0-9A-F]{64}',
                'DEADBEEF00000000000000000000000000000000000000000000000000000000')
        }
        elseif ($a.Mutate -eq 'command') {
            $line = (Get-Content $side | Where-Object { $_ -match "STREHL_DEFECT_ARM\s*=\s*'dust'" } | Select-Object -First 1)
            if (-not $line) { throw "no STREHL_DEFECT_ARM assignment in $side to anchor on" }
            Edit-Anchored -Path $side -Old $line -New ($line -replace "'dust'", "'none'")
        }
        elseif ($a.Mutate -eq 'implied') {
            $line = (Get-Content $side | Where-Object { $_ -match "STREHL_DEFECT\s*=\s*'on'" } | Select-Object -First 1)
            if (-not $line) { throw "no STREHL_DEFECT assignment in $side to anchor on" }
            Edit-Anchored -Path $side -Old "$line`r`n" -New ''
        }

        $j = Join-Path $d 'result.json'
        & pwsh -NoProfile -File $PSCommandPath -Master $mCopy -Scratch $d -OutJson $j *> (Join-Path $d 'arm.log')
        $exit = $LASTEXITCODE
        $got = if (Test-Path $j) { (Get-Content $j -Raw | ConvertFrom-Json).Verdict } else { '(no result)' }
        $verdictOk = ("$got".StartsWith($a.Want)) -and ($exit -eq $a.WantExit)
        if ($verdictOk) { $caught++ } else { $missed++ }
        Write-Host ("    {0,-11} {1,-14} want {2}/exit {3}  got exit {4}  {5}" -f
            $a.Name, $a.Why.Substring(0, [Math]::Min(14, $a.Why.Length)), $a.Want, $a.WantExit,
            $exit, $(if ($verdictOk) { 'CAUGHT' } else { "MISSED -- got '$got'" }))
        Remove-Item $mCopy -ErrorAction SilentlyContinue
    }
    Write-Host ""
    Write-Host "$($arms.Count) arms = $caught caught + $missed missed"
    if ($caught + $missed -ne $arms.Count) { throw 'partition does not sum' }
    $cj = Join-Path (Split-Path $PSScriptRoot -Parent) 'out\87-commission.json'
    @{ arms = @($arms | ForEach-Object { @{ name = $_.Name; want = $_.Want; want_exit = $_.WantExit; why = $_.Why } })
       caught = $caught; missed = $missed
       verdict = $(if ($missed -eq 0) { 'COMMISSIONED' } else { 'NOT-COMMISSIONED' }) } |
        ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 $cj
    Write-Host "wrote $cj"
    Write-Host ""
    Write-Host "VERDICT: $(if ($missed -eq 0) { 'COMMISSIONED' } else { 'NOT-COMMISSIONED' })"
    exit $(if ($missed -eq 0) { 0 } else { 2 })
}

$rows = @()
$nPass = 0; $nFail = 0; $nInconclusive = 0; $nDrifted = 0

foreach ($m in $Master) {
    $name = Split-Path $m -LeafBase
    Write-Host "=== $name"
    if (-not (Test-Path $m)) { throw "no master at $m" }
    $orig = (Get-FileHash $m -Algorithm SHA256).Hash
    $body = Get-ReproBlock "$m.provenance.txt"
    Write-Host "    original sha256 : $orig"
    Write-Host "    repro block     : $($body.Count) line(s)"

    # IS THIS EVEN THE BINARY THE SIDECAR NAMES?
    #
    # This check was missing on the first version of this script and it cost a
    # false FAIL on two subjects that had passed forty minutes earlier. Another
    # lane committed crates/strehl-core/src/optics.rs, a `cargo test` rebuilt
    # strehl.exe in place, and the reproduction command -- which names a PATH,
    # not a hash -- then invoked a DIFFERENT binary. Both masters duly came back
    # as "the sidecar does not reproduce".
    #
    # That verdict was wrong, and wrong in the expensive direction: it accuses
    # the artifact under test. Section 22 measured the actual contract and it is
    # explicit -- the command is bit-exact WITH THE BINARY IT NAMES, and its
    # whole design point is that it survives a binary change by not pinning
    # image-dependent values into itself. A binary that has moved is therefore
    # not a failure of the command; it is a different question, and the sidecar
    # already records the answer as `sha256`.
    #
    # So it is a fourth counted outcome. Collapsing it into FAIL would mean this
    # instrument reports "your provenance is broken" every time a neighbouring
    # lane commits.
    $declared = (Get-Content "$m.provenance.txt" | Select-String -Pattern '^sha256\s*:' |
        Select-Object -First 1) -replace '^sha256\s*:\s*', ''
    $exeLine = ($body | Where-Object { $_ -match 'strehl\.exe\s' } | Select-Object -First 1)
    $exePath = if ($exeLine -match '^\s*(.*?strehl\.exe)\s') { $Matches[1] } else { $null }
    $actual = if ($exePath -and (Test-Path $exePath)) { (Get-FileHash $exePath -Algorithm SHA256).Hash } else { $null }
    $binaryMatches = ($declared -and $actual -and $declared.Trim() -eq $actual)
    Write-Host ("    binary          : sidecar {0} / on disk {1} -> {2}" -f
        $(if ($declared) { $declared.Trim().Substring(0, 12) } else { '(none)' }),
        $(if ($actual) { $actual.Substring(0, 12) } else { '(missing)' }),
        $(if ($binaryMatches) { 'same binary' } else { 'DRIFTED' }))

    if (-not $binaryMatches) {
        $nDrifted++
        $verdict = ("BINARY-DRIFTED -- the binary at the path this command names is not the one " +
            "that rendered the master. The command cannot be tested against this master; " +
            "re-render, or fetch the binary the sidecar names. This is NOT a failure of the " +
            "reproduction command.")
        Write-Host "    VERDICT         : $verdict"
        $rows += [pscustomobject]@{
            Subject = $name; Original = $orig
            DeclaredBinary = $declared.Trim(); ActualBinary = $actual
            ArgvOnlySha = $null; ArgvOnlyExit = $null; ArgvOnlyDiffers = $null
            VerbatimSha = $null; VerbatimExit = $null; VerbatimMatches = $null
            Verdict = $verdict
        }
        continue
    }

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
        DeclaredBinary = $declared.Trim(); ActualBinary = $actual
        ArgvOnlySha = $neg.Sha; ArgvOnlyExit = $neg.Exit; ArgvOnlyDiffers = $negDiffers
        VerbatimSha = $pos.Sha; VerbatimExit = $pos.Exit; VerbatimMatches = $posMatches
        Verdict = $verdict
    }
    Remove-Item $neg.Out, $pos.Out -ErrorAction SilentlyContinue
}

$total = $rows.Count
Write-Host ""
Write-Host "$total master(s) = $nPass pass + $nFail fail + $nInconclusive inconclusive + $nDrifted binary-drifted"
if ($nPass + $nFail + $nInconclusive + $nDrifted -ne $total) { throw "partition does not sum" }

$dst = $OutJson
New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
$rows | ConvertTo-Json -Depth 4 | Out-File -Encoding utf8 $dst
Write-Host "wrote $dst"

if ($nFail -gt 0) { exit 1 }
if ($nInconclusive -gt 0) { exit 2 }
if ($nDrifted -gt 0) { exit 3 }
exit 0
