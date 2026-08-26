$ErrorActionPreference = "Stop"
$pin = "C:\dev\strehl-out\BUILD-SHARP\s24"
$exe = "$pin\strehl.exe"
$subject = "112MSDCF"
$env:STREHL_CACHE_DIR = "$pin\cache-$subject"

"BINARY SHA256 = " + (Get-FileHash $exe -Algorithm SHA256).Hash
$off = (Get-FileHash "$pin\$subject--off.tif" -Algorithm MD5).Hash
"baseline (STREHL_RESTORE unset) MD5 = $off"
""
"The threshold is `cap > 1.0` at restore.rs:1240. Straddle it."
"Every arm below holds STREHL_RESTORE_SIGMA=0.000001 -- maximum possible"
"aggression -- so a byte-identity CANNOT be blamed on a weak setting."
""

$env:STREHL_RESTORE_SIGMA = "0.000001"
$i = 0
foreach ($cap in @("1", "1.0000001", "4.0")) {
    $env:STREHL_RESTORE = $cap
    $out = "$pin\thr-$i.tif"; $i++
    $log = & $exe stack "D:\personal\macro\$subject" --out $out `
        --resampler catmull-rom --demosaic --pyramid-gate 4.5 2>&1
    $bk    = ($log | Select-String -Pattern "^merge backend").Line
    $lines = @($log | Select-String -Pattern "^restore ")
    $md5   = (Get-FileHash $out -Algorithm MD5).Hash
    $same  = if ($md5 -eq $off) { "IDENTICAL to baseline" } else { "CHANGED" }
    "STREHL_RESTORE=$cap"
    "    $bk"
    "    -> $same   md5 $($md5.Substring(0,8))"
    "    restore banner lines emitted : $($lines.Count)"
    if ($lines.Count -gt 0) { "    $($lines[1].Line)" }
    ""
}
