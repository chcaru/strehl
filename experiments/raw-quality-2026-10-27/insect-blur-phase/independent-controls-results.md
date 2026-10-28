# Independent control receipt and seed decision

2026-10-27. **VERIFIED from saved outputs; no RAW/reconstruction rerun.** The
fixed screen passes its declared controls. This establishes a narrow producing
phase-reader mechanism, not current weevil placement error or photographic gain.

Root's command was:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/run-controls.py --iteration 1
```

[Completion](../../../outputs/raw-quality-2026-10-27/insect-blur-phase-controls-1/completion.json)
and [scientific receipt](../../../outputs/raw-quality-2026-10-27/insect-blur-phase-controls-1/output/receipt.json)
are complete. The job exited0 in9.844s, no active/terminated children or cleanup
errors, peak committed host2,935,906,304bytes. Four CPU threads/one interop,
TF32 off; Torch peak allocated41,026,560/reserved62,914,560bytes. Whole-host
CPU samples reached17.1%; this tiny screen is not a full-workflow benchmark.

I freshly hashed214 unique referenced files,24,345,077bytes, including all
completion artifacts/source bindings, and checked the six archived executed
sources byte-for-byte against the current files. Controls are
`e28a22cf9b54a071c214ce5444c40d78a929bca63d7ea6752126b25979d0fa42`,
producer `99bca095aa6c203ff248184f6c4b08801682565e65c03afabed5e9d5585f9410`,
protocol `1295517b128f52d6eac46e0260d2801de2ee73620a704fbfcd0c76bd48c49faa`.
Completion SHA is `80fe7c11e1495f5fd695596be8d4550893c2b63490ba39bb2e805f17bf28be32`;
scientific receipt SHA is `a868a8fe9dc9fe997480d32b7cff32c972391d2a2c1413e1022ec520b6b19812`.
No corpus pixels were read by the screen. Its estimated-map curvature plant
is explicitly not calibration; maximum departure from its endpoint chord is
5.86943 native pixels, evaluated across the saved299 positions.

All80 arm errors/acceptance gates were independently recomputed from saved
vectors and truth. The first audit's unnecessary bit-equality comparison of
Python math.dist and the saved NumPy norm failed at floating reduction order;
the measured maximum difference is4.44e-16 native pixels. All actual0.10-pixel
gate decisions agree; no experimental threshold or saved result changed.

| Fixed population | p1 accepted | p2 accepted | p2 maximum native error |
| --- | ---: | ---: | ---: |
| Exact/noisy flat and rank-one,6 pairs | 0 | 0 | Refused |
| Gaussian,6 pairs | 6 | 6 | 0.049411 |
| Sign-changing disk,4 pairs | 1 | 4 | 0.046875 |
| Seven curved rungs x two phases,14 pairs | 0 | 14 | 0.056497 |

The one admitted disk p1 result is wrong by3.542777 native pixels, while its
p2 counterpart errs0.034939. This is a controlled sign-inversion benefit,
not just selective p2 refusal. Gaussian p1 maximum is0.09375. Wrong sign,
factor-two, origin omission and green-phase foils pass. Batch/singleton
decisions/vectors/grid locations match; maximum score-surface difference is
2.38419e-7 against2e-6. The half-period control admits both declared branches;
seed0 is physically wrong by128 pixels. Branch validity remains external.

Six of eight adverse p2 results are accepted: asymmetric, nonperiodic-window
and similarity cases on both greens, errors0.015625..0.049411 pixels. Both
two-depth cases refuse for ambiguous local peaks, despite candidate errors
1.92060/1.89321 pixels. Thus no admitted adverse failure exceeded0.10 in this
small set. This does **not** establish that asymmetric blur or occlusion will
always refuse or be harmless; confidence is still a heuristic. All adverse
results remain in the receipt, with no physical-motion attribution.

## Held-map initialization: explicit conditional release

**ARGUED:** keep the commissioned +/-2-native-pixel reader. A held-map-seeded
direct-pair refinement is preferable to enlarging its search after the screen.
It is a changed initialization contract, not a fresh independent alignment
from the old coarse initializer. It cannot diagnose or repair an error beyond
its local branch, and an accepted zero residual does not validate the held map.

For maps T_i from anchor149 to source i, the pair proposal must be
T_j composed with inverse(T_i), evaluated at each actual reference-i physical
patch center. Use the same proposal, integer-origin policy, original G1/G2
samples and requested pair/tile population for p1/p2. Preserve literal origins
and the native-unit returned total displacement; do not substitute a guide
centroid or lose the phase offset. Finite-patch breathing remains uncorrected
inside this unresampled translation reader.

Fit similarities from the resulting direct measurements and use the existing
global anchor-component solver. Seed transforms are proposals, never measured
edges. Retain refused/boundary pairs, compare full accepted populations,
placement coverage and cycle rank, and disclose any unplaced sources. Do not
silently fall back to old NCC edges, pool p1/p2 winners, discard short spans or
regularize corrections toward the seed. Any separately proposed hybrid would
need an explicit producing contract.

The useful next decision is then the complete paired p1/p2/baseline photograph
with unchanged consumer/development and full-resolution masters. No additional
ROI, interval, radius or confidence search is warranted by this screen. This
review supports that bounded conditional experiment; it does not license a
physical placement claim or automatic production correction.
