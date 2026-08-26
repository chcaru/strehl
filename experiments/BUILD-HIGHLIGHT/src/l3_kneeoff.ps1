# L3 -- the ladder re-run under ORCH'S OWN CONDITIONS: highlight roll-off OFF.
#
# WHY. Two reasons, and both are disqualifying for the first pass:
#
#  1. The crops ORCH is looking at were produced by pin-cur C46BDF06, which was
#     built at 11:23 and contains NEITHER the roll-off banner string nor the
#     env var name -- verified by scanning the binary. It has no roll-off at
#     all. Diagnosing what ORCH saw means reproducing what ORCH ran.
#  2. The roll-off drives rim pixels toward neutral, which is precisely the
#     population this measurement needs. Arm L6 showed it: an aggressive knee
#     took H from 0.1875 to 0.1278. Leaving it on would let my own fix mask the
#     demosaic question I am supposed to be answering.
#
# Same binary as the first ladder, same subject, same crop. The ONLY difference
# from L1/L2/L3/L5 is STREHL_HIGHLIGHT_KNEE=off, and the script asserts the
# renders actually differ from their knee-on counterparts -- an arm that
# produced a byte-identical file was not a different arm.

$ErrorActionPreference = 'Stop'
$EXE = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-highlight\release\strehl.exe"
$OUT = "C:\dev\strehl-out\BUILD-HIGHLIGHT\ladder"
$SUBJ = "D:\personal\macro\coffee-bubbles"
$ONE = "$OUT\one-frame"

Write-Output "binary sha256 : $((Get-FileHash $EXE -Algorithm SHA256).Hash)"
$env:STREHL_HIGHLIGHT_KNEE = 'off'
Write-Output "STREHL_HIGHLIGHT_KNEE = off  (matching pin-cur C46BDF06, which has no roll-off)"
Write-Output ""

$arms = @(
  @{ n = 'K1-single-demo'; d = $ONE;  a = @('--linear-srgb', '--demosaic'); twin = 'L1-single-demo' },
  @{ n = 'K2-stack-binned'; d = $SUBJ; a = @('--linear-srgb'); twin = 'L2-stack-binned' },
  @{ n = 'K3-stack-demo';  d = $SUBJ; a = @('--linear-srgb', '--demosaic'); twin = 'L3-stack-demo' },
  @{ n = 'K5-stack-caoff'; d = $SUBJ; a = @('--linear-srgb', '--demosaic', '--fix-ca', 'off'); twin = 'L5-stack-caoff' },
  @{ n = 'K7-srgb-look';   d = $SUBJ; a = @('--srgb'); twin = 'S3-stack-srgb' }
)

foreach ($arm in $arms) {
    $tif = "$OUT\$($arm.n).tif"
    $log = "$OUT\$($arm.n).log"
    $argv = @('stack', $arm.d, '--merge', 'pyramid') + $arm.a + @('-o', $tif)
    "=== $($arm.n) ==="
    & $EXE @argv 2>&1 | Tee-Object -FilePath $log | Out-Null

    $banner = (Select-String -Path $log -Pattern 'merge backend' | Select-Object -First 1).Line
    $ca = (Select-String -Path $log -Pattern 'lateral CA' | Select-Object -First 1).Line
    "BANNER: $($banner -replace '\s+', ' ')"
    "CA    : $($ca -replace '\s+', ' ')"

    # -- the arm must actually BE a different arm ------------------------
    $twin = "$OUT\$($arm.twin).tif"
    if (Test-Path $twin) {
        $a = (Get-FileHash $tif -Algorithm SHA256).Hash
        $b = (Get-FileHash $twin -Algorithm SHA256).Hash
        if ($a -eq $b) {
            Write-Output "!! knee=off produced a file BYTE-IDENTICAL to $($arm.twin)."
            Write-Output "!! Either the roll-off never engaged on this subject, or the env var was ignored."
            Write-Output "!! Recording it rather than assuming, but this arm tests nothing new."
        }
        else {
            "differs from $($arm.twin): YES  ($($a.Substring(0,8)) vs $($b.Substring(0,8)))"
        }
    }
    ""
}
Remove-Item Env:\STREHL_HIGHLIGHT_KNEE -ErrorAction SilentlyContinue
Write-Output "finished : $(Get-Date -Format o)"
