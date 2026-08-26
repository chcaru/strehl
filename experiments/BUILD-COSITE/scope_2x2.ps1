# BUILD-COSITE scope control.
#
# REQUIRES A SCRATCH PATCH THAT IS NOT AT HEAD. The STREHL_COSITE_OFF switch
# was applied to `develop_binned` in crates/strehl-cli/src/image_out.rs for the
# duration of this measurement and reverted in the same session. To re-run,
# re-apply it: wrap the two `resample_shift` calls so that
# `std::env::var_os("STREHL_COSITE_OFF").is_some()` passes the planes through
# untouched instead. Results are recorded in docs/research/BUILD-COSITE.md
# section 8.2.
#
# ORCH instructed: "measure it on the viewable sRGB render ... Measuring on the
# linear path will show you nothing." This 2x2 settles that by hash.
#
# ONE binary. One switch, STREHL_COSITE_OFF, that disables ONLY the co-site
# inside develop_binned. The alignment gather is untouched, so the switch is a
# pure probe for "did this render call write_binned at all".
#
#   viewable arm  --srgb --auto-exposure   (the shipped gallery command)
#   linear arm    --linear-srgb            (what BUILD-COSITE measured on)
#
# Predicted if the co-site is NOT on the viewable path:
#   viewable ON == viewable OFF   (bit-identical)
#   linear   ON != linear   OFF   (this is the potency half -- without it,
#                                  "identical" could just mean the env var
#                                  never reached the binary)

$ErrorActionPreference = "Continue"   # strehl logs to stderr; Stop would abort on the banner
$exe = "C:\dev\strehl-out\BUILD-COSITE\strehl-scope.exe"
$out = "C:\dev\strehl-out\BUILD-COSITE\scope"
$subject = "D:\personal\macro\coffee-bean"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$arms = @(
    @{ name = "viewable"; flags = @("--merge", "pyramid", "--pyramid-gate", "4.5", "--srgb", "--auto-exposure") },
    @{ name = "linear";   flags = @("--merge", "pyramid", "--pyramid-gate", "4.5", "--linear-srgb") }
)

foreach ($arm in $arms) {
    foreach ($state in @("on", "off")) {
        $tif = Join-Path $out "$($arm.name)-cosite-$state.tif"
        $log = [System.IO.Path]::ChangeExtension($tif, ".log")
        if ($state -eq "off") { $env:STREHL_COSITE_OFF = "1" }
        else { Remove-Item Env:\STREHL_COSITE_OFF -ErrorAction SilentlyContinue }
        Write-Host "-> $($arm.name) / co-site $state"
        & $exe stack $subject @($arm.flags) -o $tif *>&1 | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { throw "render failed rc=$LASTEXITCODE, see $log" }
    }
}
Remove-Item Env:\STREHL_COSITE_OFF -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== SHA-256 ==="
foreach ($arm in @("viewable", "linear")) {
    $a = (Get-FileHash (Join-Path $out "$arm-cosite-on.tif")  -Algorithm SHA256).Hash
    $b = (Get-FileHash (Join-Path $out "$arm-cosite-off.tif") -Algorithm SHA256).Hash
    $same = if ($a -eq $b) { "IDENTICAL -> write_binned NOT reached" }
            else { "DIFFER    -> write_binned reached, co-site ran" }
    Write-Host ("{0,-9} on  {1}" -f $arm, $a.Substring(0, 32))
    Write-Host ("{0,-9} off {1}" -f "", $b.Substring(0, 32))
    Write-Host ("{0,-9} {1}" -f "", $same)
}
foreach ($arm in @("viewable", "linear")) {
    $f = Join-Path $out "$arm-cosite-on.tif"
    Write-Host ("{0,-9} banner: {1}" -f $arm, ((Select-String -Path ([System.IO.Path]::ChangeExtension($f, ".log")) -Pattern "demosaic|binned from" | Select-Object -First 1).Line))
}
