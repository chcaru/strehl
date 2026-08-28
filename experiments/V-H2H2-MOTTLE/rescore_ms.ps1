# V-H2H2: re-score the saved p_eff ladder on ORCH's CORRECTED instrument.
#
# No renders. The five masters from twoside.ps1 are reused verbatim, so this is
# a pure re-measurement of the same pixels against a different criterion --
# which is the only honest way to answer "does my earlier verdict survive the
# corrected bar?" without letting a re-render smuggle in a second variable.
#
# WHICH BAND IS THE ACUITY CRITERION -- the thing that decides every verdict:
#
# ORCH's message instructed "EDGE ratio at bands 2 and 3 >= 0.98". Those indices
# are STALE BY ONE COMMIT. contrast_ms.py was committed 19787752 (17:13) with
# SIGMAS = [1,2,4,8,16], then amended 0ff348ec (18:03) "place contrast_ms band
# edges on V-LINEAR's qualification boundaries" to SIGMAS =
# [0.6366, 0.9362, 2, 4, 8, 16]. The band indices moved with it. The current
# file's own text says acuity lives at BAND 1 and that "bands 2+ are 0.01-0.08
# cyc/px, far too coarse to be an acuity test".
#
# So my band 2/3 numbers are NOT comparable to the band 2/3 numbers in ORCH's
# message, and I do not compare them. I read the criterion off the committed
# instrument, which is the artefact ORCH told me to score with.
#
# The committed file encodes V-LINEAR's PER-TILE qualification:
#     0.17-0.20  ratio 4.874  PASS -- carries signal
#     0.20-0.25  ratio 2.419  PASS -- carries signal
#     0.25-0.48                NOISE
# i.e. band 1 (0.17-0.25) PASSES the >= 2 qualification test ORCH set as the
# gate for using a band as a sharpness criterion. That is why band 1 is the bar.

$ErrorActionPreference = "Stop"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$d    = Join-Path $env:TEMP "vh2h2-2side"
$ms   = Join-Path $root "experiments\ORCH-drift-check\contrast_ms.py"

$masters = @("A", "K", "S1", "S100", "S1000")
$missing = $masters | Where-Object { -not (Test-Path (Join-Path $d "$_.tif")) }
if ($missing) {
    Write-Host "MISSING masters: $($missing -join ', ')"
    Write-Host "Re-run twoside.ps1 first. Refusing to score a partial ladder --"
    Write-Host "an arm that silently vanishes reads as an arm that did not lose."
    exit 1
}

Write-Host "instrument : $ms"
Write-Host "             $(git -C $root log --format='%h %s' -1 -- experiments/ORCH-drift-check/contrast_ms.py)"
Write-Host "masters    : $d  (from twoside.ps1, binary 63298741 at b7bbaaa2)"
Write-Host ""

foreach ($n in @("K", "S1", "S100", "S1000")) {
    Write-Host ("=== {0} vs A {1}" -f $n, ("=" * 44))
    python $ms (Join-Path $d "A.tif") (Join-Path $d "$n.tif")
    Write-Host ""
}
