# L1 -- the ORCH ladder: where does the coloured rim on small bright features enter?
#
# ORCH observed green-yellow rings on `coffee-bubbles` and rainbow speckle on
# `foam`, both bright-small-on-dark, and asked for a ladder that localises the
# defect to one pipeline stage BEFORE anyone proposes a fix.
#
# The arms, and what each pair isolates:
#   L1 single frame, demosaiced    \_ L1 vs L3 isolates THE MERGE
#   L3 stack,        demosaiced    /
#   L2 stack,        BINNED        -- L2 vs L3 isolates THE DEMOSAIC
#   L5 stack, demosaiced, CA off   -- L3 vs L5 isolates LATERAL CA
#   L4 stack, demosaiced, gate 4.5 -- L3 vs L4 isolates THE NOISE GATE
#   L6 NEGATIVE CONTROL on my own instrument (see below)
#
# ONE BINARY for every arm, hashed here and quoted in the report. The tree is
# currently dirty in `crates/strehl-core/src/pyramid.rs`, which belongs to
# BUILD-BLEND, so this deliberately does NOT rebuild: compiling another lane's
# in-flight merge changes into a merge experiment would be untraceable.
#
# MEASUREMENT ARMS ARE LINEAR. ORCH struck a published comparison tonight that
# was measured on --srgb output; the transfer curve is a strong non-linearity
# and moves every ratio. The sRGB arms exist ONLY to be looked at.
#
# NEGATIVE CONTROL, per ORCH's second caution: `1` was a useless probe value
# because it is the multiplicative identity. The control value here is absurd
# FOR ITS TYPE (a knee at 0.02 when the default is 0.60) and the script asserts
# THE PROGRAM'S OWN BANNER CHANGED. An unchanged banner means the arm was never
# tested, and the script says so loudly rather than producing a quiet null.

$ErrorActionPreference = 'Stop'
$EXE = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-highlight\release\strehl.exe"
$OUT = "C:\dev\strehl-out\BUILD-HIGHLIGHT\ladder"
$SUBJ = "D:\personal\macro\coffee-bubbles"
$ONE = "$OUT\one-frame"

$sha = (Get-FileHash $EXE -Algorithm SHA256).Hash
Write-Output "binary sha256 : $sha"
Write-Output "started       : $(Get-Date -Format o)"
Write-Output ""

# name, source dir, extra args, knee env
$arms = @(
  @{ n = 'L1-single-demo';  d = $ONE;  a = @('--linear-srgb', '--demosaic'); k = $null },
  @{ n = 'L2-stack-binned'; d = $SUBJ; a = @('--linear-srgb'); k = $null },
  @{ n = 'L3-stack-demo';   d = $SUBJ; a = @('--linear-srgb', '--demosaic'); k = $null },
  @{ n = 'L4-stack-gate45'; d = $SUBJ; a = @('--linear-srgb', '--demosaic', '--pyramid-gate', '4.5'); k = $null },
  @{ n = 'L5-stack-caoff';  d = $SUBJ; a = @('--linear-srgb', '--demosaic', '--fix-ca', 'off'); k = $null },
  @{ n = 'L6-NEGCTL-knee';  d = $SUBJ; a = @('--linear-srgb', '--demosaic'); k = '0.02' },
  @{ n = 'S1-single-srgb';  d = $ONE;  a = @('--srgb'); k = $null },
  @{ n = 'S2-stack-srgbbin'; d = $SUBJ; a = @('--srgb', '--binned'); k = $null },
  @{ n = 'S3-stack-srgb';   d = $SUBJ; a = @('--srgb'); k = $null }
)

foreach ($arm in $arms) {
    $tif = "$OUT\$($arm.n).tif"
    $log = "$OUT\$($arm.n).log"
    if ($arm.k) { $env:STREHL_HIGHLIGHT_KNEE = $arm.k } else { Remove-Item Env:\STREHL_HIGHLIGHT_KNEE -ErrorAction SilentlyContinue }

    $argv = @('stack', $arm.d, '--merge', 'pyramid') + $arm.a + @('-o', $tif)
    "=== $($arm.n) ==="
    "argv : $EXE $($argv -join ' ')"
    "knee : $(if ($arm.k) { $arm.k } else { '(default, on)' })"

    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $EXE @argv 2>&1 | Tee-Object -FilePath $log | Out-Null
    $sw.Stop()

    $banner = (Select-String -Path $log -Pattern 'merge backend' | Select-Object -First 1).Line
    $ca = (Select-String -Path $log -Pattern 'lateral CA' | Select-Object -First 1).Line
    $wrote = (Select-String -Path $log -Pattern '^wrote' | Select-Object -First 1).Line
    $knee = (Select-String -Path $log -Pattern 'chroma roll-off knee moved' | Select-Object -First 1)

    "BANNER: $($banner  -replace '\s+', ' ')"
    "CA    : $($ca -replace '\s+', ' ')"
    "WROTE : $(($wrote -replace '\s+', ' '))"
    "KNEE-BANNER: $(if ($knee) { $knee.Line.Trim() } else { '(none)' })"
    "elapsed: $([int]$sw.Elapsed.TotalSeconds)s"

    # -- the control must be SHOWN to have taken effect -------------------
    if ($arm.k -and -not $knee) {
        Write-Output "!! CONTROL FAILED: knee set to $($arm.k) but the program never said so."
        Write-Output "!! The arm was not tested. Refusing to let this pass as a null result."
        exit 3
    }
    if (-not $arm.k -and $knee) {
        Write-Output "!! CONTAMINATION: a non-control arm reported a moved knee."
        exit 4
    }
    ""
}

Remove-Item Env:\STREHL_HIGHLIGHT_KNEE -ErrorAction SilentlyContinue
Write-Output "finished : $(Get-Date -Format o)"
