# M110 — pre-registration

Written **before** any measurement in this milestone. Committed before the probe
was built. Nothing below may be relaxed after a reading; a bar that fails for a
reason I did not anticipate is a finding, not a bar to edit (discipline 710).

## The question

Fact 1435: the shipped alignment solve's per-frame placement track on
`bee-3-cpl` has a **second-difference jitter of median 0.4829 plane px**, p90
1.0772, max 9.7069, with 13.8% of adjacent pairs disagreeing by >= 1 px, against
a derived curvature ceiling of 0.0092 px — a factor of ~110. Read with fact 1393
(`n_eff = 1` wherever there is detail), the predicted consequence is local
geometric incoherence at election boundaries, not softness.

**The proposed corrective:** a roughness penalty on the second difference of the
placement track, added to the existing free `solve_global`, rather than
replacing the free solve with a parametric one.

## Prior art found before designing anything (rule 43)

1. **`GlobalOptions::smooth` already exists** (`align.rs:1767`) and
   `solve_global` already emits `[1, -2, 1]` penalty rows at `align.rs:2088`.
   The operator the brief asks me to add is already in the code; it defaults to
   `0.0` and no product path sets it.
2. **It has already been measured once, and it lost.** Fact 1181 / M86 P20:
   at `smooth = 0.02` it costs **+65%** held-out on `bee-3-cpl`
   (`S6-ba-smooth` 19.236 px against `S3-ba-unit` 11.649 px), and M86 §13.5
   wrote "do not use `GlobalOptions::smooth` on a well-conditioned deep stack".
   It **wins** on `foam` (2.454 px), the stack with the weakest edge set.
3. **M86 tested exactly one value of the parameter** and never measured the
   quantity fact 1435 introduced. So what is unanswered is not "does a
   second-difference prior exist" but "**is there a lambda at which the
   high-frequency jitter dies and the low-frequency accuracy survives**", and
   "does the removal survive a real discontinuity".

Therefore this milestone is a **sweep plus a robustness change**, not a build of
a new operator. Anything else would re-derive a settled answer (rule 40).

## Why this operator and not `solve_poly` (facts 1, 47)

- **Fact 47** prices the parametric win at ~6%, inside the noise, and says
  deep-stack alignment error is set by the *edges*, not the solver. So a
  parametric solve cannot be justified on absolute accuracy.
- **Fact 1** records that *no low-order polynomial in frame index matches a
  direct per-frame fit*. A global degree-6 polynomial is a **hard rank
  constraint**: it removes all structure outside a 7-dimensional subspace
  regardless of frequency.
- A second-difference penalty is **frequency-selective by construction**. Its
  response to a mode of wavenumber `w` is `(2 - 2 cos w)^2`, which is `O(w^4)`
  at low `w` and `16` at `w = pi`. DERIVED: it attenuates the Nyquist mode by
  `16 / (w/pi)^4 ~ 10^4` times more strongly than a mode with a 10-frame period.
  That is exactly the separation fact 1435 needs — the jitter is high-frequency
  (M103 §18.6 measured it nearly flat in lag, i.e. **bounded and
  high-frequency, not accumulating**) while fact 47's 6.76 px is smooth drift.
- `lambda = 0` recovers today's solver exactly, so the null control is built
  into the parameter.

## Fixed definitions

- **Stack**: `bee-3-cpl`, 299 frames, `D:\personal\macro\bee-3-cpl`.
- **Edges**: M103's committed dump `experiments/M103-halfdrift/data/A-deep-edges.csv`,
  filtered to the shipped ladder `--only-spans 1,2,4,8,16,32,64,96,128`
  (`align_cmd.rs:46 DEFAULT_SPANS`). Read-only; not modified.
- **Solver settings**: `Weighting::Unit`, `irls_iters = 3`, `huber_px = 3.0`,
  geometry 3516x2344 — the shipped `GlobalOptions` (`align_cmd.rs:343, 904`).
- **rho** = `corner_radius` = `hypot(3516, 2344)/2` = 2112.8618... plane px.
- **Jitter statistic (identical to M103's `jitter.py`, so the numbers are
  comparable)**: `|ln|A_{j+1}| - 2 ln|A_j| + ln|A_{j-1}|| * rho`, over all 297
  interior frames. Gauge-invariant by construction (a constant offset cancels
  twice). Reported as median / p90 / p99 / max / fraction >= 1 px, and split
  near (`|j - 149| <= 50`) and far (`> 100`) from the reference.
- **Held-out error**: the shipped M10 protocol, copied from
  `align_cmd.rs:459 heldout_error` — test set is `span >= 40 && used >= 12`,
  training is everything else, score is the **median** corner error of
  `edge_errors` over the test set.
- **lambda grid**: `0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1`.
- **lambda\* selection rule, fixed now**: the **largest** lambda on the grid
  whose held-out error satisfies B2. B3 is then scored at that lambda\* and
  **lambda\* is not re-chosen if B3 fails**.

## Bars

### B0 — instrument check (void everything below if it fails)

My probe's `lambda = 0` solve on the edge set above must reproduce M103's
committed baseline `C:\dev\strehl-out\M103\wm-baseline-r149.txt`:

- **1196 of 1196 IEEE-754 f64 words bit-identical** (4 words x 299 frames), and
- jitter median within **0.0001 px** of fact 1435's **0.4829 px**.

### B1 — NULL CONTROL, and it must be shown to fail

- **B1a**: with `lambda = 0`, the solver **after** my change produces placements
  bit-identical to the solver **before** it, on the same edge set:
  **1196/1196 f64 words equal, 0 differing.** Not "~identical" — the count is
  the bar.
- **B1b**: deliberately break it. Emit one penalty row at `lambda = 0` with
  weight `1e-12` — a perturbation far below any tolerance a sloppy check would
  use — and confirm B1a reports **> 0 differing words**, i.e. goes RED.
  A control never shown to fail is not a control (discipline 706).

### B2 — no regression in absolute accuracy

`heldout(lambda*) <= 1.02 * heldout(lambda = 0)` on the same edge set and the
same protocol.

I register the **relative** form because the corpus's 6.758-6.76 px figure is a
**`coffee-bean`** number (M86 §G0 / fact 1181's provenance), not a `bee-3-cpl`
one; M86 §4 reports `bee-3-cpl` at **11.562 px**. Quoting 6.76 px against a
`bee-3-cpl` solve would be a gauge error of the kind discipline 698 exists to
stop. The absolute `lambda = 0` value is measured in the same run and reported.

**This bar has power and is expected to be the one that kills the design**:
M86 already measured +65% at `lambda = 0.02`, which is inside my grid.

### B3 — the target quantity must actually fall

At `lambda*`: **median jitter <= 0.2415 px**, i.e. a **>= 2.00x** reduction from
0.4829 px. p90, max, `>= 1 px` fraction and the near/far split are reported
alongside; the far tail (max 9.7069 px) is where the mechanism predicts the
largest win.

### B4 — POSITIVE CONTROL, two-sided

Both arms use **synthetic edges generated from a truth track that carries
`bee-3-cpl`'s real measured curvature** (fact 1410 forbids a linear plant), on
the same shipped span ladder, with the same `used`/`rms`/`lever` statistics as
the real edges so the weighting is unchanged.

- **B4a — planted jitter must be removed in the predicted proportion.**
  Plant an alternating `+/- 0.5` corner-px component. At `lambda*` the recovered
  alternating amplitude must be **<= 0.50x** the planted amplitude, **and** must
  agree with the derived Nyquist transfer function to within **+/- 20%
  relative**. The transfer function is derived in the harness *before* the run
  and stored in the output.
- **B4b — a planted real step must survive.** Plant a genuine discontinuity of
  **10.0 corner px** at frame 150 on top of the curved truth. At `lambda*` with
  the **robust** penalty:
  - recovered step height **>= 90%** of 10.0 px, and
  - **<= 5** frames deviate from truth by more than 0.5 px.
  **Negative control that gives B4b its power**: the identical plant at the
  identical `lambda*` with a **purely quadratic** penalty must FAIL at least one
  of those two thresholds. If it passes, B4b has no power and is reported as
  having none rather than as a pass.

### B5 — the falsifier from fact 1

Removed signal `r(j) = ln|A_0(j)| - ln|A_{lambda*}(j)|`, in corner px.

- Registered reading: **lag-1 autocorrelation `rho_1 <= 0.0` AND fraction of
  power above `w = pi/2` >= 0.5** ⇒ what was removed is estimation error, the
  outcome the design wants.
- `rho_1 > 0.0` ⇒ smooth structure was removed; cross-check B2 and B4b, which
  should already have caught it.
- **Power control**: the same statistic on the B4b step plant solved with the
  **non-robust** penalty must read `rho_1 > 0`. If it does not, B5 cannot
  distinguish the two cases and is reported as having no power.

### B6 — visibility. Run **only if** B1-B4 pass.

A/B render of `bee-3-cpl` differing **only** in the sidecar (regulariser on vs
off). Both arms resample identically, so fact 1436's -33.0% resample confound
cancels; no arm may be added that does not resample. Integer-only registration
between panels, no auto-levels, no exposure change between panels. Report max DN
delta, RMS delta, fraction of pixels differing, and a plain visual verdict.

**"Invisible" is an acceptable and valuable result and will be reported as such.**

## Rule 20 — what input makes each bar FAIL

| bar | an input that fails it |
|---|---|
| B0 | any drift in `solve_global` since M103, or a different edge subset |
| B1a | any change to the `lambda = 0` code path, including reordering a sum |
| B1b | a check written with a tolerance instead of bit equality |
| B2 | `lambda* >= 0.02`, where M86 already measured +65% |
| B3 | a `lambda*` too small to attenuate the Nyquist mode |
| B4a | a penalty that does not actually reach the Nyquist mode |
| B4b | a purely quadratic penalty at a `lambda` large enough to pass B3 |
| B5 | a removal that is smooth in `j` |
| B6 | two byte-identical renders, or a delta below the display quantum |
