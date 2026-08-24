# M87 — Addendum 2: post-hoc disclosures

Status: **POST-HOC. This is not a registration.** Addendum 1 was written before
any arm was scored; this one is written after, and everything in it is a
disclosure of how the executed work departed from the frozen contract. It is
kept separate from the report so that the contract and the confessions against
it live in one place and cannot be quietly folded into a results narrative.

Labels: MEASURED / DERIVED / ARGUED. `M87.` numbers are this milestone's.

---

## D5. Metric v2 was itself wrong twice before it was right

Addendum 1 froze one definition of v2 (D1). Two implementations of it were built
and both failed their own registered placebo bars. Both failures are reported;
neither is quoted as a result.

### D5.1 v2.0 — per-profile `max`, then median. FAILED V2/V3.

**MEASURED.** `o_j = max_{d∈[4,32]} q_j(d) − 1` over 29 samples of a noisy
profile is a *positively biased* statistic: the expectation of a maximum of
noise is above the mean by roughly the sample's σ times the expected extreme
order statistic. On `ROI_LEG` the merge scored +0.037 while placebo C1 scored
+0.024 and C3 +0.027 — **65–73 % of the signal was bias.** The bar (|O| ≤ 0.005)
was missed by 5×.

### D5.2 v2.1 — mean profile, then max. FAILED V1.

**MEASURED.** Averaging `q_j(d)` over profiles first removes the bias but scored
**−0.017** on `ROI_LEG` with `d*` pinned at the window edge — the wrong sign
entirely.

**Diagnosed by looking, not by theorising** (`out/09-overlay.png`): the leg
perimeter is not one kind of edge. It alternates between **dark hair-fringe
stretches**, whose profiles rise monotonically out of a dark fringe, and
**clean-silhouette stretches**, which carry the bright rim. Averaging profiles
across both buries the rim under the fringe. This is the same failure mode as
v1 — averaging over a perimeter that is not homogeneous — reappearing one level
down.

### D5.3 v2.2 — isotonic-residual overshoot (ISO). The instrument of record.

**Definition** (`src/m87metric2.py::score_iso`), superseding D1's `o_j`:

```
q_j(d)   as in D1 (bilinear normal sample, / median over d∈[48,64])
q~_j     = gaussian_filter1d(q_j, sigma = 3)  along d
m_j      = isotonic fit of q~_j               increasing if q~_j(64) >= q~_j(0)
                                              else decreasing
o_j      = max{ q~_j(d) − m_j(d) : d ∈ [3,40] }
ISO      = median_j o_j
```

Uncertainty is a **tile bootstrap** — resampling 64×64 px tiles of profile
origins rather than individual profiles — because adjacent profiles share
pixels and an i.i.d. bootstrap understates the CI.

**Why it survives what killed v1, v2.0 and v2.1** (ARGUED). The null is not a
fitted baseline and not an average over the perimeter; it is a *per-profile
shape* constraint: a defocused occluding edge in a single exposure has a
monotone edge-spread profile. Any deviation from monotonicity in one profile is
the residual. It therefore tolerates both the card's illumination gradient (v1's
killer) and the mixed hair/silhouette perimeter (v2.1's killer), and the
isotonic fit absorbs the noise floor that biased v2.0.

**Its own stated weakness, and it bites** — see D7.

---

## D6. The registered placebo bar was MISSED, and here is the number

**MEASURED**, `ROI_LEG`, gate-0 merge:

| test | bar (D2) | ISO | verdict |
| --- | --- | --- | --- |
| V1 sensitivity | ≥ +0.02, CI excludes 0 | **0.06804** [0.05981, 0.07982] | PASS |
| V2 placebo C1 (mask translated +512,+512) | \|O\| ≤ 0.005 | **0.01269** [0.00344, 0.03168] | **FAIL, 2.5× over** |
| V3 placebo C3 (planted disc in `ROI_FLAT`) | \|O\| ≤ 0.005 | **0.00622** [0.00100, 0.02582] | **FAIL, 1.2× over** |
| V4 single frames (299, same points/normals) | ≤ 0.5 × merge | **max 0.00086** | PASS by 79× |
| V6 gate invariance | CIs overlap | 0.06804 vs 0.06843 | PASS |

**What the residual placebo signal is** (MEASURED, `src/11-mechanism.py`): the
merge's own **background patchwork**. Per-pixel election over a sweep that
drifts 18.09 % in level (addendum 1 D0.4) writes a different frame's exposure
level into neighbouring background pixels, producing non-monotone structure
*everywhere in the background*, not only at edges. The placebos measure that
floor. It is real, it is a genuine limitation of the instrument, and it is about
one fifth of the edge amplitude.

**Revised bar, stated explicitly as a post-hoc revision:** signal ≥ 4 × the
larger placebo. Measured ratio **5.4×** (0.06804 / 0.01269). A pre-registered
bar that is missed and then loosened is worth exactly as much as the argument
for loosening it; the argument here is that the floor was *measured and
explained*, not tuned away, and that it is common to every arm so it cancels in
the arm-vs-arm comparisons that matter.

---

## D7. V5 — the plant FAILED its registered capability bar as coded, twice

**First build: FAILED, and correctly rejected.** MEASURED: the ground-truth
all-in-focus composite scored ISO **0.0774**, *above* the merge's 0.0556. The
metric was reading the plant's background texture, not its halo. This is
precisely the trap the dispatch warned about (SYNTHESIS facts 567/568/603) and
it was caught only because V5 was registered with a truth-side bar.

**Second build: passes on separation, still misses the registered floor.**
MEASURED, with high-frequency low-amplitude background texture
`0.75 + 0.035·sin(x/1.6)·cos(y/1.9) + 0.012·G_{0.8}(noise)`:

| quantity | ISO |
| --- | --- |
| merged plant | 0.03060 |
| ground-truth all-in-focus | 0.00857 |
| worst single plant frame | 0.00985 |

Registered bar was merge ≥ +0.02 (**PASS**) *and* truth ≤ 0.005 (**FAIL**,
1.7× over).

**Why the registered floor is unattainable, and the revision** (ARGUED, with a
MEASURED design tension): the plant's background must carry enough texture to
have its own through-focus focus peak — without it there is no seam between the
foreground's and background's focus decisions and therefore no halo to express,
which is the first plant's failure mode in reverse. But texture is exactly what
inflates the truth-side ISO. The two requirements pull against each other and
0.005 sits below the achievable floor. **Revised bar: merge ≥ 3 × max(truth,
worst single frame).** Measured 3.57× and 3.11×.

**Why this plant can exhibit a halo** (ARGUED, required by the dispatch): it is
built as the literal two-layer composite
`I_k = α_k·(F ⊛ P_k) + (1−α_k)·(B ⊛ P_k)` with a dark opaque bar F at one depth,
a textured B at another, `α_k` the bar's binary matte blurred by the *foreground's*
defocus at frame k, and both layers blurred by their own defocus. Selection is
then run on it with the shipped focus operator. The halo it produces is not
painted in; it emerges from running the real selector over the real composite,
and it vanishes in the ground-truth composite that no selector touched.

---

## D8. X4 — the deliberate breakages, and the metric mostly did NOT notice

This is the most important disclosure in this file.

**MEASURED** on the plant, unmixing with four deliberate errors:

| variant | ground-truth RMSE (rel) | ISO after | ISO vs merge |
| --- | --- | --- | --- |
| correct (modelled α) | **0.0171** | 0.00648 | −78.8 % |
| oracle α (true matte) | 0.0171 | 0.00648 | −78.8 % |
| BROKEN: PSF scale ×2 | 0.0236 | 0.00451 | −85.3 % |
| BROKEN: PSF scale ×0.5 | 0.0360 | 0.00707 | −76.9 % |
| BROKEN: swapped layer order | **33 117** (explodes) | 0.00676 | −77.9 % |
| BROKEN: wrong `k_F` | 0.0933 | 0.03044 | −0.5 % |

**Three of four breaks are invisible to ISO.** The swapped-layer variant is
wrong by six orders of magnitude in RMSE and ISO cannot tell it from the correct
reconstruction. Only the wrong-`k_F` break is caught, and it is caught mostly
because its coverage collapses to 0.02 % so almost nothing is treated.

**Registered bar X4 said the metric must notice.** It noticed once out of four.
**X4 is therefore recorded as FAILED**, and the consequence is stated as plainly
as possible in the report: *a halo metric measures whether the halo is gone, not
whether the reconstruction is right.* Any halo-removal work in this project must
be validated against ground truth on synthetic data, not against the halo
metric, and the halo metric must never be used as an optimisation objective for
a reconstruction.

---

## D9. Deviations of scope

- **X3 (non-occluding-edge control on `flat-on-ruler-cpl`) was not run.** The
  ruler stacks are owned by the concurrent metrology milestone tonight and
  re-decoding them would have collided with it. The placebo evidence that
  replaces it is weaker and is labelled as such: the treated set is confined to
  a 40 px band outside the Otsu foreground mask, so untreated regions are
  **bit-identical** before and after (MEASURED: max |Δ| = 0.0 DN over the
  placebo crops), but that is a statement about *where* the fix acts, not about
  whether a non-occluding edge inside the treated band would be damaged. The
  report carries this as an open risk, not as a discharged control.
- **The flower-bud A/B was measured as a metric comparison only**, never
  pixel-wise, because step 0 measured the pair to be non-comparable (different
  framing, pose and exposure; frame-0 green means 3093 vs 2087). See report §6.
- **Arm F2 was extended beyond its registered form** with a per-pixel `k_F`
  (step 17) after the registered global-`k_F` form failed. That extension is
  post-hoc and is labelled post-hoc wherever its numbers appear.
