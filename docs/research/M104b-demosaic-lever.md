# M104b — the demosaic lever: what a win would have to look like

**Milestone:** M104b (suffixed stem, following the `M76b` precedent, to avoid a
third collision on a numeric stem — see discipline 644, which came from mine).
**Status:** PRE-REGISTRATION. No measurement has been taken. Committed before
any arm is decoded.
**Origin:** the orchestrator's request to *"register a bar for the demosaic
lever"*, which he describes as the second free win: Malvar-He-Cutler ships
today and sits mid-pack in a **0.3518 dex** spread across rawpy's algorithms
(`LINEAR −3.2552` … `AAHD −2.9033`), *"a spread larger than the entire
deficit"*.

---

## 1. Two corrections to the framing, before any bar is set

Both are knowable from the source and both change what a positive result would
mean. I am registering them now so that neither can be discovered
conveniently later.

### 1.1 A band-power spread is not a menu of available wins

`crates/strehl-core/src/demosaic.rs:19-51` documents that MHC was **chosen**,
not defaulted to, and one of its four stated reasons is directly about the
measurement I am being asked to make:

> **It cannot manufacture detail.** Every output is a bounded linear
> combination of measured samples. Rule 18 asks which direction a stage can be
> fooled in; a linear interpolator can only blur and alias, never hallucinate,
> so a sharpness metric downstream cannot be inflated by it.

The corollary is not written down, and it is the whole problem: **an adaptive
demosaic can inflate a sharpness metric.** `AAHD`, `AMAZE`, `DCB`, `VCD`,
`LMMSE` and `DHT` are all content-adaptive. Ranking them by band power will
therefore rank *hallucination* as *resolution*, and the algorithm that wins
such a ranking is the one that invents the most convincing structure.

So the 0.3518 dex spread is **an upper bound on what could be won, an upper
bound on what could be faked, and it does not distinguish them.** Any bar that
is just "more power in a band" is unfit for this question. §2 is built to
separate the two.

The same document already concedes the honest part — *"it is not the best
demosaic available. AHD, DDFAPD/DLMMSE, RCD and the learned methods all beat
it on zipper artifacts near high-frequency diagonal edges"* — so the existence
of a real win is not in dispute. Its **size**, measured in real detail rather
than in power, is.

### 1.2 The licence gate means a passing result does not license a switch

`AGENTS.md:12-40` forbids opening `librtprocess`, RawTherapee, ART, darktable
or Filmulator — GPL-3.0, and the lineage of `AMAZE`, `VCD`, `DCB`, `LMMSE` and
`RCD`. `demosaic.rs:43-45` records that MHC was implemented **from the paper's
stencils** and that *"no implementation was read to write this."*

Therefore, for any candidate that wins here, the only lawful route is
**re-implementation from a published paper**, exactly as MHC was. That is a
substantial engineering task with its own correctness burden — not a free win.
`rawpy`/LibRaw is used here **only as a measuring instrument in a separate
process**, producing pixel data; no algorithm is read, copied or ported.

**This does not devalue the measurement**, it scopes what the measurement can
authorise: a number that says *how much real detail is on the table*, which is
exactly what one would want before deciding whether to spend that engineering.
I am registering in advance that **I will not recommend adopting any specific
algorithm**, only report what each recovers.

---

## 2. The instrument: separating recovered detail from manufactured detail

The ruler makes this separable in a way a natural subject does not, because
**its structure is known a priori** and because the **optics impose a ceiling
that is already measured in this corpus**.

### 2.1 The physical ceiling is the discriminator

M5 measured the diffraction knee at **`0.2762` cyc/px**; the a-priori bellows
factor `B = 1 + m/p = 3.000` predicts **`0.2821`**, agreeing to **2.1%**
(SYNTHESIS facts 27 and 123). **The lens cannot deliver signal above that
frequency.** So, on a full-resolution demosaiced render:

| band | interpretation |
|---|---|
| **`R_sig`** = [0.15, 0.2762] cyc/px | below the optical cutoff — **real detail lives here** |
| **`R_alias`** = [0.30, 0.48] cyc/px | above the optical cutoff — **nothing here can be real** |

Power in `R_alias` is noise, CFA aliasing, or invention. **This is not an
inference from a model I built; it is the lens.** A demosaic that adds power
above the cutoff is manufacturing it by construction.

### 2.2 The four registered quantities

1. **`R_sig`** — contrast-normalised band power over [0.15, 0.2762] cyc/px.
2. **`R_alias`** — the same over [0.30, 0.48] cyc/px.
3. **`Φ = R_sig / R_alias`** — **fidelity**. Genuine resolution raises `Φ`;
   invention raises `R_alias` and so *lowers* it.
4. **`X`** — **chroma modulation at the comb**, from `R/⟨R⟩ − G/⟨G⟩` and
   `B/⟨B⟩ − G/⟨G⟩`. **The ruler is grey, so the true value is exactly zero.**
   Any chroma at the tick frequency is false colour, and unlike everything
   else here its ground truth is known without measuring anything.

Plus the comb modulations `M₁` at `f0` and `M₂` at `2·f0` from the M104
instrument, which is already admitted on 7/7 controls and is **insensitive to
output dimensions** (DIM control: `1.0014` and `1.0019` across changed
dimensions).

---

## 3. Bars — numeric, and fixed before any arm is decoded

Let `Δ` denote a candidate minus MHC, in dex, with SEs from across-ROI
repetition.

| bar | condition | value |
|---|---|---|
| **D1** REAL WIN | `ΔR_sig ≥ +0.02` dex **and** `ΔΦ ≥ −2 SE` | both required |
| **D2** MANUFACTURE | `ΔR_sig ≥ +0.02` **but** `ΔΦ < −2 SE` → **NOT a win** | reported as manufactured |
| **D3** CHROMA | `ΔX ≤ +2 SE` — no new false colour | ground truth 0 |
| **D4** COMB | `ΔM₁ ≥ −2 SE` and `ΔM₂ ≥ −2 SE` | real ticks must not fade |
| **D5** INERT | ≥ 8 live ROIs, S/B ≥ 3 | else **no evidence** |

**`D2` is the bar that makes this worth doing.** A metric that cannot return
"it scored higher and is worse" would agree with the naive band-power ranking
and add nothing.

### What result would make me report that MHC is already the right choice

**Stated in advance, as rule 12 requires:** if every rawpy algorithm either
fails `D1` or passes it only by failing `D2`, `D3` or `D4`, then **the shipped
demosaic is not costing measurable real detail on this subject** and the
0.3518 dex spread is mostly a spread in *artefact*, not in *resolution*. I
will report that plainly and recommend spending nothing. **That is a
completely acceptable outcome and I will not manufacture a lever.**

### Controls, each with its failing value

- **`NCD`, the negative control, made to go red exactly.** Apply an unsharp
  mask of exactly `amount = 0.500000`, `radius = 1.0` px to the MHC render.
  This manufactures detail by construction. It **must** raise `R_sig`, raise
  `R_alias` more, and drive `ΔΦ < −2 SE` — i.e. it must be **caught by D2**.
  **If a planted sharpener passes D1, the discriminator is blind and every
  result below is void.**
- **`PLD`, placebo.** Decode the same frame twice with the same algorithm.
  Every quantity must agree to **machine precision** (`< 1e-12`), not
  "closely".
- **`XNULL`.** MHC's own `X` on a grey ruler must already be small; it is the
  scale against which any candidate's false colour is judged.
- **`CUT`, a physical check on the band split.** `R_alias/R_sig` on a **single
  undemosaiced binned** frame must be far below 1, confirming the optical
  cutoff sits where facts 27/123 say. If the "empty" band is not empty on a
  path with no demosaic at all, the split is wrong and D1–D2 are meaningless.

### Registered predictions, to be scored

- (a) `LINEAR` loses real detail: `ΔR_sig < 0` and `ΔM₂ < 0`.
- (b) At least one adaptive algorithm triggers **D2** — higher `R_sig`,
  lower `Φ`.
- (c) `AAHD`, the orchestrator's top scorer, gains **less than half** of its
  0.3518 dex band-power lead once measured as `R_sig`.
- (d) `ΔX > 0` for at least one adaptive algorithm — visible false colour on a
  grey ruler.
- (e) **The orchestrator's combined claim**: with the resample removed *and* a
  best-case demosaic, the render sits **above** a single rawpy-`AHD` frame in
  `R_sig`. Registered as scoreable; **not** assumed.

---

## 4. Scope, and what is deliberately not measured

- **Only the green-derived luma and the two chroma differences.** No
  full-colour appearance metric.
- **The ruler only.** It is flat, static and grey, which is what makes the
  chroma null and the comb prior work. **Nothing here transfers to
  `bee-3-cpl` without re-measurement.**
- **Score the band, not the picture.** M87 measured the occlusion halo as a
  *second, independent* visible defect on these renders that survives at
  `--gate 0`. It is an election defect, not a sharpness defect, and it is
  unfixed for real captures. ROIs here are placed on ruler face only; any ROI
  containing a silhouette boundary is excluded before measurement, not after.
- **The merge is held out.** Arms are decoded from **one frame**, so the
  demosaic is the only stage that differs. Mixing in a 299-frame merge would
  confound demosaic quality with noise averaging.

---

## 5. Result — MEASURED

Frame `DSC00049.ARW` of `flat-on-ruler-cpl`, 15 live ROIs, 384 px, paired per
ROI. Shipped arm is `strehl stack --demosaic --gate 0` with `STREHL_ALIGN=0`,
so **no `fit_to_cover` resample contaminates the comparison**. Raw output:
`experiments/M104b-demosaic/out/d1_arms_384.log`.

### 5.1 Controls — all four pass, and the negative control went red exactly

| control | value | bar | verdict |
|---|---|---|---|
| **NCD** planted unsharp, amount `0.500000`, radius 1.0 px | `ΔR_sig +0.2054` (**49.52σ**), `ΔΦ −0.1263` (**31.14σ**) | must be caught by **D2** | **RED, as required** |
| **PLD** placebo, same algorithm decoded twice | worst deviation **`0.000e+00`** | `< 1e-12` | PASS |
| **CUT** band split vs the diffraction knee | `R_alias − R_sig = −0.7740` dex | `< −0.30` | PASS |
| **D5** INERT | 15 live ROIs | `≥ 8` | PASS |

**NCD is the load-bearing one.** A planted sharpener raises `R_sig` by more
than any real algorithm managed and is still classified **MANUFACTURED**,
because it raises `R_alias` faster. The discriminator does the job it was
registered to do.

### 5.2 Every algorithm fails D1

| arm | `ΔR_sig` dex | σ | `ΔΦ` dex | σ | verdict |
|---|---|---|---|---|---|
| `AAHD` | **+0.0190** | 7.07 | **−0.0626** | 13.21 | no win (D1 unmet) |
| `DHT` | +0.0131 | 3.27 | −0.0252 | 6.73 | no win (D1 unmet) |
| `AHD` | −0.0217 | 3.22 | +0.0132 | 2.33 | no win |
| `PPG` | −0.0341 | 3.49 | +0.0300 | 4.42 | no win |
| `VNG` | −0.0477 | 7.08 | −0.0314 | 2.26 | no win |
| `DCB` | −0.0511 | 4.99 | +0.1447 | 10.59 | no win |
| `LINEAR` | −0.1192 | 17.16 | +0.1733 | 12.88 | no win |

**This is the outcome §3 registered in advance as "MHC is already the right
choice."** No algorithm clears `ΔR_sig ≥ +0.02` dex.

**`AAHD` misses by 0.0010 dex and I am reporting that as a miss, not rounding
it to a pass.** The conclusion does not rest on where the bar sits: had `AAHD`
cleared D1, its `Φ` falls **13.21σ**, so **D2 would have classified it
MANUFACTURED**. The two independent bars agree.

### 5.3 The 0.3518 dex spread is mostly artefact

The orchestrator's framing was that MHC *"sits mid-pack in a 0.3518 dex spread
… a spread larger than the entire deficit."* Measured as **real detail below
the diffraction cutoff**, the best available gain over MHC is **+0.0190 dex** —
**5.4% of that spread**. Registered prediction (c) said "less than half"; the
true figure is **less than a twentieth**.

The rest of the spread is `R_alias`: power above `0.2762` cyc/px, where **the
lens cannot deliver signal**, so it is aliasing and invention. Ranking
demosaics on band power ranks that.

### 5.4 The registered predictions

- **(a) CONFIRMED.** `LINEAR` loses real detail: `−0.1192` dex at **17.16σ**.
- **(b) CONFIRMED.** Adaptive algorithms trigger the D2 pattern: `AAHD`
  `ΔΦ −0.0626` (13.21σ), `DHT` `−0.0252` (6.73σ), `VNG` `−0.0314`.
- **(c) CONFIRMED, and by a wider margin than registered.** 5.4%, not <50%.
- **(d) CONFIRMED.** Every adaptive arm carries **more** false colour on a grey
  ruler than MHC: `X` rises from `0.8288` to `0.9217` (`AAHD`), `0.9056`
  (`DHT`), `0.9004` (`AHD`).
- **(e) NOT SCORED.** The combined claim needs M95's fix, which has not landed.

### 5.5 The licence gate, now measured rather than argued

§1.2 predicted the algorithms that beat MHC sit behind GPL implementations.
LibRaw refused **six of thirteen** at the door:

```
LMMSE, VCD, MODIFIED_AHD, VCD_MODIFIED_AHD, AFD  -> "requires GPL2 demosaic pack"
AMAZE                                            -> "requires GPL3 demosaic pack"
```

`AMAZE` and `LMMSE` are exactly the algorithms `demosaic.rs:47` names as
beating MHC. **They could not be measured here and could not lawfully be read
if they had been.**

---

## 6. Verdict

**NO LEVER. Do not spend engineering on the demosaic.** MEASURED: no
available algorithm delivers `≥ 0.02` dex of real sub-cutoff detail over the
shipped Malvar-He-Cutler on this subject; the best candidate manufactures
detail at 13.21σ and adds false colour to a grey ruler. The 0.3518 dex spread
that motivated the question is **5.4% real and the rest artefact**.

**The softness is not here.** M104 measured the resample at `+0.1623` dex on
this same ruler, **8.5× larger than the best demosaic gain**, and 97.0% of it
is one removable operation. That remains the fix worth making.

### What would overturn this

A demosaic that raises `R_sig` by `≥ 0.02` dex **without** lowering `Φ`. None
of the seven tested does. This was measured on **one flat, grey, periodic
subject**; it does not transfer to `bee-3-cpl` without re-measurement, and the
zipper artefacts `demosaic.rs` concedes MHC suffers live on **high-frequency
diagonal** edges that a ruler at a shallow angle under-represents.

---

## 7. Instrument defects found and disclosed

Three of my own, all caught by controls or by a bar failing, all fixed before
the numbers in §5:

1. **Seed lookup by the wrong key type.** `seed_combs` returns a dict keyed by
   **integer ROI index**; I looked up by `(x, y)` tuple, so every lookup
   returned `None` and every frame scored zero live ROIs. My first diagnosis —
   "the seed frame is out of focus" — was **wrong**, and the real cause was a
   type mismatch that produced a plausible-looking null.
2. **Seeding a focus bracket from a single frame.** A single exposure is sharp
   only in a band, so `find_comb` locked onto coarse structure at `f0 ≈ 0.016`
   cyc/px instead of the ruler's `0.140` binned. Both arms then agreed to three
   decimals **on the wrong feature** — the arms were fine and the seed was not.
   Repaired by taking the frequency from the 79-frame merge, which is in focus
   everywhere, while liveness stays on the demosaic-free binned decode.
3. **A per-arm INERT gate on a paired design**, which let every candidate
   choose its own ROI sample, and **an unpaired SE on paired data**. The
   second is the worse one: carrying the ROI-to-ROI spread of "how much ruler
   is in this crop" into the error bar inflated SEs to `~0.18` dex, an order
   of magnitude above the effects, and **declared every arm inconclusive by
   construction**. Differencing per ROI first cuts the SEs to `0.003–0.014`
   dex. A defect that returns "no significant difference" is the most
   comfortable kind to leave in and the easiest to miss.
