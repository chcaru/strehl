# M1 -- ORCH's discriminator: MY radial statistic on BUILD-SHARP's subject.
#
# THE QUESTION. BUILD-SHARP measured `flower-bud-alone-cpl` and concluded the
# fringe is NOT lateral CA: R-B displacement bounded at 0.05 px against the
# 0.5-2 px a visible fringe needs, with a G-vs-G null of exactly 0.0000. I
# measured `coffee-bubbles` and concluded C is the survivor: signed (R-G)/Y
# growing 2.09-2.99x centre to corner on every arm under every selector.
#
# ORCH's instruction is precise and I am following it exactly: run MY statistic
# on THEIR subject. Do NOT re-run their measurement. If (R-G)/Y reads flat on
# flower-bud, the two fringes are different defects and both reports stand. If
# it reads radial, the two statistics disagree on the same data and one of them
# is wrong -- which matters more than the fringe.
#
# WHY THREE CHANNEL-PAIR AXES AND NOT JUST MINE. BUILD-SHARP's axis is R-B.
# Mine is R-G. Those are not the same measurement, because in this codebase
# GREEN IS THE REFERENCE CHANNEL: optics.rs:449 gives green no coefficient by
# construction and freezes both green gathers bitwise. Red and blue are each
# corrected TOWARD green, with OPPOSITE-SIGNED coefficients (eps_r = -704.5 ppm,
# eps_b = +174.4 ppm). So a residual carried against green can be large while
# the R-B difference stays small. Projecting the same mask onto all three axes
# costs nothing extra and is the only way to tell "no defect" from "an axis that
# cannot see this defect". That is ORCH's possibility 3, made measurable.
#
# ARMS. Same binary as the coffee-bubbles ladder (F9BD5191), so this is a
# like-for-like across subjects and not a cross-build comparison -- which this
# project has established are VOID outside the green plane.
#
# NEGATIVE CONTROL. --fix-ca off is absurd for its type (it disables the stage
# entirely, it is not a value near a default) and the script ASSERTS THE
# PROGRAM'S OWN BANNER CHANGED between the arms. An unchanged banner means the
# arm was never tested and the comparison is meaningless; this is the trap that
# cost this project a headline table, so it is checked rather than assumed.

$ErrorActionPreference = 'Stop'
$EXE  = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-highlight\release\strehl.exe"
$OUT  = "C:\dev\strehl-out\BUILD-HIGHLIGHT\flowerbud"
$SUBJ = "D:\personal\macro\flower-bud-alone-cpl"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

$sha = (Get-FileHash $EXE -Algorithm SHA256).Hash
Write-Output "binary sha256 : $sha"
Write-Output "subject       : $SUBJ"
Write-Output "started       : $(Get-Date -Format o)"
Write-Output ""

# knee OFF on both CA arms: BUILD-SHARP's reading and ORCH's crop both predate
# the roll-off, so this reproduces THEIR conditions, not mine.
$arms = @(
  @{ n = 'M1-caon-kneeoff';  a = @('--linear-srgb', '--demosaic');                    k = 'off' },
  @{ n = 'M2-caoff-kneeoff'; a = @('--linear-srgb', '--demosaic', '--fix-ca', 'off'); k = 'off' },
  @{ n = 'M3-caon-kneeon';   a = @('--linear-srgb', '--demosaic');                    k = $null }
)

$banners = @{}
foreach ($arm in $arms) {
    $tif = "$OUT\$($arm.n).tif"
    $log = "$OUT\$($arm.n).log"
    if ($arm.k) { $env:STREHL_HIGHLIGHT_KNEE = $arm.k }
    else { Remove-Item Env:\STREHL_HIGHLIGHT_KNEE -ErrorAction SilentlyContinue }

    $argv = @('stack', $SUBJ, '--merge', 'pyramid') + $arm.a + @('-o', $tif)
    "=== $($arm.n) ==="
    "argv : strehl $($argv -join ' ')"
    "knee : $(if ($arm.k) { $arm.k } else { '(default 0.60, on)' })"

    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $EXE @argv 2>&1 | Tee-Object -FilePath $log | Out-Null
    $sw.Stop()

    # THE BANNER, NOT THE ARGV. An argv records what I asked for; only the run's
    # own banner records what the program did.
    $ca = (Select-String -Path $log -Pattern 'lateral CA').Line -join ' '
    $mb = (Select-String -Path $log -Pattern 'merge backend').Line -join ' '
    $banners[$arm.n] = $ca
    "  merge backend : $($mb -replace '^\s*merge backend\s*:\s*','')"
    "  lateral CA    : $($ca -replace '^\s*lateral CA\s*:\s*','')"
    "  elapsed       : $([math]::Round($sw.Elapsed.TotalSeconds,1)) s"
    ""
}

# ASSERT THE CONTROL BIT. If the CA banner is identical between the on and off
# arms the flag did nothing and every number downstream is void.
if ($banners['M1-caon-kneeoff'] -eq $banners['M2-caoff-kneeoff']) {
    Write-Output "FAIL: --fix-ca off did NOT change the banner. The control arm was never tested."
    Write-Output "  M1: $($banners['M1-caon-kneeoff'])"
    Write-Output "  M2: $($banners['M2-caoff-kneeoff'])"
    exit 1
}
Write-Output "control OK: the CA banner differs between arms, so the flag bit."
Write-Output "  CA on  : $($banners['M1-caon-kneeoff'])"
Write-Output "  CA off : $($banners['M2-caoff-kneeoff'])"
Write-Output "finished : $(Get-Date -Format o)"
