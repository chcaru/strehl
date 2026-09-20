# Corrected feature-address oracle

**Independently reviewed local headroom, not a complete repair.** The long
cyan/magenta downward column is substantially removed, with the compact bright
contact and black inclusion retained. The right branch remains conspicuous
and may carry a slightly stronger thin fringe than the preceding spatial arm.
The unchanged facet/nearby structure remain intact and no obvious capsule seam
was found. Helicon B is still more compact overall. No two-branch cleanup,
noise-neutrality or competitive SOTA claim follows.

This is a separately named, post-failure manual diagnostic. Only the dark
capsule endpoint changed from(3102,2203) to(3080,2212). All donors, radii,
reconstruction, geometry, noise model, base, limiter and development are held.
The original two failures remain failures. The corrected target was chosen
from their photographs and verified by actual source/mask accounting; it is
not an independently discovered automatic label or a SOTA result.

The complete70-frame output and RGB16 masters are in `corrected-full-1`.
The eight fixed six-arm boards and old/new support outlines are in
`corrected-review-1`. The independent photographic verdict is recorded in
`corrected-results-review.md`; that review, not the mechanical checks below,
determines what the image demonstrates.

MEASURED: the new candidate changes4271 RGB16 pixels versus the preceding
spatial candidate, all inside the predeclared conservative rectangle
[3052,2122,80,120]. Every pixel outside is exactly unchanged, including the
other four canonical windows and the other two donor interventions. The
complete baseline is exact. These counts describe scope, not quality.
All six generated controls pass, including original-mode identity, unchanged
facet/structure masks, the new target's full membership, and the old fan's
decreased membership1 to0.09228515625. Losing old coverage is an explicit
photographic risk, not hidden as an expansion.

Executed with Python312 `-I -B`, and `-X faulthandler` for full/review:

```
python experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-6
python experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-6 --out experiments/donor-consistency/controls-6
python experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-6 --screen experiments/donor-consistency/controls-6 --out experiments/donor-consistency/corrected-full-1 --spatial --correct-target
python experiments/donor-consistency/photo-compare.py --run-dir experiments/donor-consistency/corrected-full-1
python experiments/donor-consistency/corrected-photo-review.py
```

Fresh build153.891s, controls0.547s, complete triplet35.953s, independent view
and whole-image change checks6.274s. These are single operational costs, not
full alignment timing or a competitive speed benchmark. Candidate TIFF SHA256:
`a41c456285253b1031e14fdd6b5313a89d85062d8ff8cfebcfa07613ada25b32`.

The automatic concentration rule has separately failed its true-radial
control and nominated zero sources in124 real tracks. It remains closed.
Unconstrained positive blur fitting cannot establish ownership: a compact
core can explain an unrelated positive feature by putting that feature into
its fitted kernel. No automated correction is promoted from these diagnostics.
The next implementation resumes the already positive complete all-CFA wavelet
screen, extending it to natural boundaries and the actual GPU gather with
explicit propagated source noise. See `complete-cfa-wavelet/next-design.md`.
