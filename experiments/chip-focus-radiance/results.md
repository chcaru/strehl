# Complete chip radiance observation: cleanup with unacceptable detail loss

MEASURED / VISUALLY REVIEWED, 2026-09-25. Reject this fixed candidate overall.
It substantially reduces broad coloured spill, but suppresses protected fine
structure. No default is changed and no SOTA or general planar-mode qualification
is earned. The independent review inspected both full overviews and all25fixed
native pairs; root separately inspected both whole images and one native pair
in each of the7named regions. Complete current/candidate images and masters
were shown to the owner, including the adverse detail finding.

The broader contrast improvement is not a tone adjustment: the actual canonical
RAW baseline reproduces current production RGB16 and ICC exactly, and its pinned
rewrite is whole-TIFF byte identical. Candidate uses that same development.
The recipe changes full CFA radiance, including DC, with shared Gaussian weights
on the independently fitted spatial focus front. It does not retain the current
frequency assembly. This establishes a visible tradeoff, not its unique cause.

Independent native inspection finds erased horizontal contact subdivisions,
smeared central stipple, broader lower-array boundaries, and suppressed scratch
branches/small marks. Upper-left contacts show particularly conspicuous surround
cleanup while their edges and interiors blur. Reduced grain, flatter colour or
less spread cannot stand in for preserved detail. The full view is orientation;
these verdicts use the unresampled256/384pixel pairs in views-1/completion.json.

Commands executed from the repository with Python3.12 and `-I -B -X faulthandler`:

```
experiments/chip-focus-radiance/run.py build --out experiments/chip-focus-radiance/build-1
experiments/chip-focus-radiance/run.py build --out experiments/chip-focus-radiance/build-2
experiments/chip-focus-radiance/run.py controls --build experiments/chip-focus-radiance/build-2 --out experiments/chip-focus-radiance/controls-1
experiments/chip-focus-radiance/run.py build --out experiments/chip-focus-radiance/build-3
experiments/chip-focus-radiance/run.py controls --build experiments/chip-focus-radiance/build-3 --out experiments/chip-focus-radiance/controls-2
experiments/chip-focus-radiance/run.py full --build experiments/chip-focus-radiance/build-3 --controls experiments/chip-focus-radiance/controls-2 --out experiments/chip-focus-radiance/full-1
experiments/chip-focus-radiance/run.py views --run experiments/chip-focus-radiance/full-1 --out experiments/chip-focus-radiance/views-1
```

execution.md preserves the first compile error and address-control cancellation.
The latter was repaired with both original points and unchanged separation bar;
the first degenerate point stays recorded. Build3 freshly compiled CLI in184.906s.
Controls2 passes4tests in0.344s. The independent reviewer verifies identities,
planar and refusal JSONs byte-identical to the completed controls1records; only
the address detector changes. Finite-input overflow and zero mass are exercised.

Generated planar MSE is55248.281DN² versus951982.574for the uniform mean;
shifted-front and erased-detail destroyers fail the same fixed bar. Flat MSE is
88.206versus399.947for individual frames and12.119for the full mean. Thus weighting
retains an explicit noise cost relative to all-frame averaging. These analytic
plane-array controls are not calibrated camera physics, actual MHC quality or
evidence of a real-image gain. The full photograph overturns a broad interpretation.

The complete299-source original-RAW observation finishes131.813s. Peak Job
committed memory is3,475,750,912bytes, not RSS. These are bounded operational
readings, not a speed benchmark. Reference149, crop[133,89,3250,2166], all-source
support, input file hashes and after-run metadata checks pass. No original is
written and no aligned-frame volume is retained. Candidate mass stays finite
and positive,15.686945–19.014545; this is normalization safety, not confidence.

| Complete artifact | SHA256 |
| --- | --- |
| Current TIFF | abd056b39bcf8a7d88915260d0fe9bd0bc0ef273744652fb7c6e4d9ec9b187c5 |
| Candidate TIFF | 29e2f315b614d86f972d8d0d909289d591e9b5c16794142498623984fdcdfc17 |
| Current decoded RGB16 | fbeeda70e45be91086e5d6400b642054df908a87ae4021815ad493940960298c |
| Candidate decoded RGB16 | 9215e7b6f01ed9153b1bf56b45aa7102fa47b1be5a9364e914cbf8617eef978f |

Keep the original two-band focus-front refusal and this photographic rejection.
Do not run a width/sigma, site, schedule or source-subset sweep to rescue this
average. Its broad-spill improvement supplies a narrower reconstruction lead;
any distinct estimator must independently preserve detail and confront noise,
misplacement, model mismatch and genuine clipped/occluding structure.
