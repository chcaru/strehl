# M97 --n-eff-map -- E-series bars. Rule 47: capture output first, read
# $LASTEXITCODE immediately, filter afterwards, record LITERAL exit codes.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\e1"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

# STREHL_ALIGN=0 removes the sidecar cache as a confound: these bars are about
# the export mechanism, not about registration.
$env:STREHL_CACHE_DIR = "$out\cache"
$env:STREHL_ALIGN = "0"
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

function Sha($p) {
    if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0, 16) } else { "NOFILE" }
}

function Run($name, $gates, $mapFlag, $mapEnv) {
    if ($mapEnv) { $env:STREHL_DUMP_NEFF = $mapEnv }
    else { Remove-Item Env:\STREHL_DUMP_NEFF -ErrorAction SilentlyContinue }

    $a = @("stack", $dir, "--limit", "20", "--out", "$out\$name.tiff")
    foreach ($g in $gates) { $a += @("--gate", $g) }
    if ($mapFlag) { $a += @("--n-eff-map", $mapFlag) }

    $o = & $exe @a 2>&1
    $code = $LASTEXITCODE                       # read IMMEDIATELY, unfiltered
    $o | Out-String | Set-Content -Encoding utf8 "$out\$name.log"
    Write-Output ("{0,-10} EXIT={1} IMG={2}" -f $name, $code, (Sha "$out\$name.tiff"))
}

# --out forbids >1 gate, so arm F omits it to isolate the n-eff-map refusal.
function RunRefuse($name, $gates, $mapFlag) {
    Remove-Item Env:\STREHL_DUMP_NEFF -ErrorAction SilentlyContinue
    $a = @("stack", $dir, "--limit", "20")
    foreach ($g in $gates) { $a += @("--gate", $g) }
    $a += @("--n-eff-map", $mapFlag)
    $o = & $exe @a 2>&1
    $code = $LASTEXITCODE
    $o | Out-String | Set-Content -Encoding utf8 "$out\$name.log"
    $wrote = Test-Path $mapFlag
    Write-Output ("{0,-10} EXIT={1} MAP_WRITTEN={2}" -f $name, $code, $wrote)
    $o | Out-String | Select-String "Error" | Select-Object -Last 2 |
        ForEach-Object { "    | " + $_.Line.Trim() }
}

Write-Output "=== runs ==="
Run "A_nomap"  @("4") $null            $null
Run "B_flag"   @("4") "$out\B.tiff"    $null
Run "C_env"    @("4") $null            "$out\C.tiff"
Run "D_both"   @("4") "$out\D_flag.tiff" "$out\D_env.tiff"
Run "E_gate2"  @("2") "$out\E.tiff"    $null
Write-Output ""
RunRefuse "F_2gates" @("4", "2") "$out\F.tiff"

Write-Output ""
Write-Output "=== E1: merged bytes unchanged by the export ==="
$ha = Sha "$out\A_nomap.tiff"; $hb = Sha "$out\B_flag.tiff"; $hc = Sha "$out\C_env.tiff"
Write-Output "  no-map=$ha  flag=$hb  env=$hc"
Write-Output ("  E1: " + $(if ($ha -eq $hb -and $hb -eq $hc) { "PASS" } else { "FAIL" }))

Write-Output ""
Write-Output "=== E1b: PLANT -- the hash must be able to move ==="
$he = Sha "$out\E_gate2.tiff"
Write-Output "  gate4=$ha  gate2=$he"
Write-Output ("  E1b: " + $(if ($ha -ne $he) { "PASS" } else { "FAIL -- E1 is vacuous" }))

Write-Output ""
Write-Output "=== E2: both mechanisms agree; flag wins ==="
$mb = Sha "$out\B.tiff"; $mc = Sha "$out\C.tiff"
Write-Output "  flagmap=$mb  envmap=$mc"
$dflag = Test-Path "$out\D_flag.tiff"; $denv = Test-Path "$out\D_env.tiff"
Write-Output "  both set -> flag written=$dflag, env written=$denv (env must be False)"
Write-Output ("  E2: " + $(if ($mb -eq $mc -and $mb -ne "NOFILE" -and $dflag -and -not $denv) { "PASS" } else { "FAIL" }))

Write-Output ""
Write-Output "=== E3 / E3b: connected to the estimator ==="
python C:\dev\strehl-out\M97\neffstat.py "$out\B.tiff" "$out\B_flag.log"
Write-Output ""
python C:\dev\strehl-out\M97\neffstat.py "$out\E.tiff" "$out\E_gate2.log"

Write-Output ""
Write-Output "=== provenance (rule 47) ==="
Write-Output "dir=$dir limit=20 gate=4 (explicit; arm E gate=2, arm F gates 4+2)"
Write-Output "env: STREHL_ALIGN=0 STREHL_DUMP_NEFF=<per arm> STREHL_CACHE_DIR=$out\cache"
Write-Output ("threads=" + $env:NUMBER_OF_PROCESSORS)
Push-Location C:\dev\blog\death-of-software\projects\strehl
Write-Output ("commit=" + (git rev-parse --short HEAD) + " + uncommitted --n-eff-map work")
Pop-Location
