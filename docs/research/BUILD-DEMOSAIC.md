# BUILD-DEMOSAIC — is the gather flip's chroma excess restored or created? A ground-truth answer, and a defect the statistic cannot see

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`D1, D2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `d2ee3831` (`V-REVIEW halo: gallery Lanczos
provably manufactures edge rims; box does not`). One commit from another lane
landed underneath this work while it ran — `eba1c6e1`, `V-GATHER: the chroma
cost is not the demosaic, it is a stale noise gate` — and it reaches the same
verdict by three independent routes. §7 states what that does and does not do to
this file's contribution.

**Read-only inputs, never written to:** `D:\personal\macro\wrapped-text-1`,
`tweezers-cpl`, `lavendar-cpl`. All outputs under
`C:\dev\strehl-out\BUILD-DEMOSAIC\`. Verification binary built in a detached
worktree pinned at `d2ee3831`.

---

## 0. The commission

> Is the chroma excess **restored** or **created**? … Settle this first and tell
> me the answer before building the fix. If it is restored, say so and stop — I
> would rather lose the lane than "fix" honest signal.

With the method fixed in advance: a **synthetic scene with known ground truth**,
not a difference between two arms neither of which is truth, because §111
records three real-image detectors that died on exactly this question.

---

## 1. The answer, up front

**RESTORED.** The chroma excess V-GATHER measured is not manufactured by the
double demosaic. **I did not build the fix.**

But the honest answer has a second half that the binary question does not have a
slot for, and it is the part worth reading:

> **The double demosaic is not innocent. It is invisible.**

It *does* create real chroma error against a known truth — **+128 to +455 DN
rms**, on every scene tested, including scenes whose true `R−B` is *exactly
zero everywhere*. What it does **not** do is raise the `R−B` high-pass statistic
that V-GATHER used. It **lowers** it, by **9.3% to 16.8%**, and it lowers it by
a mechanism I measured directly: the second demosaic **correlates R and B noise**
through the reconstructed green they share, and `var(R−B)` falls when `ρ` rises
whatever the per-channel error does.

So the statistic reads this defect as an *improvement*. That is the finding.

| question | answer | route |
|---|---|---|
| Does the double demosaic cause V-GATHER's +25.2…48.6% chroma excess? | **No.** It contributes ×0.70–0.89. | D3, D4, D6 |
| Is the excess restored? | **Yes** — it is the luma-band restoration passing into `R−B`. | D5 |
| Is the double demosaic harmless? | **No.** +128…+455 DN vs truth. | D2 |
| Would removing it improve V-GATHER's statistic? | **No — it would make it ~29% worse.** | D7 |

That last row is the trap. Anyone who fixes the double demosaic while watching
the `R−B` high-pass will measure themselves getting worse and revert a correct
change.

---

## 2. The instrument

`crates/strehl-cli/examples/build-demosaic-truth.rs`. It `#[path]`-includes the
real `align_cmd.rs` (strehl-cli has no lib target) and calls
`warp_frame_in_place_plane` and `warp_frame_in_place_fullres` — **the shipping
functions**, not a port.

An analytic `Scene` is a sum of band-limited waves evaluable at any *real*
coordinate, so truth exists at the sub-pixel positions the warp actually samples.
It is mosaiced into a synthetic `Frame`, pushed through the real warp, demosaiced,
and compared against `scene.rgb()` evaluated at the exact same mapped coordinate.

Arms: `nowarp`, `plane`, `fullres` (shipping), `oracle` (identical gather, but the
warp-time planes come from **truth** — isolates the warp-time demosaic and
nothing else), `oracle±100/300` (calibrated planted defect), `bilin`, and `once`
(demosaic once, warp in RGB — the candidate fix, as an upper bound on the prize).

### 2.1 Commissioning — all pass

```
  C0 CFA parity          : rggb() agrees with cfa_site_channel at all four sites   PASS
  C0 CA isolation        : profile_for_capture_env declines the synthetic frame     PASS
  C1 identity null       : fullres at IDENTITY = nowarp floor, 492.4752 DN both            PASS
  C2 planted defect  flat       : oracle     0.50 -> +100 DN    36.47 -> +300 DN   109.39   PASS
  C2 planted defect  achromatic : oracle   319.40 -> +100 DN   321.48 -> +300 DN   337.62   PASS
  C2 planted defect  coloured   : oracle   403.25 -> +100 DN   404.89 -> +300 DN   417.82   PASS
  C2 planted defect  vivid      : oracle   804.52 -> +100 DN   805.35 -> +300 DN   811.92   PASS
  C3 planted improve flat       : oracle     0.50 < shipping fullres   281.05            PASS
  C3 planted improve achromatic : oracle   319.40 < shipping fullres   447.66            PASS
  C3 planted improve coloured   : oracle   403.25 < shipping fullres   595.28            PASS
  C3 planted improve vivid      : oracle   804.52 < shipping fullres  1259.49            PASS
  C4 healthy control        : vivid TRUE chroma HP 1511.6 DN is 3.9x the achromatic
                               scene's MANUFACTURED HP 385.0 DN, and the metric still
                               ranks the oracle best on it (804.5 DN)             PASS
  C5 harness fidelity       : re-gather == warp_frame_in_place_fullres to the byte
                              (checked inside every run above; a mismatch aborts)  PASS
```

C4 is §111.3's healthy control: a scene carrying **3.9× more real chroma than the
achromatic scene's entire manufactured signal**, which the metric must not
convict. It does not.

### 2.2 The first planted defect failed commissioning, and was right to

**D1 (MEASURED).** My first planted defect was a *bilinear* warp-time demosaic.
It failed C2 by reading as an **improvement** — and it is one, on this metric:

| scene | shipping Malvar | bilinear |
|---|---|---|
| achromatic | 447.66 | **349.99** |
| coloured | 595.28 | **495.54** |
| vivid | 1259.49 | **1109.17** |

Bilinear is a low-pass, and on a metric that rewards closeness to a smooth truth,
smoothing and correctness are indistinguishable. This is §110.6's rule biting in
its own right: *a planted defect that reads as an improvement is telling you your
defect is not a defect.* It was replaced with a calibrated chroma injection
(±d DN alternating per quad = 0.25 cyc/px; note `(−1)^(x+y)` is **constant on
both R and B sites** and would be annihilated by the high pass).

The bilinear result stands as a finding: **at the warp-time stage only**, the
shipping Malvar is worse than bilinear against truth on all three detailed
scenes. That is not an argument to change the final demosaic — it is an argument
that the warp-time one should not exist.

---

## 3. Ground truth: the double demosaic creates error (D2)

**D2 (MEASURED).** `fullres − oracle` is the warp-time demosaic's own
contribution, with the gather, resampler, geometry and final demosaic all held
identical. Chroma error vs truth, DN rms, 451,584 interior px:

| scene | nowarp | plane | **fullres** | **oracle** | fullres − oracle | once |
|---|---|---|---|---|---|---|
| flat + noise sd 400 | 356.26 | 303.85 | **281.05** | **0.50** | **+280.55** | 331.17 |
| achromatic (true R−B ≡ 0) | 492.48 | 441.92 | **447.66** | **319.40** | **+128.26** | 464.08 |
| coloured | 549.17 | 529.30 | **595.28** | **403.25** | **+192.03** | 520.73 |
| vivid | 879.86 | 979.33 | **1259.49** | **804.52** | **+454.97** | 847.07 |

Positive on every scene, and it **grows with how much real chroma the scene
carries**. On the achromatic scene the true `R−B` is *exactly zero at every
pixel*, so all 447.66 DN is manufactured; 128.26 DN of it is the second demosaic.

**This is a real defect and it is on the shipping path.** It is simply not the
one V-GATHER's statistic was pointing at.

---

## 4. The same statistic, at the same stage, moves the other way (D3)

**D3 (MEASURED).** V-GATHER's statistic D — rms of the 7×7-box high-pass of
`R−B`, pooled over the flattest quantile of 128 px tiles — applied to the
single-frame warp stage on **real sensor data**, three subjects, both colour
spaces, four flatness quantiles:

```
  window 1536x1536 at (1024, 1024) of DSC00001.ARW   ISO 100   black 512     [wrapped-text-1]
  q=0.05  chroma HP  nowarp    18.69   plane    16.00   fullres    14.52   plane->fullres   -9.3%
  q=0.1   chroma HP  nowarp    18.52   plane    15.76   fullres    13.94   plane->fullres  -11.5%
  q=0.25  chroma HP  nowarp    18.11   plane    14.78   fullres    13.00   plane->fullres  -12.0%
  q=1     chroma HP  nowarp    14.96   plane    12.02   fullres    10.56   plane->fullres  -12.2%
```

`tweezers-cpl` −14.2…−16.3%; `lavendar-cpl` −1.5…−11.6%; linear sRGB −1.5…−16.8%.
**Never once positive**, in any of the 48 real-data cells measured.

**D3a (MEASURED).** Nor is the sign a property of one warp. Nine warps spanning
translation 0.06→3.9 plane px, scale 0→2.3%, rotation 0→0.004 rad, on
`wrapped-text-1`, q=0.10: `−0.6, −11.8, −3.5, −13.7, −2.4, −11.2, −7.5, −9.6,
−7.9 %`. All negative; the only near-null is the 0.06 px warp, which is nearly
the identity and should be null.

---

## 5. The decomposition, and why it is not a coincidence (D4, D5)

I rendered both arms myself with a binary built in a detached worktree pinned at
`d2ee3831`, `--limit 20 --linear-srgb --demosaic`, `STREHL_FIX_CA=off` — V-GATHER's
exact configuration — and applied **V-GATHER's own `chroma_real.py` code**:

```
wt1: g0 (4688, 7032, 3) float64  g1 (4688, 7032, 3)
  max |g1-g0| = 1338.000 DN   mean |g1-g0| = 37.7076 DN
       q     nt |    luma g0    luma g1    ratio |     chr g0     chr g1    ratio
    0.02     39 |    36.2373    59.9080   1.6532 |    48.4110    62.0099   1.2809
    0.05     98 |    36.4059    59.6280   1.6379 |    48.6475    61.7448   1.2692
    0.10    195 |    35.9421    58.5518   1.6291 |    48.1124    60.6094   1.2597
    0.25    486 |    38.8956    59.5824   1.5319 |    53.4442    62.8012   1.1751
    0.50    972 |    66.3905    83.4939   1.2576 |    85.4818    81.9624   0.9588
    1.00   1944 |    68.1405    83.5988   1.2269 |    85.3495    79.6468   0.9332
```

**D4 (MEASURED).** V-GATHER's number reproduces: chroma ×1.2597 at q=0.10
(+26.0%, their reported low end was +25.2%), luma ×1.6291 (inside their
×1.267–1.870 band). *The excess is real. I am not disputing the observation.*

**D5 (MEASURED, then DERIVED).** But **chroma rises *less* than luma**, and the
ratio of the two ratios is extraordinarily stable:

| q | 0.02 | 0.05 | 0.10 | 0.25 | 0.50 | 1.00 |
|---|---|---|---|---|---|---|
| chroma ratio / luma ratio | 0.7748 | 0.7749 | **0.7733** | 0.7671 | 0.7624 | 0.7606 |

0.760–0.775 across a 50× range of tile counts. A chroma-*specific* defect would
push this **above** 1. It sits below.

And it sits below at **exactly the value the single-frame warp stage predicts**.
Same subject, linear sRGB, no merge, no render, my own instrument:

| q | 0.05 | 0.10 | 0.25 | 1.00 |
|---|---|---|---|---|
| chroma/luma, single frame | 0.8188 | **0.8039** | 0.7363 | 0.7117 |

Master 0.7733 against single-frame 0.8039 at the matched quantile — and the
master value lies inside the single-frame band at every quantile. Two entirely
independent instruments (one frame with no merge; twenty frames through the
shipping binary) agree on a quantity neither was built to produce.

**The decomposition is therefore:**

```
observed chroma excess  =  broadband restoration  ×  double-demosaic chroma suppression
              ×1.26     =        ×1.63            ×            ×0.77
```

The chroma excess is **entirely accounted for by the luma-band restoration**.
The double demosaic is the only term holding it *down*.

---

## 6. The mechanism, measured directly rather than argued (D6)

The proposed mechanism: Malvar interpolates colour *differences* against
reconstructed green, so R and B estimates at non-native sites share a
green-derived component. That **correlates** R and B error, and

```
var(R−B) = var R + var B − 2 ρ sqrt(var R · var B)
```

makes any suppression of `R−B` at fixed per-channel variance a statement about
`ρ` and nothing else. So I measured `ρ` rather than inferring it.

**D6 (MEASURED).** Pearson ρ of the high-passed R and B planes, same tiles,
camera-native, `wrapped-text-1`:

| q | nowarp | plane | **fullres** (2 demosaics) | **once** (1 demosaic) |
|---|---|---|---|---|
| 0.05 | +0.6446 | +0.6034 | **+0.6938** | +0.6248 |
| 0.10 | +0.6490 | +0.6087 | **+0.7121** | +0.6272 |
| 0.25 | +0.6517 | +0.6003 | **+0.7479** | +0.6354 |
| 1.00 | +0.6508 | +0.5961 | **+0.7598** | +0.6356 |

The second demosaic raises ρ from **0.60 to 0.69–0.76**. `once` — *the same
gather, the same resampler, the same bandwidth, one demosaic instead of two* —
does **not** raise it (0.625–0.636, i.e. back at the unwarped frame's level).
`tweezers-cpl` is stronger still: plane +0.592 → fullres **+0.776**, once +0.629.

The mechanism is confirmed by the arm that removes it.

---

## 7. The fix would make the statistic worse (D7)

**D7 (MEASURED).** `once`'s chroma/luma ratio relative to `plane`:

| q | 0.05 | 0.10 | 0.25 | 1.00 |
|---|---|---|---|---|
| `once`, wrapped-text-1 | 0.9900 | **0.9992** | 0.9646 | 0.9539 |
| `once`, tweezers-cpl | 0.9709 | 0.9670 | 0.9899 | 0.9506 |
| `once`, lavendar-cpl | 0.9824 | 0.9633 | 0.9781 | 0.9538 |

With one demosaic the chroma statistic tracks the luma statistic to within 5%.
At matched luma restoration (`once` luma 15.27 vs `fullres` 15.60 at q=0.10),
`once` carries chroma **27.09 vs fullres 22.27** — 22% *higher*.

**DERIVED:** a correct fix that removes the second interpolation would move the
master chroma ratio from ×1.26 to roughly ×1.63, i.e. **~29% worse** on the
statistic that started this investigation. That is not a reason not to fix it. It
is a reason not to *steer* by that statistic.

---

## 8. Independent corroboration, and what this file adds

`eba1c6e1` landed mid-run and exonerates the double demosaic three ways: an exact
identity-warp no-op; a ported simulation reproducing the luma excess (×1.16–1.86)
but refusing the chroma excess (**new/old = 0.80–1.03**); and a `--gate 0` render
showing the gather *reducing* chroma noise. It locates the real cause: **a stale
noise gate in the pyramid merge** that was not re-derived for the gather order.

Their 0.80–1.03 and my −9.3…−16.8% (= ×0.832–0.907) are the same measurement
taken by different means, one by simulation and one by the shipping functions.
**Two lanes, two methods, same answer: the excess is not the demosaic.**

What this file adds that a differential method structurally cannot:

1. **Ground truth (D2).** Every arm in `eba1c6e1` is compared to another arm. That
   can show the double demosaic is not the *source of a difference*; it cannot
   show whether it is *right*. Against truth it is not: **+128 to +455 DN**.
   "EXONERATED" is therefore too strong. Exonerated of the chroma-HP excess, yes.
   Innocent, no.
2. **Why the statistic is blind to it (D6).** ρ rises 0.60 → 0.76 under the second
   demosaic and does not rise without it.
3. **The steering hazard (D7).** Removing the defect makes the statistic worse.

---

## 9. What I did not find

**The owner's magenta pixels are not explained by this work, and this instrument
argues against the double demosaic being their cause.** Worst-pixel chroma error
on the *achromatic* scene — the brushed-steel / white-trichome regime — is
**lowest** in the shipping `fullres` arm:

| scene | nowarp | plane | fullres | oracle | once |
|---|---|---|---|---|---|
| achromatic, chroma max | 1585.1 | 1430.6 | **1214.7** | 1364.5 | 1489.9 |
| vivid, chroma max | 3146.0 | 3288.7 | **4319.1** | 2915.8 | 2944.9 |

On achromatic material `fullres` has the smallest worst-pixel excursion of any
arm. On vivid material it has the largest (+31% over plane, +48% over oracle).
So the double demosaic hurts most where chroma is *real*, which is the opposite
of the reported symptom. **I did not identify the magenta mechanism.** Per §111,
I am not building a fourth detector for it on the way past.

Also not done, and deliberately: **I did not build the fix.** The brief said to
settle restored-vs-created and stop if restored. It is restored.

---

## 10. An instrument bug I caught, because the numbers moved when they should not

**D8 (MEASURED, method).** Adding a fourth arm (`once`) to the flat-tile
statistic changed the **`plane`** arm's reading from **15.92 to 41.68 DN** — on
pixels that had not changed — and collapsed all four quantiles to a single value.

Cause: V-GATHER's `measure()` selects tiles on `(l0+l1)/2`, the mean of the arms
being compared. **The site list therefore moves when the arms move**, and adding
an arm silently re-selects the pixels. In `chroma_real.py`'s own two-arm use this
is benign; it is not a safe generalisation.

Fixed by selecting tiles on **one fixed reference arm** (`nowarp`) for every
comparison, and by excluding the outer 128 px tile ring, where the gather reads
off-frame and `once_rgb` reports NaN rather than inventing an edge-clamped value.
Every number in §§4–7 is post-fix. **This is the only reason the §4 figures differ
slightly from an earlier draft of the same table.**

---

## 11. Facts, disciplines and questions

**Facts:** D1–D8 above.

**Disciplines proposed:**

- **DD1.** *A metric that can be improved by smoothing cannot commission a
  smoothing defect.* Plant a defect that is **not** a low-pass, or the planted
  defect will read as a planted improvement (D1).
- **DD2.** *A defect that correlates two channels is invisible to a metric on
  their difference.* Before trusting a difference statistic, measure the
  correlation it is implicitly holding fixed (D6).
- **DD3.** *Pool-selection must not depend on the arms being compared.* If the
  tile/pixel selection is derived from the arms, adding or changing an arm
  silently re-selects the sample (D8).
- **DD4.** *Exoneration by differential methods is exoneration of an attribution,
  not a finding of innocence.* Only truth can say whether a stage is right (D2).

**Questions left open:**

- **DQ1.** What causes the isolated magenta pixels on achromatic subjects? Not
  settled here, and §9's table argues it is not the double demosaic.
- **DQ2.** Should the warp-time demosaic be removed anyway, on D2's ground-truth
  cost, knowing it will move V-GATHER's statistic the wrong way and break the
  byte-freezes? **Orchestrator's call, not mine.** `once` is better than
  `fullres` on the coloured (+75 DN) and vivid (+412 DN) scenes but *worse* on
  flat+noise (−50 DN) and achromatic (−16 DN) — the obvious fix is not a free win.
- **DQ3.** At the warp-time stage only, bilinear beats the shipping Malvar
  against truth on all three detailed scenes (D1). Worth pursuing only if DQ2 is
  answered "remove it".

---

## 12. Files

**Instrument**

- `crates/strehl-cli/examples/build-demosaic-truth.rs` — the whole lane.
  `#[path]`-includes `align_cmd.rs`; analytic `Scene`; `mosaic`/`wb_mosaic`;
  `oracle_planes`/`planted_chroma`/`once_rgb`; `gather_from_planes` (byte-checked
  against the shipping gather, C5); `highpass` (r=3, V-GATHER's); `flat_tile_chroma`
  (chroma HP, luma HP, ρ, fixed selection reference); `run_scene`; `run_real`.

**Analysis**

- `experiments/BUILD-DEMOSAIC/src/01-repro-vgather.py` — V-GATHER's statistic D,
  importing V-GATHER's own `hp`/`boxblur`, on masters I rendered myself.
- `experiments/BUILD-DEMOSAIC/out/03-truth.log` — the run quoted throughout.

**Not modified:** no `crates/` shipping file, and
`crates/strehl-cli/tests/byte-freezes.tsv` is untouched. The default render is
bit-for-bit unchanged by this lane, because this lane changed no shipping code.
