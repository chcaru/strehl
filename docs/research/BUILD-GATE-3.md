# BUILD-GATE-3 — pre-registration: what the gate-floor fix should do to ORCH's 1:1 sharpness ratio, written before it was measured

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`F1, D1, Q1, …` per rule 28.** The orchestrator allocates absolute numbers at
fold.

Every claim is labelled **MEASURED**, **DERIVED**, **ARGUED** or
**PREDICTED**. A **PREDICTED** claim has no measurement behind it *by
construction* — that is the point of the document.

**Source revision at writing:** `46738e4a`. **Nothing in section 4 has been
measured at the time of writing.** The only numbers this lane has run through
`orch_sharp1to1.py` are its two commissioning arms (§2), which describe the
instrument and contain no data from either of my arms.

**Instruments, all ORCH-owned, read and run but never edited:**
`experiments/ORCH-drift-check/orch_sharp1to1.py` (the numerator),
`experiments/ORCH-drift-check/orch_printready.py` (the gate that consumes it).

---

## 0. Why this document exists

ORCH's brief: *"Pre-register the stopping rule now, before you see a number …
What I do not want is a number arriving first and a rationalisation second."*

The failure mode being guarded against is real and this project has already
paid for it once: `overshoot_frac` was amplitude-invariant to six significant
figures and scored a planted 2 px ring as a gain, and it survived commissioning
because every arm ever run against it made the image worse. A prediction
written after the fact cannot be wrong, and a statistic that cannot be wrong is
not a measurement.

---

## 1. The numerator, as read rather than as approximated

**F1 (MEASURED, by reading the source).** `orch_sharp1to1.py::patch_gain` is
the statistic. On `PATCH = 70` px tiles inside each `CROP = 560` px site:

```
ratio(tile) = detail(master_tile).fine
              / max( detail(src_tile).fine  over REGISTERED source frames )
```

`detail().fine` is mean `|∂x| + |∂y|` at 1 px — an L1 gradient magnitude, not
an energy. The reported figure is the **median** over every tile at every
accepted site. Verdicts: `> 1.05` RECONSTRUCTION, `0.95–1.05` SELECTION,
`< 0.95` DEFECT.

**F2 (MEASURED, by reading the source).** Three exclusions are load-bearing and
none of them is a scoring rule — each removes tiles that are *not measurements*:

| exclusion | constant | what it removes |
| --- | --- | --- |
| tile below the detail floor in **both** arms | `PATCH_FLOOR = 50.0` | a ratio of two noise floors |
| source frame correlating below the gate | `CORR_MIN = 0.50` | **different content**, not soft content |
| site not textured relative to the best site | `SITE_SHARE = 0.25` | background scored against read noise |

The skipped count is printed separately and never folded into the count that
passed — the partition discipline this corpus already carries.

**F3 (MEASURED, by reading the source).** ORCH's warning that the acquittal line
read `master/best-source` while the rule was `max over registered source
frames` — *"the worst frame"* — is **scoped to `orch_printready.py`, and does
not apply to this numerator.** In `orch_printready.py` the statistics are
blotch and chroma, where **low is good**, so `max` over sources selects the
*worst* frame and the label inverted the meaning. In `orch_sharp1to1.py` the
statistic is `detail`, where **high is good**, so `max` selects the *sharpest*
frame and `best-source` is accurate. I am recording this because the warning as
stated would, if carried across, invert my reading of my own result.

---

## 2. The instrument's own commissioning, run unmodified

**F4 (MEASURED.)** `python orch_sharp1to1.py commission` — exit 0:

```
arm                                                median     expect   verdict
SELECTION   (master == sharpest source)            1.0000       ~1.0   PASS  (64 patches, 0 skipped)
DEFECT      (master blurred past every source)     0.1717       <1.0   PASS  (64 patches, 0 skipped)
RECONSTRUCT (master == unblurred latent)           3.4867       >1.0   PASS  (64 patches, 0 skipped)
COMMISSIONED: all three verdicts are reachable.
```

The RECONSTRUCT arm is present, as ORCH required. This is the property
`overshoot_frac` lacked: the statistic is known to be able to **score an
improvement as an improvement**, not merely to score damage as damage.

**F5 (MEASURED.)** `python orch_sharp1to1.py commission-reg` — exit 0. Accept
arms span `0.6582–1.0000`, reject arms `0.0052–0.0516`, margin **`0.6066`**.
`CORR_MIN = 0.50` sits inside that gap.

---

## 3. An objection to the stopping rule's tolerance, which makes it stricter

ORCH proposed: *"the fix ships if … sharpness on the selection-dominated arm
does not fall by more than the identity bias (1.0–1.4%)."*

**F6 (MEASURED + DERIVED).** **That tolerance is the wrong quantity, and it is
too loose.** The `1.0–1.4%` is V-EYES' *order-statistic inflation* — measured
by scoring the master against `n` noised copies of itself, which prices the fact
that `max` over `n` draws grows with `n`. It is the right correction for
comparing a master against its **sources**.

It is not the right correction here, because **my comparison is paired.**
Before and after, on one subject, I use:

- the same source frames,
- the same `n`,
- the same sites, the same tiles, the same registration shifts.

The denominator `max over registered sources` is therefore **literally the same
float** in both arms and cancels exactly. The order statistic cannot contribute
to a difference in which it appears identically on both sides.

The residual measurement noise on a paired Δ is the renderer's own
reproducibility, and that is **`0` by measurement**: both byte-freezes
reproduced twice at `78fed9a1` (`88712017FE31362F…`, `52517FF8AE245F23…`), and
the harness's own SELECTION arm reads exactly `1.0000`, not `1.01`.

**So the honest tolerance on a paired before/after Δ is zero, and any non-zero
fall is real.** I am proposing this against my own interest: it removes the
1.4% of cover ORCH offered me.

**D1 (ARGUED).** A zero tolerance is not a usable ship rule, so materiality has
to come from somewhere external rather than from the instrument's noise. The
only externally-anchored figure available is the head-to-head: **strehl/enfuse
sharpness `0.977`**. We are at parity and **there is no sharpness headroom** —
so the materiality threshold is not a tolerance at all. Any measurable fall on
the shipping path spends a currency we do not have, to buy noise where we are
already `1.54–1.76×` ahead.

I therefore accept ORCH's rule **with the tolerance replaced**:

> **The fix ships ON BY DEFAULT only if the shipping-arm fall is not
> measurable.** Otherwise it ships **behind a switch defaulted off**, and the
> calibration finding is documented. The switch already exists and needs no new
> surface: `STREHL_GATE_FLOOR=white` restores the constant exactly, and
> `gatefloor.rs::enabled()` is a one-line default flip.

---

## 4. THE PREDICTIONS — nothing below has been measured

The mechanism, stated so the predictions follow from it rather than the reverse:

**Measured floors at band 0 (BUILD-GATE-2 §0):** shipping/fullres `1.1787×`
white, plane `0.6225×` white. The gate is `2.0 · beta · v`. Correcting `beta`
therefore **raises** the bar on the shipping path and **lowers** it on the plane
path. A higher bar averages more pixels. Band 0 is the finest octave, which is
the band `detail().fine` is most sensitive to.

**P1 (PREDICTED) — sign, shipping arm.** Every subject's median ratio **FALLS**.
This is the primary prediction and it is the opposite of what ORCH expected when
the brief was written.

**P2 (PREDICTED) — the discriminating two-arm test.** On the **plane** arm
(`STREHL_FULLRES_GATHER=0`) the *same code change* makes the ratio **RISE**,
because there the correction removes averaging (`averaged` 97.2 → 60.0 on
`foam`). **A mechanism-free explanation — "the new code just softens things" —
predicts both arms fall.** This is the test that separates my model from a bug.

**P3 (PREDICTED) — magnitude, and it is regime-split.** Because the sources are
unchanged, `Δratio/ratio = Δ(master fine detail)/(master fine detail)` exactly.
My Q1 acuity instrument measured the master's sharp-tile high-pass falling
`19.9–36.1%` on the shipping arm from white → measured. `detail().fine` is a
*broader* high-pass than that probe, so the same change should read **diluted**:

| regime | subjects | predicted relative fall | point estimate |
| --- | --- | ---: | ---: |
| averaging-dominated | `flower-bud-alone-cpl`, `119MSDCF`, `109MSDCF`, `coffee-bubbles` | **10–25%** | **16%** |
| selection-dominated | `bee-1-cpl` (`avg_index` 0.06) | **under 3%** | **~1%** |

The regime split is not a hedge, it is the mechanism: only pixels *near the
gate* can flip, and on `bee-1-cpl` only ~6% of sites are averaged at all, so
there is almost nothing available to flip. **I would count anything outside
`[5%, 35%]` on the averaging arm as the mechanism being wrong**, not as a
noisy measurement.

**P4 (PREDICTED) — ordering.** The size of the fall is monotone in each
subject's Δ`averaged`(band 0). `bee-1-cpl` smallest, `flower-bud-alone-cpl`
largest. Ordering is a stronger test than any single level because it cannot be
satisfied by an overall scale error.

**P5 (PREDICTED) — the noise arm, which is ORCH's item 3 and my Q1.** Flat-region
high-pass noise on the shipping arm **falls 15–35%**. And the sharper
prediction: **noise and sharpness move together to within 10 percentage
points** — i.e. the gate at band 0 is a **non-selective attenuator**, which is
BUILD-GATE-2 §4's finding (`foam` −22.5%/−23.2%, `couch-fibers-cpl`
−35.7%/−36.1%, CNR −1.0% and −0.6%).

> **If noise improves substantially MORE than sharpness degrades, my Q1 answer
> is wrong, the fix is a genuine quality win, and BUILD-GATE-2 §4 must be
> retracted.** That is the outcome I would most like and least expect.

**P6 (PREDICTED, and it holds by construction) — the placebo.** The
align-refused subject moves **exactly `0.000`**. An align-refused frame never
reaches `measure`, so its correction is identically `1.0`. This is already
proven byte-identical in BUILD-GATE-2 §6; if it moves, the correction is being
applied where no warp exists and the patch is wrong.

**D2 (a commitment).** I will not tune `beta` to move any ratio. `beta` is a
measured physical quantity and tuning it to hit a metric destroys the
measurement. **Nor will I rescale the `2.0` to undo the correction** — fact 631
already settled that: `t/k` is the right way to *price* a miscalibration and the
wrong way to *undo* one, because rescaling the gate does not reproduce a
different operator's decisions. The only legitimate lever is the ship/no-ship
switch in §3.

---

## 5. Q2 is now visible, and it reframes the whole decision

**D3 (ARGUED).** The `2.0` multiplier has never been justified by any
measurement in this corpus. Until tonight it was multiplied by a `beta` that was
wrong by `1.18×` on the shipping path — which means **the product's
sharpness/noise operating point has been set by a calibration error, not by a
decision.** Nobody ever chose it.

That is why "does the fix make the picture better?" is the wrong question to ask
of this patch. The patch restores the gate to the value the banner always
claimed it had. It does not, and cannot, choose where the operating point
*should* be. Those are two decisions that have been conflated, and correcting
the calibration is what makes the second one visible for the first time.

---

## 6. What will be run

**F7 (MEASURED).** Bracket depths: `bee-1-cpl` **299**, `flower-bud-alone-cpl`
**205**, `119MSDCF` **33**, `109MSDCF` **22**, `coffee-bubbles` **19**.

**F8 (DERIVED).** `orch_sharp1to1.py::main` holds every developed frame resident
(`srcs.append((name, luma(s), s))`) — roughly 336 MB per 24 MP frame. At
complete depth that is **~6.4 GB for `coffee-bubbles` and ~100 GB for
`bee-1-cpl`**. So:

- **`coffee-bubbles`, `109MSDCF`, `119MSDCF` run at complete depth through
  ORCH's script unmodified.** No new code, no new risk.
- **`bee-1-cpl` and `flower-bud-alone-cpl` need a streaming driver** that
  `import`s `luma`, `detail`, `register`, `best_site`, `patch_gain` and the
  constants **from `orch_sharp1to1` itself** — the numerator is reused, never
  reimplemented — and keeps only a per-tile running `max`, which is
  mathematically identical to `patch_gain`'s `max` over a resident list.

**D4 (a commitment).** That driver is commissioned before it is believed: it
must reproduce the unmodified script's median **to the printed digit** on a
shallow subject at the same `nsrc`. If it does not, the deep subjects are
reported as NOT MEASURED rather than measured by an uncommissioned instrument.

**Arms:** `{white, measured} × {fullres, plane}` per subject, at complete depth,
plus the align-refused null. Outputs under `C:\dev\strehl-out\BUILD-GATE\`;
`D:\personal\macro\` is read-only.

**`crates/` declaration, per ORCH's sequencing request.** The only file under
`crates/` this lane will touch for this work is
**`crates/strehl-cli/src/merge_cmd/gatefloor.rs`** — and only if §3's rule sends
the fix behind a default-off switch, in which case the change is the one-line
default in `enabled()`. I will re-read `git --no-pager status --porcelain
crates/` immediately before writing and will not open `defect_map.rs` or
`merge_cmd.rs`.
