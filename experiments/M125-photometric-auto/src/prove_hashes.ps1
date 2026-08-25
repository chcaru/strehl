# M125 -- the byte-identity proof (AGENTS.md rules 26, 39, 47).
#
# Obligations, registered in PREREGISTRATION.md section 7.3:
#
#   H1  new binary `off`, and new binary with NO env var set at all, are
#       byte-identical to the CURRENT binary's output, on two owner stacks.
#   H2  `auto` on a stack the rule DECLINES is byte-identical to `off`.
#   H3  `auto` on a stack the rule ACCEPTS is byte-identical to `on`.
#   H4  a PLANT: the same harness must be able to report an INEQUALITY, or
#       H1-H3 prove nothing. `on` vs `off` on the declining stack is the plant.
#
# Every arm records the binary, its hash, the full argv, every environment
# variable set, the exit code, the output hash and the output byte count.
#
# Rule 45: STREHL_WARPMAP is pinned into this milestone's scratch.
# Rule 46/47: the exit code is captured in the statement after the call.
# Nothing is written to D:\.

$ErrorActionPreference = "Stop"

$NEW  = "C:\dev\strehl-out\M125\bin\strehl-m125.exe"
$OLD  = "C:\dev\strehl-out\M125\bin\strehl-baseline.exe"
$ROOT = "C:\dev\strehl-out\M125"
$LIB  = "D:\personal\macro"

$ledger = New-Object System.Collections.ArrayList
$ledgerPath = Join-Path $ROOT "ledger-proof.csv"

function Clear-StrehlEnv {
    foreach ($v in @("STREHL_WARPMAP","STREHL_ALIGN","STREHL_PHOTOMETRIC","STREHL_SOFT_GATE",
                     "STREHL_FIX_CA","STREHL_FIX_HALO","STREHL_FIX_HALO_DELTA","STREHL_SMOOTH",
                     "STREHL_SMOOTH_HUBER","STREHL_DUMP_NEFF","STREHL_DUMP_ELECTION",
                     "STREHL_ROBUST_ELECTION","STREHL_DUMP_MERGE_STATE","STREHL_CACHE_DIR",
                     "STREHL_FREEZE_REQUIRE","STREHL_CAPTURES","STREHL_RESAMPLER")) {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
}

function Render {
    param([string]$Exe, [string]$Subject, [string]$Arm,
          [string[]]$Extra, [hashtable]$Env, [int]$Limit, [string]$Warp)

    $dir = Join-Path $LIB $Subject
    $out = Join-Path $ROOT "measure\$Subject`__$Arm.tif"
    if (Test-Path $out) { Remove-Item $out -Force }

    Clear-StrehlEnv
    $Env["STREHL_WARPMAP"] = $Warp
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }
    $envRecord = ($Env.GetEnumerator() | Sort-Object Name |
                  ForEach-Object { "$($_.Name)=$($_.Value)" }) -join " "

    $argv = @("stack", $dir, "--limit", "$Limit", "--gate", "4", "--out", $out) + $Extra

    $ErrorActionPreference = "Continue"
    $log  = & $Exe @argv 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    Set-Content -Path (Join-Path $ROOT "logs\proof-$Subject-$Arm.log") `
        -Value (@("# binary $Exe",
                  "# binsha $((Get-FileHash -Algorithm SHA256 $Exe).Hash)",
                  "# env    $envRecord",
                  "# argv   strehl $($argv -join ' ')",
                  "# exit   $code", "") + ($log | ForEach-Object { "$_" }))

    $hash = ""; $len = 0
    if (Test-Path $out) {
        $hash = (Get-FileHash -Algorithm SHA256 $out).Hash
        $len  = (Get-Item $out).Length
    }
    $dec = [regex]::Match((($log | ForEach-Object { "$_" }) -join "`n"),
                          'AUTO: (APPLIED|DECLINED|ABSTAINED)')
    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject; arm = $Arm; exit = $code
        sha256 = $hash; bytes = $len
        decision = $(if ($dec.Success) { $dec.Groups[1].Value } else { "-" })
        binary = (Split-Path -Leaf $Exe)
        envs = $envRecord; argv = "strehl $($argv -join ' ')"
    })
    Clear-StrehlEnv
    return $hash
}

$H = @{}
foreach ($S in @("tweezers-cpl", "bee-3-cpl")) {
    $L = 100
    $wp = Join-Path $ROOT "warp\$S-l$L.txt"
    if (-not (Test-Path $wp)) { throw "missing warp map $wp -- run run_baseline.ps1 first" }
    Write-Output "==================== $S ===================="

    # the CURRENT binary, default invocation: the control
    $H["$S/OLD-default"] = Render $OLD $S "OLDdefault" @()                        @{} $L $wp
    # the NEW binary, no environment variable set at all
    $H["$S/NEW-unset"]   = Render $NEW $S "NEWunset"   @()                        @{} $L $wp
    # the NEW binary, explicit off, via the flag and via the environment
    $H["$S/NEW-off"]     = Render $NEW $S "NEWoff"     @("--photometric","off")   @{} $L $wp
    $H["$S/NEW-envoff"]  = Render $NEW $S "NEWenvoff"  @()  @{ STREHL_PHOTOMETRIC = "off" } $L $wp
    # on and auto
    $H["$S/NEW-on"]      = Render $NEW $S "NEWon"      @("--photometric","on")    @{} $L $wp
    $H["$S/NEW-bare"]    = Render $NEW $S "NEWbare"    @("--photometric")         @{} $L $wp
    $H["$S/NEW-auto"]    = Render $NEW $S "NEWauto"    @("--photometric","auto")  @{} $L $wp

    foreach ($k in @("OLD-default","NEW-unset","NEW-off","NEW-envoff","NEW-on","NEW-bare","NEW-auto")) {
        Write-Output ("  {0,-12} {1}" -f $k, $H["$S/$k"])
    }
}

$ledger | Export-Csv -NoTypeInformation -Path $ledgerPath

Write-Output ""
Write-Output "==================== VERDICTS ===================="
$fail = 0

$checks = @(
  @{ t = "H1a tweezers  OLD default == NEW unset";      a = "tweezers-cpl/OLD-default"; b = "tweezers-cpl/NEW-unset"; eq = $true },
  @{ t = "H1b tweezers  OLD default == NEW --off";      a = "tweezers-cpl/OLD-default"; b = "tweezers-cpl/NEW-off";   eq = $true },
  @{ t = "H1c tweezers  OLD default == NEW env off";    a = "tweezers-cpl/OLD-default"; b = "tweezers-cpl/NEW-envoff";eq = $true },
  @{ t = "H1d bee-3     OLD default == NEW unset";      a = "bee-3-cpl/OLD-default";    b = "bee-3-cpl/NEW-unset";    eq = $true },
  @{ t = "H1e bee-3     OLD default == NEW --off";      a = "bee-3-cpl/OLD-default";    b = "bee-3-cpl/NEW-off";      eq = $true },
  @{ t = "H1f bee-3     OLD default == NEW env off";    a = "bee-3-cpl/OLD-default";    b = "bee-3-cpl/NEW-envoff";   eq = $true },
  @{ t = "H2  bee-3     auto (DECLINED) == off";        a = "bee-3-cpl/NEW-auto";       b = "bee-3-cpl/NEW-off";      eq = $true },
  @{ t = "H3  tweezers  auto (APPLIED)  == on";         a = "tweezers-cpl/NEW-auto";    b = "tweezers-cpl/NEW-on";    eq = $true },
  @{ t = "H3b tweezers  bare --photometric == on";      a = "tweezers-cpl/NEW-bare";    b = "tweezers-cpl/NEW-on";    eq = $true },
  @{ t = "H4a PLANT bee-3    on != off";                a = "bee-3-cpl/NEW-on";         b = "bee-3-cpl/NEW-off";      eq = $false },
  @{ t = "H4b PLANT tweezers on != off";                a = "tweezers-cpl/NEW-on";      b = "tweezers-cpl/NEW-off";   eq = $false },
  @{ t = "H4c PLANT bee-3 auto != tweezers auto";       a = "bee-3-cpl/NEW-auto";       b = "tweezers-cpl/NEW-auto";  eq = $false }
)
foreach ($c in $checks) {
    $same = ($H[$c.a] -eq $H[$c.b]) -and $H[$c.a] -ne ""
    $ok = ($same -eq $c.eq)
    if (-not $ok) { $fail++ }
    Write-Output ("  {0}  {1,-46} {2}" -f $(if ($ok) { "PASS" } else { "FAIL" }), $c.t,
                  $(if ($same) { "identical" } else { "different" }))
}
Write-Output ""
Write-Output "PROOF: $($checks.Count - $fail)/$($checks.Count) obligations met"
Write-Output "PROOF-DONE"
