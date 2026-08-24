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
