# Fixed optical-floor output: legitimate, narrowly scoped

**ARGUED:** `T_optical=B(T_pinhole)` is a legitimate alternative output for this
fixture, where B is exactly its already supplied sigma0.7 discrete PSF. It asks
for an all-in-focus appearance at that supplied optical resolution rather than
undoing the common optical floor. It is a new, post-failure consumer definition:
the original pinhole failures remain failures. Sigma0.7 is supplied synthetic
optics, not a measured camera/lens resolution, and the64/1024 pupil failure is
unchanged. No photographic admission follows from this read-only check.

There is a crucial baseline asymmetry. The saved mean and oracle-donor images
are developed actual observations and **already contain B**, plus focus and
demosaicing effects. Applying B again would handicap these appearance estimates.
For the primary alternate-consumer comparison:

- Filter the complete96×96 truth, each inverse's saved pinhole, and the full
  signed component templates exactly once. Retain all inverse arms, including
  the original Huber visibility1 reference, not merely the latest candidate.
- Compare observed mean/oracle-donor appearance estimates **unchanged** against
  B(T). Their training-only status and restricted oracle-bound interpretation
  remain. Report their different estimands explicitly.
- Filtered copies of those observed baselines may be shown only as a separate
  common-lowpass diagnostic. They cannot be the sole disconfirming baselines.

Applying one common blur to all images is mathematically a valid band-limited
error diagnostic, but it is not automatically a fair captured-appearance
comparison. Calling the latter result an improvement while hiding the baseline
double blur, or silently replacing the earlier quality verdict, would be metric
laundering.

Commission the exact supplied operator, not a visually convenient smoother:
same normalized7-tap separable kernel, f32 sigma bits, channel treatment and
order. `model.py::_blur` uses zero padding, while the independent generator's
`psf` uses nearest padding and the reverse separable order. Neither boundary
can influence the fixed16:80 interior when filtering full96 arrays with radius3;
the small arithmetic difference needs a fixed numerical tolerance. Do not blur
an already cropped64×64 or core patch. A one-layer forward evaluated exactly at
its supplied focus is an independent consumer witness for B(pinhole), subject
to the already known interpolation/roundoff tolerance.

Required fail-capable checks before interpreting the new numbers:

1. Exact B(T) is the positive. A half-glint or half-coloured-filament destroyer
   must still return half recovery using **B(template)** and the correspondingly
   transformed absent-component image. Do not mix pinhole templates with optical
   output or mask a template before filtering; the3-pixel apron must be real.
2. B(B(T)) is the fixed double-blur destroyer. It must remain distinguishable
   by true-component/detail requirements after the target change. If the chosen
   bars admit it, disclose that the check cannot reject this extra blur instead
   of interpreting lower colour error as preserved detail. Do not alter sigma
   or search a blur amount to make this control convenient.
3. A fixed wrong-colour image (e.g. R/B-swapped truth before B) must remain
   rejected by RGB/chroma and per-colour filament requirements. Low-pass filtering
   must not erase the test's ability to detect the measured colour regression.
4. Keep flat first and keep all existing strict paired core/ridge RGB **and
   chroma** guards against B(visibility1), with same-domain absolute comparisons
   to the unchanged observed mean/oracle. The new target must give the older
   inverse and simple observed baselines an opportunity to win. No best arm or
   best phase may be selected from these saved-data results.

The strongest directly matched falsifier is **B(matrix) versus B(visibility1)**
on the fixed colour/detail regions. It changes the consumer identically for
the two inverses. A disappearance of the latest colour regression under this
fixed operator would establish a target-resolution dependence, not identify
the source of the error as an optical nullspace or prove a safe new prior.
Held-out raw predictions do not change because no state or forward model is
refitted. Preserve those failures and stationarity limits alongside the new
appearance results. This critique performed source inspection only; no filtering,
scoring, refitting or numerical experiment was run.
