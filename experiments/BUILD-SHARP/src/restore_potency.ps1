$ErrorActionPreference = "Stop"
$pin = "C:\dev\strehl-out\BUILD-SHARP\s24"
$exe = "$pin\strehl.exe"
$subject = "112MSDCF"
$env:STREHL_CACHE_DIR = "$pin\cache-$subject"

"BINARY SHA256 = " + (Get-FileHash $exe -Algorithm SHA256).Hash
$off = (Get-FileHash "$pin\$subject--off.tif" -Algorithm MD5).Hash
"OFF (flag unset) MD5 = $off"
""
"2x2: does the CAP move it, or only SIGMA?"
""

# (cap, sigma, label)
$arms = @(
  @("4.0",     "",        "A  cap 4.0    calibrated sigma  (the shipped-ish arm)"),
  @("1000000", "",        "B  cap 1e6    calibrated sigma  (ORCH's proposed potency arm)"),
  @("1000000", "0.000001","C  cap 1e6    sigma x 1e-6      (cap AND sigma absurd)"),
  @("4.0",     "0.000001","D  cap 4.0    sigma x 1e-6      (sigma alone)")
)

foreach ($a in $arms) {
    $env:STREHL_RESTORE = $a[0]
    if ($a[1] -eq "") {
        Remove-Item Env:\STREHL_RESTORE_SIGMA -ErrorAction SilentlyContinue
    } else {
        $env:STREHL_RESTORE_SIGMA = $a[1]
    }
    $out = "$pin\potency-$($arms.IndexOf($a)).tif"
    $log = & $exe stack "D:\personal\macro\$subject" --out $out `
        --resampler catmull-rom --demosaic --pyramid-gate 4.5 2>&1
    $bk  = ($log | Select-String -Pattern "^merge backend").Line
    $g1  = ($log | Select-String -Pattern "^restore G1").Line
    $md5 = (Get-FileHash $out -Algorithm MD5).Hash
    $same = if ($md5 -eq $off) { "IDENTICAL to OFF" } else { "CHANGED" }
    "$($a[2])"
    "    $bk"
    "    -> $same   md5 $($md5.Substring(0,8))"
    "    $g1"
    ""
}
