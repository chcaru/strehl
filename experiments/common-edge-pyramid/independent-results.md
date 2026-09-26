# Independent fixed-recipe closure

**MEASURED: reject; no photograph nominated.** The actual common-canonical
guide fails preservation and both predeclared positives. This is a quality
failure after successful arithmetic commissioning, not a numerical refusal.
No guide, bandwidth, threshold or source subset is revised from these results.

Evidence: `controls-1/output/screen.json` SHA256
`edbbd0e604739bd1053d8c926eb21d6929c165aabff18583065dfc0bd55f6a09`
and `operator.json` SHA256
`7c6f0c34c900b81ec94fddfb106521a0cb888e8767393673a7faf982171c9069`.
The saved invocation ran:

```powershell
& 'C:\dev\blog\death-of-software\projects\strehl\experiments\common-edge-pyramid\build-2\cli-tests.exe' 'merge_cmd::common_edge_pyramid::independent_controls::' --ignored --nocapture --test-threads=1
```

The exact environment is retained in `controls-1/invocation.json`. Both tests
passed mechanically in 3.625 s, exit 0, terminal active-process count zero;
completion records sources and inputs unchanged. Build-1's missing trait
import failure remains recorded; only that import changed before build-2.
This review read saved outputs; it did not rerun the experiment.

## Re-chosen comparisons

All errors below are final normalized camera-RGB RMSE in the original fixed
window. Uniform is the existing Gaussian unit-weight consumer, not a new-basis
arm. It is a useful noise reference but much poorer than canonical on these
structured cases; beating uniform alone would hide the actual regression.

| Fixed window | Canonical | Uniform | Actual common guide | Truth guide, diagnostic only |
|---|---:|---:|---:|---:|
| Curved boundary | .01136408 | .04552057 | .02488815 | .02185566 |
| Near-fine/far-coarse | .00518630 | .01720556 | .01426402 | .01438063 |
| Genuine glint core | .00372711 | .04439548 | .00821661 | .00812461 |
| Weak colour | .00196893 | .00373313 | .00202595 | .00203542 |

The actual guide increases the two positive-window errors by 2.19x and 2.75x
versus canonical. This is not merely chromatic redistribution: Curved green
RMSE rises .01141380 to .02474379, and Thin green .00523118 to .01288816.
Chroma also worsens there (.00486400 to .00674953 and .00321569 to .00392407).
Weak colour remains inside the fixed protection bars, with a small error
increase rather than a demonstrated benefit.

Thin's genuine green near-component recovery drops from 1.00855 to .54029;
its far component changes only .93711 to .92274. Thus the aggregate loss
includes destroyed near detail, not a uniformly softer but equivalent image.
The unclipped glint's green core recovery .98102 to .93518 still passes the
90% retention bar, so the result does **not** support saying that the glint
was erased. Its core RGB error nevertheless more than doubles. Adjacent
green near-detail recovery falls 1.02153 to .70680; the clipped scene shows
essentially the same adjacent loss. No clipped-core recovery was tested.

All three flat cases fail the comparison to uniform. Their actual-guide RGB
errors are .00114108, .00099330 and .00262622, versus uniform .00100414,
.00071794 and .00229677. However, these are almost the canonical values
(.00114149, .00099527, .00263033). The basis therefore fails to repair the
inherited flat-selection cost; the data do not show a large new flat-noise
penalty caused by this guide. Green and chroma comparisons, not just RGB,
are retained in the receipt and participate in the failure.

The constant guide reproduces canonical within the preset numerical allowance.
The displaced guide is less harmful than the actual guide on Curved and Thin
(RGB .01313681 and .00728784), yet still fails the original guards. Temporal
mean guidance also fails (.02719211 and .01253365). Most importantly, even
the supplied truth guide fails both positives and the Thin/adjacent-detail
protections. This makes a contaminated canonical guide an insufficient
explanation by itself. It does not isolate which part of the changed spatial
basis, held old-basis decisions or new terminal mean causes the damage, and
does not refute every guide-dependent pyramid.

## Arithmetic and scope

Independent literal support checks, wrong-border/parity/guide destroyers,
three/seven-band even/odd roundtrips, terminal mean and uniform averaging all
pass. Maximum tested direct-mean error is .006836 DN, below .02 DN; literal
f64 support error is at most .002914 DN. A false step guide reconstructs a
constant input exactly in these roundtrip cases. That rules out simple
literal copying of guide intensity on this constant control, not structured
guide-induced damage in a merge. The nuisance arms exhibit the predeclared
error/retention form of harmful guide dependence. No separate visual claim
of a newly invented edge is made from aggregate metrics alone.

Ordinary one-pass canonical CFA/RGB equals the instrumented canonical output
bit-for-bit on Flat and Thin. All-arm diagnostic-emission identity also
passes; its mandatory internal integrity checks were not disabled. All five
erasure/noise destroyers reject, truth passes all eight scoring paths, and
all protected witnesses and both positive-error witnesses are live. The
Curved projection can exceed one while its far projection becomes negative;
the absolute-error guards catch that blind spot in retention-only scoring.

The decisive result is the unchanged conjunction:
`candidate_nominated=false`, `photographic_replay_admitted=false`.
Seven-band numerical support is not seven-band occlusion validation, these
known generated cases are not fresh photographs, and the shared injected
noise constants do not validate camera calibration. Close this fixed recipe.
