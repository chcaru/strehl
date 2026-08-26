# V-M111 — independent verification of M111's halo-correction claim audit

**Verifier:** V-M111 (independent). **Subject:** `docs/research/M111-waxy-blobs.md` §18, facts P46–P52,
disciplines P53–P55, commit `4cebacb`. **Folded by ORCH as:** SYNTHESIS facts 1595–1602, disciplines 821–823.
**Method:** every claim re-derived from the underlying script/JSON or read at primary source in
`docs/research/M87-occlusion.md`. M111's prose was used only to fix the *wording* of each claim, never as evidence.
**Worktree:** `git worktree add --detach C:\dev\strehl-out\V-M111 HEAD` (detached `3a8177a`), removed after use.
No file under `crates/` was modified. `SYNTHESIS.md`, `AGENTS.md`, `README.md`, `docs/captures-needed.md` untouched.

## 0. Bottom line

**Do not enable `STREHL_FIX_HALO`. The conclusion survives verification, and is stronger than M111 stated it.**
It rests on four independent legs, three of which M111 did not lean on: M87's registered bar **V3 FAILED**
(`56-bmf.json` `bars.V3 = false`); band RMSE against ground truth rises **monotonically** +215.9/+354.4/+558.4 %;
ISO returns verdicts **4 % apart** on reconstructions **six orders of magnitude** apart in true error; and the
report's own author never retracts the recommendation anywhere in 5 400 lines.

**ORCH's blur hypothesis is dead.** BMF = 4.428 is exact and the coarse match is 4.3e-12. Not a near miss.

**Eight of ten items confirmed; two carry defects that ORCH has folded verbatim** (items 6 and 7 — see §2).
I also found **one defect M111 missed in its own guard**: the numeric arm is **sign-blind**.

## 1. Per-item verdicts

| # | Claim | Verdict | Primary source | Re-derived |
| --- | --- | --- | --- | --- |
| 1 | BMF = 4.428, five numbers, direction | **CONFIRMED** | `M87/data/56-bmf.json`, `src/56-bmf.py`, M87 §23 | BMF − fine/blur_fine = **0.000e+00** |
| 2 | Pre-registration precedes the data | **CONFIRMED-BUT** | `src/56-bmf.py` docstring; commit `d9c2b89` | git cannot order it; mtime + self-falsification can |
| 3 | Metric is not a sharpness proxy | **CONFIRMED-BUT** | `data/36-registration-controls.json` | `resample_pct` = **+0.5791520675613199** |
| 4 | 87.9/84.6 from an unshipped pipeline | **CONFIRMED** | `src/20-local-partition.py`, `data/42-ship-metric.json` | 87.852 / 84.611 / **72.933**; gap **15.0 pts** |
| 5 | M87 recommends against enabling | **CONFIRMED** | M87 §16.9 title, §0 L44, §23.3 | no retraction in 5 400 lines |
| 6 | Non-occluding control | **CONFIRMED-BUT (defect)** | `data/22-plant-truth.json`, `src/16-plant.py` | 1.000 / **0.394326** / 2.5360 / 2.86617 |
| 7 | Far-frame control miscounted & mis-aimed | **CONFIRMED (counts) / MISLABELLED (mechanism)** | `crates/strehl-cli/src/merge_cmd/halo.rs:444`, M87 §3.3 | 79 / 220 / **2.7848** |
| 8 | Silhouette-keying, not blur | **CONFIRMED** | `data/21-cost.json`, `data/16-plant.json`, M87 §16.3 | 0.854131 vs 0.820904; **6.29 orders** |
| 9 | d40 destroys 9.4 % of the fine band | **CONFIRMED-BUT** | `data/56-bmf.json` | 1 − 0.9058119414185171 = **9.4188 %** |
| 10 | M111's guard had an inert arm | **CONFIRMED-BUT + NEW DEFECT** | executed | numeric arm fired **0 of 7**; now proven live; **sign-blind** |

### Item 1 — BMF = 4.428. CONFIRMED, exactly.

All five numbers are present in `experiments/M87-occlusion/data/56-bmf.json`, region `DAMAGE`:
`fine` 0.9058119414185171, `coarse` 0.9145749511806655, `blur_coarse` 0.9145749511849404
(|Δ| = **4.2749e-12**), `blur_sigma` 5.107862440268608, `blur_fine` 0.2045521012027618, `BMF` 4.4282700402115793.
`BMF − fine/blur_fine = 0.000e+00`. Direction confirmed: BMF ≫ 1 means the correction keeps **4.43×** as much
fine band as the blur that matches it on the coarse band, which refutes "no better than a blur".

**Arithmetic nuance ORCH should know:** 90.58/20.46 from the *rounded* percentages is **4.42717**, which rounds to
4.427, not 4.428. The report's 4.428 is right from full precision. Anyone re-checking from the printed
percentages will get a one-in-the-last-place mismatch and think they found an error.

**The stronger fact M111 buried:** the registered bar **V3 FAILED** (`bars` = `{V1: true, V2: true, V3: false, V4: true}`).
V3 required the correction to remove *more* coarse than fine; it removed **less** (0.9146 coarse retained vs
0.9058 fine). M87 §23.3 calls this "the important failure". This is a *do-not-enable* datum sitting inside the
same file as the *blur-refuted* datum, and it is the load-bearing half.

### Item 2 — Pre-registration. CONFIRMED-BUT.

`src/56-bmf.py` carries `REGISTERED BARS -- WRITTEN BEFORE THE SCRIPT WAS RUN`, with V4:
`PREDICTION: the shipped d=40 correction scores BMF <= 1.05 ... If BMF >> 1 my §16.9 reading was too harsh and I will say so.`

**Git cannot prove the ordering**: script and JSON landed in one commit, `d9c2b89` (2026-08-24 07:36:22).
Two corroborations: filesystem mtimes `56-bmf.py` 07:33:14 → `56-bmf.json` 07:34:08 (script precedes data by 54 s);
and — decisive — **the registered prediction was falsified by its own data and conceded** in §23.3 and fact P59.
A back-dated pre-registration is written to win, not to lose.

**Correction to ORCH's framing.** Fact 1595 says M87 pre-registered "in ORCH's direction". True as a *direction*,
false as a *chronology*: M87 registered this against **itself** at 07:33, roughly eleven hours before ORCH raised
the blur hypothesis. It is convergence, not deference. M111's own P53 is accurate on this; the paraphrase drifts.

### Item 3 — The metric is not a sharpness proxy. CONFIRMED-BUT (two operations spliced).

`data/36-registration-controls.json`, `resample_pct` = **+0.5791520675613199** = 100·(Uw/U − 1) from
U = 0.06804824389038239 (unresampled) and Uw = 0.0684423467018127 (Catmull-Rom warped). **Sign is positive**, and
in this section's convention positive means ISO went *up* — the destruction did not flatter the metric. Confirmed.

**But the "~49 % of gradient energy" is not M87's measurement of this arm.** It is inherited from **M86 P23**
(`docs/research/M86-alignment.md:581`): Catmull-Rom "retains 0.5139 of a real frame's gradient energy … a single
gather still costs ~49 %", measured at a **half-pixel shift on a single real frame** — the worst-case phase.
M87's arm is a **similarity warp** (scale 1.0473871678075815) applied to the **merged** image, so sub-pixel phases
vary across the field and the gradient-energy actually destroyed is **unmeasured and ≤ 49 %**. M87's own docstring
discloses it "warps AFTER the merge … It therefore bounds the interpolator's lowpass rather than reproducing arm
A's exact path." M111 partially discloses the splice in its §18 ("covered, but by different arms and different
statistics"); ORCH's fold does not.

**The structural claim is independently sound and does not need the 49 %.** `m87metric2.score_iso` samples image
**values** along edge normals, normalises by a far-field baseline median, and takes an overshoot statistic. There
is **no gradient and no Laplacian term anywhere in it**. ISO cannot be a sharpness proxy by construction, which is
already SYNTHESIS fact 1307.

### Item 4 — 87.9 %/84.6 % come from an unshipped pipeline. CONFIRMED, all three qualifiers.

Verified from the script, not the prose. `src/20-local-partition.py`:
* **gate 0** — it builds its own merge as `argbest = np.argmax(field, axis=0)` then `take_along_axis`. Pure argmax, no promotion gate.
* **ROI crops** — flower `FBOX = (700,1700,900,2100)`; bee from cached `bee3-leg-*.npy` = `ROI_LEG (1200,1900,300,1400)` plus a 22 px margin.
* **unaligned** — frames are read at fixed coordinates with no warp applied.

`data/20-local-partition.json`: bee `local-d40.delta_pct` = 87.8522868521695 → **87.9 %**; flower = 84.61072502896403 → **84.6 %**.
Shipped path: `data/42-ship-metric.json` `delta_pct` = **72.93287068931788**, ISO 0.06406250130015284 → 0.01733988006656978,
n_prof 5714, rendered by the §16.7 command with `--gate 2 --srgb --demosaic` and a `STREHL_WARPMAP` sidecar. Gap = **15.0 points**.

**Caveat for the fold:** 87.9 % and 72.9 % differ in **region and pipeline and implementation** (Python prototype vs
the Rust binary). "Overstates by fifteen points" is a difference of two measurements, not a controlled delta. The
qualifiers M111 asserts are all true; the 15-point number is not attributable to any one of them.

### Item 5 — M87 recommends against enabling. CONFIRMED. The withdrawal is NOT broader than M111 says.

This was the most consequential item and I checked it exhaustively rather than by quotation.

* Section title, verbatim: `### 16.9 The full-frame result, and why I am telling you not to enable it`
* Verbatim finding: "they have been replaced by a smooth, milky, **scalloped** band that follows the silhouette.
  It is larger, softer and more conspicuous than the halo it replaced. **It looks worse.**"
* Withdrawal banner, verbatim (line 1699): "⚠ **PARTIALLY WITHDRAWN by §23.3 / P59.** The conclusion — *do not
  enable this by default* — **stands**, on the strengthened evidence of registered bar V3, which the correction
  FAILS … But this section's implication that the result is **blur-grade destruction** was too harsh and is
  withdrawn … The defect is insufficient *selectivity*, not destruction."
* §23.3, verbatim: "**§16.9's implication that this is blur-grade destruction was too harsh** and I withdraw that reading."
* Fact P59 consequence: "**§16.9's implication of blur-grade destruction is withdrawn.** The correction is
  genuinely structured, merely insufficiently selective."
* Still standing: §0 VERDICT L44 "**Do not default this on.**"; §16 header L1500 "do not turn this on by default";
  §23.4 L2525 "the default-ON blocker".

I ran a whitespace-collapsed scan of **all 5 400 lines** for retraction and enabling language
(`experiments/V-M111/scan_withdrawals.py`): 9 do-not-enable statements, 3 enable-positive matches (all
counterfactual or quoting the flag name), 33 "withdraw" occurrences. **Only two touch the halo recommendation —
the §16.9 banner and §23.3 — and both are mechanism-only.** There is no late retraction. **Fact 1597 is safe.**

*Minor correction to the commission's framing:* M111 cites §§24.5, 25.9, 28.7 as places showing the BMF result
**still stands**, not as the location of the withdrawal. Verified: §24.5 "The BMF bar of §23 is computed in named
bands over a stated region and is unaffected"; §25.9 "it goes in paired with `BMF`, never alone"; §28.7 "None is
withdrawn". M111's quotations are verbatim-accurate.

### Item 6 — The non-occluding control. CONFIRMED-BUT — and ORCH's fold carries a factual error.

All numbers exact in `data/22-plant-truth.json`: control `moved_frac` = **1.0** at d10/d20/d40;
`iso_delta_pct` = −186.61661286218143 / −141.95215104923915 / +63.92997491506704;
`rmse_band_delta_pct` = 215.9272880666851 / 354.3743093662254 / 558.4216991248774 (monotone increasing);
occluding arm `moved_frac` = 0.39432565789473684. Ratio = **2.5360** ("2.5×"). The "2.9×" is a different quantity:
ISO_d10/F0_ISO = 0.03918438112879363/0.013671357266243078 = **2.86617**.

**(a) Does the control contain occlusion?** Partly — and the loose language matters. From `src/16-plant.py`,
the control composites an opaque dark bar (F = 0.08) over textured background (mean 0.75) as `img = fb + bb·(1−a)`.
That **is** a geometric occluder with a strong silhouette. What the control removes is the **depth step**
(`KB = KF = 40`), so there is no differential defocus, no two-layer veil, and no occlusion-halo mechanism.
Its measured ISO floor is genuinely low: **0.01367 vs 0.03060** for the occluding arm (2.2×). So the control is
**fit for purpose** — it is a same-depth silhouette, which is precisely the discriminandum. But M87, `halo.rs`
and M111 all describe it as "no occlusion at all" / "no defect at all", which is not literally true.

**(b) `moved_frac = 1.000` is forced by construction, not measured.** I rebuilt the plant from M87's own
`16-plant.py` and computed the elected-frame distribution directly (`experiments/V-M111/plant_moved_frac.py`).
Over the control's 24 320 treated pixels, `max |argbest − k_F| = 3` frames. Every treated pixel elects within
**3** frames of the foreground, so **any** delta ≥ 4 forbids 100 % of them. That is why the value reads exactly
1.000 at all three doses — it is not a dose response at all. `src/22-plant-truth.py` says so in its own docstring:
"the forbidden band contains the background's own focus peak, and the partition **must** wreck it."

The same run reproduced the occluding arm at **0.394326** (JSON: 0.39432565789473684) and showed why it too is
constant across doses: the distribution is bimodal, 39.4 % at |Δk| ≤ 3 and 60.6 % at |Δk| ≈ 49–52, with nothing in
between, so deltas of 10, 20 and 40 all cut at the same place.

**Therefore the "2.5× more aggressive" ratio is a designed-in tautology, not evidence.** The non-tautological
version of the identical finding is fact P30 on **real** data — item 8 — and that is what should be cited.

**(c) ORCH's fact 1598 contains a factual error, inherited verbatim from M111's P50.** Both say 0.394 is
"the real occluding scene". It is not: it is the **synthetic plant's two-depth arm**
(`22-plant-truth.json` key `occluding (KB=90, two depths)`). On the **real** occluding scene the figure is
**0.821** (`21-cost.json` `bee.local-d40.moved_frac_of_treated`), against 0.854 at the planted disc — a ratio of
**1.04×, not 2.5×**. The fold invites the reader to believe a 2.5× aggression gap was measured on real data. It was not.

**(d) "Non-monotone" needs care.** The three quoted percentages (−186.6/−142.0/+63.9) are themselves
**monotone increasing**. The non-monotonicity is in ISO(dose) **including the untreated baseline**:
0.013671 (d0) → 0.039184 (d10) → 0.033078 (d20) → 0.004931 (d40) — up, then down, with a sign reversal.
The substance is right; the presentation invites a reader to check monotonicity of the wrong sequence.

**(e) Disclosed at source, to M87's credit:** the plant's V5 capability bar **failed**
(`16-plant.json` `capability: false`; truth-composite ISO 0.00857 against a registered ≤ 0.005), as did the C1/C3
placebo bars (0.01269, 0.00622), with a post-hoc revised bar "signal ≥ 4× larger than placebo", measured 5.4×.
Disclosed and explained, not tuned away.

### Item 7 — ORCH's far-frame control. Counts CONFIRMED; mechanism MISLABELLED as MEASURED.

**Counts, verified against the shipped code rather than any report.** `crates/strehl-cli/src/merge_cmd/halo.rs:444`:
`fn allows(&self, s, k) -> bool { (k as i32 - self.kf[s] as i32).unsigned_abs() >= self.delta as u32 }`, with
`pub const DELTA: u16 = 40` (L86). Its unit test `the_band_is_the_only_thing_that_vetoes_a_frame` (L611–634) pins
kf = 100 → 139 forbidden, 140 allowed, 61 forbidden, 60 allowed, so the forbidden set is {61…139} = **79 frames**.
Complement of 299 = **220**; 220/79 = **2.7848** → 2.8×. bee-3-cpl has 299 frames (§16.11).
**Caveat:** 79 holds only where the band is interior. For `k_F < 39` or `k_F > 259` the band clips against the
sweep ends and fewer frames are forbidden, so **79 is a per-pixel upper bound**, not a constant.

**Guard weakness worth recording:** `halo_claim_guard.py` computes `forbidden = 2*DELTA - 1` with
`DELTA, NFRAMES = 40, 299` hardcoded **in the guard itself**. Under AGENTS rule 35 those three checks have no
independent term — the test's subject and object are the same value. I verified 79/220/2.8 against `halo.rs`
and its unit test instead.

**Mechanism: M87 labels it ARGUED, and ORCH folded it as MEASURED.** M87 §3.3 labels its own paragraphs
explicitly. MEASURED: near-band elected-value percentile rank **0.675** vs far-field **0.429**; median
|k_elected − k_F| **32** frames near vs **96** far. DERIVED: the estimator-seam reading. **ARGUED**: the sentence
"Those pixels are therefore **yoked** to the foreground's focus decision and elect k ≈ k_F" sits under
"**ARGUED, and it explains the sign.**" §3.4's support ladder returns a pre-registered verdict of **MIXED**.

**Independent test of whether the "mostly misses" prediction is true.** It is true on real data and **false on
M87's own plant**, and neither M111 nor ORCH says so:
* **On the bee:** the treatment moves **82.1 %** of treated pixels (`21-cost.json`), so 82.1 % elect *inside* the
  near band and the complement arm could forbid at most **17.9 %** — an under-treatment of **4.58×**. M111's
  prediction is correct here, and this measured number is the evidence it should have cited.
* **On the plant's occluding arm:** the treatment forbids 39.4 %, the complement forbids **60.6 %** — the
  complement would move **more** pixels, not fewer. The prediction **inverts**.

So the mechanism claim is scene-dependent, and its truth on the shipped subject is an *implication* of a measured
moved-fraction, not a measurement of yoking. It should not be folded as MEASURED without that chain shown.

### Item 8 — Silhouette-keying, not blur. CONFIRMED at primary source.

`data/21-cost.json`: `control_nonoccluding_disc.local-d40.moved_frac_of_treated` = **0.8541305725755335** (85.4 %)
against `bee.local-d40.moved_frac_of_treated` = **0.820904169997264** (82.1 %). The whole ladder agrees:
d20 73.9 % vs 67.9 %, d80 93.3 % vs 96.0 %. Both are measured **in the real bee image**, which is what makes this
the load-bearing version of item 6. M87 §16.2 verbatim: "It keys on **silhouettes**, not on **occlusions**, and it
cannot tell them apart."

`data/16-plant.json`: "modelled alpha, correct scale" `rmse_rel` **0.017068437557895503**, ISO **0.006476070070566**;
"BROKEN: swapped layer order" `rmse_rel` **33116.841299017135**, ISO **0.006758630564818**. Ratios: RMSE
**1.940e+06** (**6.29 orders of magnitude**), ISO **1.0436** (4 % apart). Of four deliberately broken
reconstructions ISO flagged exactly one (the wrong-`k_F` arm, ISO 0.03044); M87 §4.4: "Registered bar X4 said the
metric must notice. It noticed once in four." M87's binding rule is verbatim at source: "no halo-removal arm may
be certified on ISO alone." **Fact 1600 is safe as written.**

### Item 9 — d40 destroys 9.4 % of the fine band. CONFIRMED-BUT (region qualifier).

1 − 0.9058119414185171 = **9.4188 %**. The inputs *are* the shipped renders
(`30-SHIP-BEFORE-default.tif` / `31-SHIP-AFTER-fixhalo.tif`, 4688 × 7032 × 3, produced by §16.7's `--gate 2`
command with the warpmap sidecar) — so "on the shipped frame" is correct against the *render*.
**But the statistic is computed over a 700 × 1100 ROI window** `R_DAMAGE = (866, 1566, 1050, 2150)`, selected as
"the location of the strongest correction in the frame". M111's P49 phrase "measured on the real full frame" is
imprecise. This is a much milder issue than item 4 — there the whole *pipeline* differed; here only the
*measurement window* does, and it is honestly labelled at source. The paired no-op window
`(1500, 2100, 3500, 4300)` correctly reads `changed_frac 0.0, fine 1.0, coarse 1.0`, which is a real negative control.
Coarse removed at the same site: **8.5425 %** — less than the fine, which is bar V3's failure again.

### Item 10 — M111's own guard defect. CONFIRMED-BUT, and I found a further defect.

Settled by execution, not reading.

**Structural fact.** In `pin`'s loop, `if literal not in row: fails.append(...); continue`. The `continue` makes
the numeric comparison **unreachable by any report-side mutation**. The numeric arm can fire only when the
**source** value moves away from the report's literal.

**Part A — which arm caught M111's seven report plants?** I re-planted all seven and classified the firing arm.
**The numeric arm fired in 0 of 7.** Six were caught by LITERAL-PRESENCE. D4 ("V3 false" → "V3 true") was caught by
a *separate* standalone report-text check (`if "V1 true, V2 true, V3 false, V4 true" not in rows["P49"]`), which
does not short-circuit anything. So M111's P55 is right in substance — 7/7 green from an instrument whose
source-opening arm had never fired — but slightly imprecise in attributing all seven to the short-circuiting arm.

**Part B — the numeric arm is now LIVE.** Proven with targets M111 never used, planted into a redirected copy of
the source data via the guard's `M111_HALO_DATA` override:
* **N1** `blur_sigma` 5.107862 → 5.9 → `FAIL P46: report says 5.108, source says 5.900000`. Numeric arm.
* **N2** control RMSE d20 354.374 → 400.0 → `FAIL P51: report says +354.4%, source says 400.000000`. Numeric arm.
* **N3** 215.96, just **outside** 1-dp rounding → fires. **N4** 215.94, just **inside** → correctly stays GREEN.
  The arm discriminates; it is not merely always-red.
* **N6** `coarse(fix)` 0.91457 → 0.85 → numeric arm **and** the coarse-match structural check.

**NEW DEFECT — the numeric arm is SIGN-BLIND.** The comparison is `ok = abs(abs(stated) - abs(value)) <= tol`,
taking `abs()` on **both** sides. **N5** flipped `CONTROL.local-d20.iso_delta_pct` at source from **−141.95215** to
**+141.95215** — a sign inversion that reverses the claim's meaning — and the guard reported **GREEN 23/23**.
This bites precisely where it matters: P51's entire content is a **sign pattern**, and the structural
non-monotonicity check inspects only `d10 < 0 < d40`, leaving **d20's sign completely unguarded**. (Note also
that P51's `pin` passes `-ctl[...]["iso_delta_pct"]`, and that negation is a no-op under `abs()`.)
The underlying value is correct — I read it directly — so this is a defect in instrument **power**, not in the finding.

M111's own `halo_claim_guard_negctl.py` reproduces exactly as advertised (`GREEN 7/7 report defects, 3/3 source
defects caught`, exit 0), but its classifier accepts any failure line containing "at source", which would also
match the structural `bars changed at source` arm. My stricter classifier confirms the true numeric arm fired for N1–N3.

## 2. Which of ORCH's folded facts 1595–1602 are unsafe as written

| Fact | Status | Action |
| --- | --- | --- |
| 1595 | **Unsafe in one clause** | The "~49 % gradient energy" is **M86's** measurement of a half-pixel shift on one frame, not a measurement of the warp M87 applied. Splice must be disclosed. |
| 1596 | **Safe** | All three qualifiers and 72.9 % verified at script and JSON. Optionally note the 15 points confound region *and* implementation. |
| 1597 | **Safe** | Title, quotes and withdrawal scope all verbatim-correct. Exhaustive scan finds no late retraction. |
| 1598 | **UNSAFE — factual error** | "0.394 on the real occluding scene" is wrong; 0.394 is the **synthetic plant's** two-depth arm. On real data the figure is 0.821 vs 0.854 = 1.04×. Also: the 1.000 is forced by construction. |
| 1599 | **Unsafe in two clauses** | Label the mechanism **ARGUED** (M87 §3.3 does). Note 79 is a per-pixel **upper bound** (band clips near sweep ends). |
| 1600 | **Safe** | Strongest item on the list. Verified at `21-cost.json` and `16-plant.json`; M87's rule quoted verbatim. |
| 1601 | **Safe with a qualifier** | The render is shipped/aligned/gate-2, but the 9.4 % is over a 700×1100 ROI **window** of it. Add "at the damage window". |
| 1602 | **Safe, and now incomplete** | Verified by execution. Must be extended: the numeric arm, though live, is **sign-blind**. |

**Exact corrected text.**

**1595**, replace the final sentence with:
> Independently, ISO is structurally incapable of scoring sharpness — `score_iso` samples image *levels* along
> edge normals against a far-field baseline, with no gradient or Laplacian term (fact 1307). Consistent with
> that, M87's resampling control moved the metric **+0.6 %, positive** under a Catmull-Rom similarity warp
> (`36-registration-controls.json`, `resample_pct` = +0.5792). The "~49 % of gradient energy" figure is **M86's**
> (M86 P23), measured on a half-pixel shift of a single frame — the worst case — and is **not** a measurement of
> the warp M87 scored; M87's own docstring says the arm "bounds the interpolator's lowpass rather than
> reproducing arm A's exact path."

**1598**, replace the first two sentences with:
> **THE CORRECTION FIRES HARDEST WHERE THERE IS NOTHING TO FIX.** On M87's **synthetic plant**, the
> non-occluding control's treated-pixel fraction is 1.000 at every dose against 0.394 on the plant's
> **occluding** arm — but that 1.000 is **forced by the control's construction**: every treated pixel elects
> within **3** frames of `k_F`, so any delta ≥ 4 moves all of them (re-derived, V-M111). **The load-bearing
> version is on real data:** at a planted non-occluding disc in the bee image the correction moves **85.4 %**
> of treated pixels, against **82.1 %** at the bee's real occluding edge (`21-cost.json`) — it is *no more*
> selective on a genuine occlusion than on a silhouette with nothing behind it.

**1599**, replace the mechanism clause with:
> **And it is aimed wrong.** M87 §3.3 measures that near-band pixels elect frames close to the foreground's
> (median |k_elected − k_F| **32** frames near against **96** in the far field; elected-value percentile rank
> 0.675 against 0.429) and labels the causal reading — that they are *yoked* to the foreground's election —
> **ARGUED**, not measured. The consequence is measured on the bee: the treatment moves **82.1 %** of treated
> pixels, so a complement band could forbid at most **17.9 %** — **4.6× under-treatment** — and would score near
> zero by construction. On M87's synthetic plant the same comparison **inverts** (complement 60.6 % against
> treatment 39.4 %), so the argument is scene-dependent and holds on the shipped subject, not universally.
> The count `79` is a per-pixel **upper bound**: the band clips where `k_F < 39` or `k_F > 259`.

**1601**, replace "on the shipped frame" with:
> at the damage window (`866,1566 × 1050,2150`, 700 × 1100 px) of the shipped full-frame aligned gate-2 render

**1602**, append:
> V-M111 confirmed the arm is now live (plants at `blur_sigma` and the control RMSE both produced
> `report says X, source says Y`, with correct behaviour on both sides of the rounding tolerance) **and found a
> second defect in the same arm: it is sign-blind.** The comparison is `abs(abs(stated) - abs(value)) <= tol`,
> so flipping `CONTROL.local-d20.iso_delta_pct` from −141.95 to **+141.95** at source leaves the guard **GREEN
> 23/23**. P51's claim is a *sign pattern*, and the structural check inspects only d10 and d40 — d20's sign is
> unguarded. **A comparison that discards sign cannot guard a claim whose content is sign.**

**Disciplines 821–823.** 821 and 822 are safe and are strengthened by this verification — 822's rule ("plant a
defect that only arm N can see, and require arm N to be the one that reports it") is exactly the method that
found the sign-blindness, and should be extended with "…and plant it on *both sides of zero*". 823's "matched
1000× more precisely than ORCH specified" I cannot verify, as ORCH's specification is not in the corpus available
to me; the rest of 823 is confirmed.

## 3. Right for the wrong reason

1. **Item 6 (P50) — the 2.5× aggression ratio.** Numerically exact, conclusion correct, evidence tautological:
   `moved_frac = 1.000` is guaranteed by a control built so that the forbidden band swallows the background's own
   focus peak, and its own script says so. The correct citation is P30's 85.4 %-vs-82.1 % on real data.
2. **Item 6 (P50) — "the real occluding scene".** The 0.394 comparator is synthetic. Right conclusion, wrong noun,
   and ORCH folded the noun.
3. **Item 7 (P54) — "mostly misses".** True on the shipped subject and derivable from a measured 82.1 %, which
   M111 does not cite; false on the plant, which M111 does not check. Asserted as a mechanism where M87 labels it ARGUED.
4. **Item 3 (P46) — the 49 %/+0.6 % pairing.** The conclusion is right for a *better* reason than the one given:
   ISO has no gradient term at all, so no calibration of the destroyed energy is needed.
5. **Item 1 (P47) — BMF.** Right for exactly the right reason, and *understated*: M111 leads with the refutation
   of ORCH and buries the failed bar V3, which is the datum that actually blocks enabling.
6. **Item 10 (P55).** Substantively right, mildly wrong in detail — one of the seven (D4) was caught by a
   different standalone check, not by the short-circuiting literal arm.

## 4. Reproduction

Run from a detached worktree of HEAD (`experiments/V-M111/`). Scripts assume the worktree at
`C:\dev\strehl-out\V-M111`; edit the path constant at the top of each if reproducing elsewhere.

| script | what it settles |
| --- | --- |
| `rederive_bmf.py` | items 1, 9 — every BMF number and the ROI/no-op windows, from `56-bmf.json` |
| `plant_moved_frac.py` | item 6 — rebuilds M87's plant and re-derives 1.000 / 0.394326 and their forcedness |
| `final_arith.py` | items 4, 6, 7, 8 — all ratios and roundings from the JSON |
| `scan_withdrawals.py` | item 5 — exhaustive whitespace-collapsed retraction scan of M87's 5 400 lines |
| `guard_power_test.py` | item 10 — per-arm power test of M111's guard, including the sign-flip probe N5 |

Item 7's counts were verified against `crates/strehl-cli/src/merge_cmd/halo.rs` (read-only) and its unit test
`the_band_is_the_only_thing_that_vetoes_a_frame`, **not** against `halo_claim_guard.py`, whose `DELTA`/`NFRAMES`
are hardcoded in the guard itself.

---

## 5. Appendix — PIL 16-bit RGB exposure audit (added after ORCH's fleet hazard notice)

**Result: no number in this verification is exposed. Every measurement I certified was produced by a
`tifffile` reader, a `rawpy` reader, an `.npy` cache, or an in-memory synthetic array.** Confirmed by call-site
inspection of every script in the evidence chain, and by re-running the two most-cited numbers through both readers.

| my item | number | producing script | reader | verdict |
| --- | --- | --- | --- | --- |
| 1, 9 | BMF 4.428270; 9.4188 %; bars V1–V4 | `56-bmf.py` | **tifffile**, hardened with a comment citing fact P40 | safe |
| 3 | +0.5791520675613199 | `36-registration-controls.py` L55 | **tifffile**, `[:,:,1]` | safe |
| 4 | 87.852 / 84.611 | `20-local-partition.py` | rawpy + `.npy`; **no `Image.open` in the file** | safe |
| 4 | 72.933 | `42-ship-metric.py` | **tifffile**, records `"reader":"tifffile"` in its own JSON | safe |
| 6 | 1.000 / 0.394326 / RMSE ladder | `22-plant-truth.py`, `16-plant.py` | synthetic, in-memory; PIL only copies **PNGs** after `json.dump` | safe |
| 7 | 79 / 220 / 2.7848 | `halo.rs` + its unit test | no image I/O | safe |
| 8 | 0.854131 / 0.820904 | `21-cost.py` | `.npy` caches; PIL only copies **PNGs** after `json.dump` | safe |
| 8 | 33116.84 / 0.017068 | `16-plant.py` | synthetic, in-memory | safe |
| 10 | guard arms | `halo_claim_guard.py` | no image I/O | safe |

All PIL uses found in the chain are `Image.fromarray(...uint8).save(...)` (writing 8-bit PNG previews) or
`Image.open(f).save(...)` over `glob("*.png")` **after** the JSON was written. None reads a TIFF for measurement.
My own six scripts contain no TIFF read at all except the deliberate control below.

### 5.1 The hazard is already in the corpus as M87 fact P40

M87 hit this on 2026-08-24 and caught it in seven minutes. Mtimes: `40-ship-delta.py` 05:04:57 (PIL) →
`43-ship-crops.py` 05:09:58 (PIL) → **`46-ship-crops2.py` 05:11:05 (tifffile)** → every later measurement script
uses tifffile. Fact **P40**, MEASURED: *"PIL silently converts `strehl`'s 16-bit RGB TIFFs to 8-bit on read. The
same before/after pair reads `max delta = 163` through PIL and `41887 / 65535` through `tifffile`."* §16.11 adds
*"A note on an error I made and caught … I nearly reported the correction as having almost no effect."*
A scan of every report found the stale numbers **only** in those two self-confessions — no result propagates them.

### 5.2 One live defect: a stale PIL-era artifact is still committed

`experiments/M87-occlusion/data/41-ship-delta.json` holds **`"max_delta": 163`** (true **41887**) and
**`"frac": 0.13445276493222597`** (true **0.13666067504183702`, from the tifffile-produced `43-ship-crops.json`).
Its producer `src/40-ship-delta.py` still reads via `Image.open` and was never fixed; neither was
`src/43-ship-crops.py`, which was silently superseded by the higher-numbered `src/46-ship-crops2.py`.
A re-run "in numeric order" therefore regenerates the corruption in `41-ship-delta.json` and leaves it there.
**Not cited by this verification.** `43-ship-crops.json` *is* cited (for the ROI window) and *is* the tifffile
version; the window is self-validating in any case, since the paired no-op window reads exactly zero change
under both readers.

### 5.3 Re-run, not reasoned: what 8-bit quantisation actually destroys

`experiments/V-M111/reader_blast_radius.py` imports M87's **own** `56-bmf.py` functions and runs them twice on
the same shipped pair, changing only the reader.

| statistic at `R_DAMAGE` | tifffile | PIL | change |
| --- | --- | --- | --- |
| dtype / max | `uint16` / 56833 | `uint8` / 222 | 8-bit |
| **`max_delta`** | **17629** | **69** | **destroyed, 255x** |
| **`changed_frac`** | **0.124247** | **0.123738** | **-0.41 % (sub-step differences vanish)** |
| fine retention | 0.9058119414 | 0.9058911722 | +0.009 % |
| coarse retention | 0.9145749512 | 0.9145653524 | -0.001 % |
| matched blur sigma | 5.107862 px | 5.108092 px | +0.005 % |
| **BMF** | **4.428270** | **4.430201** | **+0.04 %** |
| fine band destroyed | 9.4188 % | 9.4109 % | -0.008 pts |
| bars V2 / V3 | True / False | True / False | **identical** |

**Refinement to the triage rule.** 8-bit quantisation acts as a roughly uniform, signal-independent dither. It
destroys **per-pixel extrema** (`max_delta`), **change detection and nonzero counts** (`changed_frac`), extreme-tail
percentiles, and byte-hash identity. It does **not** measurably disturb **ratios of large-N RMS aggregates**, nor
the bar verdicts derived from them — BMF moved 0.04 % and both registered bars returned the same answer.

**Do not over-generalise this.** BMF survives because the underlying signal here is *large* (max delta 17629 of
65535, 27 % of range) and is aggregated over 770 000 pixels, not because ratios are inherently safe. A correction
moving pixels by tens of counts would vanish in the aggregate too. This is a counterexample to *"every small-signal
metric dies"*, not a licence to skip a re-run. The cheap triage question is: **is my statistic an extremum, a
count, or a hash (assume destroyed), or a mean/RMS/ratio over more than about 10^4 pixels of a signal that is
large relative to 1/255 of range (probably fine — but re-run it anyway if it is cheap)?**

### 5.4 Second pass, after ORCH's correction — the narrowing dose-response on BMF

ORCH's refinements say damage scales with the file's **occupied** range, and that ratios can fail *toward a
clean null*. Both bear directly on my items 1 and 9, so I measured rather than argued
(`experiments/V-M111/narrowing_dose_response.py`, using M87's own `56-bmf.py` functions).

**The DAMAGE ROI occupies 39 333 DN of 65 535 — 60.0 % of full scale — and the correction's own signal is
17 629 DN, i.e. 44.8 % of that occupied range.** This is a high-contrast, large-signal case. Compressing it into
narrower spans and applying PIL's narrowing:

| span DN | surviving levels | fine | coarse | blur_fine | **BMF** | V2 / V3 |
| --- | --- | --- | --- | --- | --- | --- |
| **39 333 (actual)** | 31 655 | 0.90581194 | 0.91457495 | 0.20455210 | **4.4283** | True / **False** |
| 20 000 | 67 | 0.90608982 | 0.91450222 | 0.20419327 | 4.4374 | True / False |
| 8 000 | 28 | 0.90832702 | 0.91489381 | 0.20412778 | 4.4498 | True / False |
| 4 000 | 14 | 0.91115714 | 0.91705975 | 0.20576939 | 4.4280 | True / False |
| **2 100** | **9** | 0.92006111 | 0.94384491 | 0.26732918 | **3.4417** | True / False |
| 1 000 | 5 | 0.93960108 | 0.96126196 | 0.36427044 | **2.5794** | True / False |
| 400 | 3 | 0.76620573 | **1.01836** | 1.00000000 | **0.7662** | True / False |

**ORCH's warning is confirmed, and understated.** BMF is exact down to ~14 surviving levels, then collapses:
−22 % at 9 levels, −42 % at 5. The `fine` ratio climbs toward 1.0 (0.9058 → 0.9396), i.e. **the correction appears
to destroy less detail than it does** — the clean null. At 3 levels the instrument *inverts*: `coarse` exceeds 1.0
(the correction appears to **add** coarse energy), the blur bisection pins at its floor, `blur_fine` saturates at
exactly 1.0, and **BMF drops below 1 — which would have read as "the correction is worse than a blur", the exact
opposite of the finding.** The failure mode is not only toward a null; past the null it reverses the conclusion.

**The actionable predictor is surviving-level count, not "small signal".** For an RMS band ratio the breakpoint is
about **10–15 levels**. ORCH's ~2 100 DN example sits exactly on it (9 levels). My ROI is 19× above the danger span.

**Gap in the two triage questions as stated.** BMF passes both: it is not absolute, and it divides a *large*
quantity by a small one (0.906 / 0.205). Yet it is destroyed at narrow span — because the compression enters
through an **intermediate**, `blur_fine`, which *is* a small-over-large ratio (0.2046 → 0.2673 → 0.3643 → 1.0000)
and which compresses toward 1 exactly as ORCH describes. **The two questions must be applied to every intermediate
in the chain, not only to the number you publish.** A statistic can be safe by both tests and still be built on
one that is not.

**What survives regardless:** bar **V3 is False at every span**, including the pathological 3-level row. The
registered bar that actually blocks enabling `STREHL_FIX_HALO` is robust to reader, to quantisation and to
narrowing. **My bottom line is unchanged and is now better supported than when I first stated it.**

### 5.5 My own sweep reproduced ORCH's false positive — an automated list cannot settle this

I ran a return-value-aware regex sweep of all `experiments/**/*.py`, trying to separate real pixel reads from
tag-only reads. **It flagged `ORCH-drift-check/ca_radial.py` as PIXELS-VIA-PIL — the same false positive ORCH
made — because `im = Image.open(path)` is textually identical whether the next line takes `im.tag_v2` or
`np.asarray(im)`.** `ca_radial.py:60-79` in fact validates bits-per-sample, samples-per-pixel, compression and
planar config and **raises `SystemExit`** on a mismatch before reading pixels by `np.memmap`; it fails loudly,
which is the behaviour the discipline asks for.

A second false-positive class the sweep exposed: the **audit scripts written in response to the hazard notice**
(`pil16_probe.py`, `a5_pilcheck.py`, `n5_quant.py`, `s9_pilaudit.py`, `r14_pil_hazard.py`,
`v7_pil_exposure_selfcheck.py`, and my own `reader_blast_radius.py`) all call PIL **deliberately, as a control**,
and all flag as exposed. Any grep-based sweep will now light up mostly on the instruments built to measure the
problem.

**Conclusion: a grep produces candidates, never verdicts.** The classifier's own false-positive rate on the one
case with a known answer was 1/1. This is ORCH's §4 lesson, reproduced independently on my own instrument.

### 5.6 Third pass, after ORCH withdrew the triage rule

**My clearance never used the withdrawn rule and does not need re-deriving.** It rested on (a) *provenance* —
call-site inspection showing every number came from `tifffile`, `rawpy`, `.npy` or an in-memory synthetic array —
and (b) a *measured dose-response* on the actual quantiser. Neither is an argument from the form of a statistic.
I also did not model quantisation as random dither: `narrowing_dose_response.py` applies the real deterministic
narrowing `floor(clip(x,0,65535)/257)`, which is the failure mode ORCH's §"quantisation error is not noise"
warns about, avoided by construction rather than by luck.

**One clearance of mine IS weakened, and I am flagging it.** In §5.3 I cited the paired no-op window
(`1500,2100 x 3500,4300`) reading `changed_frac 0.0, max_delta 0` as evidence that the damage window is
self-validating. `changed_frac` and `max_delta` are **differencing statistics** (`a - b`), exactly the class that
books correlated quantisation error as signal. Measured: narrowing moves `changed_frac` **down**, 0.124247 →
0.123738, because sub-step differences vanish. My reading was taken on `uint16` so it is valid *as measured* —
but **a zero-change no-op control run through a narrowing reader would read zero whether or not there was a
change, and would look identical.** The control cannot distinguish "no change" from "change quantised away".
It should not be cited as a control on any narrowed data.

### 5.7 The number that does not fit — BMF's error OSCILLATES, so a single-point robustness check is worthless

Refining §5.4 to a fine grid (`experiments/V-M111/narrowing_fine_grid.py`):

| levels | 31655 | 100 | 54 | 41 | 21 | 18 | 16 | 14 | 13 | 12 | 10 | **9** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **BMF** | 4.4283 | 4.4313 | 4.4431 | 4.4460 | **4.5126** | 4.4705 | **4.3895** | 4.4280 | 4.4636 | 4.4218 | 4.4708 | **3.4417** |

The error is **not monotone in narrowing**. It oscillates within about **±2 %** between 10 and 100 levels
(high +1.9 % at 21 levels, low −0.9 % at 16), crossing the true value several times, then falls off a cliff
between 10 and 9 levels (−23 %).

**This refutes my own §5.4 reading.** There I reported BMF = 4.4280 at 14 levels against a truth of 4.4283 and
treated the near-exact agreement as evidence of robustness down to 14 levels. The fine grid shows that agreement
is **a zero crossing of an oscillation**, not a plateau: its immediate neighbours are 4.3895 (16 levels) and
4.4636 (13 levels). **A validator sampling one narrowing level could have certified "quantisation-immune to 14
levels" from a coincidence.** A single-point robustness check on a quantisation-sensitive statistic proves
nothing; the ladder is the minimum.

Revised breakpoint: **immune above ~10 levels to within ±2 %; collapses below 10.** Worth noting that V-M113
independently put its own immunity limit near **12 distinct levels** for a *position* statistic on a different
milestone and different data. Two milestones landing at 10-12 may be a real property of 8-bit narrowing or may be
coincidence across two different statistic classes; I have one statistic and cannot tell which.

### 5.8 `STREHL_FIX_HALO` has the nesting hazard ORCH found in `STREHL_FIX_CA`

Checked at ORCH's instruction, in the gate this verification is about. `crates/strehl-cli/src/merge_cmd.rs:2095`:

    let halo_fix = if halo::enabled() && opts.out.is_some() {

`opts.out` is `Option<PathBuf>` (`merge_cmd.rs:76`) — **`--out` is optional**. Three consequences:

1. **`STREHL_FIX_HALO=1` without `--out` is a completely silent no-op.** The "halo fix : ON" banner
   (L2103-2116) is *inside the same condition as the effect*, there is no `else`, and nothing warns that the
   correction was requested and skipped.
2. **Worse, and true even with `--out`:** `report(...)` (L2083) and `report_statistics(...)` (L2085) both run
   **before** pass three (L2088). **The correction therefore never changes any number `strehl` itself prints.**
   A/B-ing the gate on `strehl`'s own reported statistics returns a null *by construction, always.* This is
   deliberate — the comment at L2090-2094 says passes one and two are untouched so "the corpus's frozen numbers
   cannot move" — but the consequence for a validator is undocumented.
3. **The nesting is documented nowhere.** `halo.rs`'s module docs (L48-62) do not mention `--out`; a repo-wide
   grep for it returns only the two `opts.out.is_some()` call sites.

**Not load-bearing on my ten verdicts** — M87's §16.7 ship render used `--out` (it produced
`31-SHIP-AFTER-fixhalo.tif`) and every figure I certified was measured by re-reading that file externally with
`tifffile`. But anyone who A/B tests this gate the obvious way will measure a guaranteed null, and ORCH proposed
enabling it.

### 5.9 A third reason not to enable, which is in the shipped code and which nobody cited

`halo.rs:52-56`, verbatim:

> Treated pixels are re-elected, not re-averaged: each takes one frame's sample, so inside the yoke the gate's
> noise averaging is lost and the band is noisier than its surroundings. Every M87 measurement was made at gate 0,
> where that is also true of the uncorrected image, so the numbers above are like for like; **against a gated
> merge it is an additional, unmeasured cost.**

The shipped default is **gate 2**. So by the shipped code's own admission, the correction's noise cost **under
the configuration it would actually run in is unmeasured**. Neither M87 §16.9, nor M111, nor my §0 cited this.
It is a third independent reason not to enable, alongside failed bar V3 and the +558.4 % RMSE control.

**One factual error in that same comment:** "Every M87 measurement was made at gate 0" is **false as written**.
The numbers *in that doc block* (L34-46) are the gate-0 plant ladder and the statement is fair for them, but
M87 §16.7's shipped render used `--gate 2` and produced the 72.9 % figure, the BMF of 4.428 and the 9.4 % fine-band
result — all verified in this report. A reader of `halo.rs` would wrongly conclude no gate-2 measurement exists.

**And note the trap this sets.** Measuring that "additional, unmeasured cost" means measuring *noise* in the
treated band. The natural estimators — split-half, frame-difference, paired — are precisely the class ORCH's
§"quantisation error is not noise" shows will book correlated error as signal. **Whoever measures this must not
use a differencing estimator on narrowed data**, or they will report the band as quieter than it is and clear a
correction that is actually noisier.
