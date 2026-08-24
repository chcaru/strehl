# R7 -- does the CA switch reach a rendered pixel?
#
# BARS, REGISTERED BEFORE THE RUN:
#   N1  CA-off rendered twice must be BYTE-IDENTICAL (same SHA256). This is the
#       determinism/no-hidden-state control. If it fails, nothing else here
#       means anything.
#   N2  CA-on must DIFFER from CA-off. If these hash the same, the switch is a
#       silent no-op -- the exact failure fact 1449 describes, and the trap that
#       would make "the correction doesn't help" the wrong conclusion.
#   N3  A typo'd profile must FAIL LOUDLY. Assert the EXACT exit code, never a
#       -ne 0 predicate (rule 47: the corrupted value is 0 under PS7 and -1
#       under 5.1, so -ne 0 is unsafe in both directions).
#   N4  The default path is unchanged: CA unset, CA=0 and CA=off must all
#       produce the SAME hash as each other.
#
# One sidecar is solved ONCE and reused by every arm, so `reference` and the
# solve are held fixed across arms by construction (fact 1446: StackIdentity
# covers neither reference nor resampler).

$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-out\M107-chroma\cargo-target-m107\release\strehl.exe"
$out  = "C:\dev\strehl-out\M107-chroma\r7"
$dir  = "D:\personal\macro\bee-3-cpl"
$PROFILE_KEY = "a7c2-fe100gm-2xtc-x4cpl"

New-Item -ItemType Directory -Force -Path $out | Out-Null
$side = Join-Path $out "bee-3-cpl-warpmap.txt"
$log  = Join-Path $out "r7.log"
"R7 -- CA wiring A/B, started $(Get-Date -Format o)" | Set-Content $log
"binary: $exe" | Add-Content $log

$n = (Get-ChildItem $dir -Filter *.ARW).Count
$ref = [int]([math]::Floor($n / 2))
"frames=$n reference=$ref" | Add-Content $log
Write-Host "bee-3-cpl: $n frames, reference $ref"

if (-not (Test-Path $side)) {
    Write-Host "solving sidecar (once, shared by all arms)..."
    $alignOut = & $exe align $dir --out $side --reference $ref 2>&1
    $alignCode = $LASTEXITCODE
    $alignOut | Add-Content $log
    "align EXIT=$alignCode" | Add-Content $log
    if ($alignCode -ne 0) { Write-Host "align EXIT=$alignCode -- ABORT"; exit 1 }
}
$env:STREHL_WARPMAP = $side

function Render($label, $caValue) {
    $tif = Join-Path $out "$label.tif"
    if ($null -eq $caValue) {
        Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
    } else {
        $env:STREHL_FIX_CA = $caValue
    }
    $t0 = Get-Date
    $o = & $exe stack $dir --srgb --auto-exposure -o $tif 2>&1
    $code = $LASTEXITCODE
    $sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $o | Add-Content $log
    $shown = if ($null -eq $caValue) { "<unset>" } else { $caValue }
    "--- arm $label  STREHL_FIX_CA=$shown  EXIT=$code  ${sec}s" | Add-Content $log
    $h = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash } else { "NO-FILE" }
    "    sha256=$h" | Add-Content $log
    Write-Host ("  {0,-10} EXIT={1}  {2,6}s  {3}" -f $label, $code, $sec, $h.Substring(0, 16))
    return @{ code = $code; hash = $h }
}

Write-Host "rendering arms..."
$off1 = Render "off1" $null
$on   = Render "on"   $PROFILE_KEY
$off2 = Render "off2" $null
$zero = Render "zero" "0"
$offw = Render "offword" "off"

Write-Host ""
Write-Host "=== typo arm (must fail loudly) ==="
$env:STREHL_FIX_CA = "a7c2-fe100gm-2xtc-x4cpl-TYPO"
$badTif = Join-Path $out "typo.tif"
$bo = & $exe stack $dir --srgb --auto-exposure -o $badTif 2>&1
$badCode = $LASTEXITCODE
$bo | Add-Content $log
"--- typo arm EXIT=$badCode" | Add-Content $log
Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
Write-Host "  typo arm EXIT=$badCode"
($bo | Out-String) -split "`r?`n" | Where-Object { $_ -match "profile" } | ForEach-Object { Write-Host "    $_" }

Write-Host ""
Write-Host ("=" * 60)
$n1 = ($off1.hash -eq $off2.hash)
Write-Host "N1  off1 == off2 (byte-identical null) : $(if($n1){'PASS'}else{'FAIL'})"
Write-Host "      off1 = $($off1.hash)"
Write-Host "      off2 = $($off2.hash)"
$n2 = ($on.hash -ne $off1.hash)
Write-Host "N2  on  != off (switch reaches pixels) : $(if($n2){'PASS'}else{'FAIL -- SILENT NO-OP'})"
Write-Host "      on   = $($on.hash)"
$n3 = ($badCode -eq 1)
Write-Host "N3  typo arm EXIT=$badCode (want exactly 1) : $(if($n3){'PASS'}else{'FAIL'})"
$n4 = ($off1.hash -eq $zero.hash -and $off1.hash -eq $offw.hash)
Write-Host "N4  unset == 0 == off                  : $(if($n4){'PASS'}else{'FAIL'})"
Write-Host ("=" * 60)
$all = $n1 -and $n2 -and $n3 -and $n4
Write-Host "VERDICT: $(if($all){'ALL BARS PASS'}else{'BARS FAILED'})"
"VERDICT: $(if($all){'ALL BARS PASS'}else{'BARS FAILED'})" | Add-Content $log
