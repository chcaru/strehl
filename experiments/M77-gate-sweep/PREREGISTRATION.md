# M77 pre-registration — the spatial gate sweep

**Committed before any number in this milestone existed.** Nothing below was
written after seeing a result. Where a deviation later proves necessary it will
be declared as a deviation, in the report, with its reason.

---

## 1. The question

SYNTHESIS **fact 1036** (M73, `35afb73`) records that at the shipped
`DEFAULT_GATE = 4.0`, on two real subjects, the merge admits **1.238 of 130** and
**1.766 of 120** frames — `n_eff/N` of **0.0095** and **0.0147**, with the
admitted set a **singleton at 81.4% and 58.7%** of scored pixels. Fact 629's
corpus floor is **0.0118**, measured at the *looser* gate 2.0.

The corpus cannot currently choose between two readings:

- **(a)** the gate is too tight, and frames carrying real information are being
  discarded;
- **(b)** the collapse is **correct** — at this magnification only one frame
  carries the pixel in focus, so there is genuinely nothing to average.

This matters because the project's thesis is that `strehl` is an **estimator**
and every shipping competitor is a **selector**. Under reading (b) the shipped
estimator behaving as a selector on real subjects is a defensible answer that the
project must **state in its own claims**. Under reading (a) the default is wrong.

**M73 §13.6 named this exact gap and declined it:** *"Image quality of the merged
output. This milestone scores index fields only. Whether a merge admitting 1.24
frames produces a worse image than one admitting 12 is unmeasured."* The shipped
CLI's own `--gate` help says the same thing about itself: *"The sharpness cost of
THIS gate on real frames is not measured in this corpus, and no number here
should be read as claiming otherwise."*

---

## 2. Mechanism and observable, stated without a direction

**Mechanism.** Opening the gate admits more frames per pixel. Two consequences
move in **opposite** directions and neither is disputed:

1. Averaging more frames reduces the variance of the estimate, at best as
   `1/sqrt(n_eff)` when the admitted frames contribute independent noise.
2. Admitting frames whose focus differs from the winner's mixes in blurred
   samples, which reduces resolved contrast.

**The gate's correctness is the question of whether the shipped value sits at the
knee of that tradeoff.** This needs no ground truth, because the two effects are
measured on the same sweep and move in opposite directions.

**I do not state which way this comes out, and there is no outcome this
pre-registration prefers.** "The shipped gate sits at the knee, reading (b)
holds" and "there is free variance reduction above gate 4, reading (a) holds" are
both fully successful outcomes. A third — that the two sides disagree *between
stacks* — is also a real outcome and §7 says what I do with it.

---

## 3. Instrument, and why no code change is needed

The shipped CLI already computes both sides and already sweeps:

```
strehl stack <dir> --gate 0 1 2 4 8 16 32 64 --flat-roi X,Y,W,H --detail-roi X,Y,W,H
```

- `--gate` takes `num_args = 1..` (`main.rs:120`) and every value is folded in the
  **same pass two**, so a sweep costs one decode budget rather than one per value.
- **ACCEPTANCE INVARIANT 1 of 2** (`merge_cmd.rs:1007`) prints, per gate, the
  flat-ROI **high-pass sd** and an **HP RATIO** against the distribution over
  **every** frame.
- **ACCEPTANCE INVARIANT 2 of 2** (`merge_cmd.rs:1189`) prints, per gate, the
  noise-**corrected** detail gradient and a **RETENTION** ratio.
- The `mean n_eff` ladder is printed at `merge_cmd.rs:966`.

**No file under `crates/` will be modified.** The project's gate for touching the
certified path is pre-registration plus a re-run of M62's acceptance battery;
this milestone needs neither, and if I come to believe a code change is
unavoidable I will say so in the report instead of making it.

**Build provenance.** The binary will be built from a `cargo clean -p` of the
workspace crates so the build prints `Compiling` lines. A `Finished` with no
`Compiling` proves freshness, not authorship, and will not be measured from.

---

## 4. Arm G0 — ROI selection, which is the whole experiment

**Discipline 438: a rule validated on one ROI class has not been validated.** The
corpus has already been bitten here, and it is recorded in shipped source:
`flat_ratio.rs:15–23` states that the four flat ROIs the corpus published are
**53.3%, 50.9%, 80.0% and 72.2% scene structure by variance**, and that one of
them *"is not even detail-free."* M73 §5.5 adds that on `wrapped-text` the label
stock's own texture, not the print, supplies most of the focus signal — so "low
gradient" does not mean "flat" on that subject.

**ROIs are therefore selected by a rule fixed here, before any sweep runs, and
computed from INPUT FRAMES ONLY.** No merge output, at any gate, enters ROI
selection. This is what keeps ROI choice from being circular with the result.

Rule, per stack:

1. Tile the plane on a fixed grid of **256×256** candidate tiles, stride 128,
   discarding tiles within 32 px of the plane edge.
2. Sample frames at a fixed stride so that **at least 12 frames** are examined,
   always including the first, middle and last.
3. For each tile compute, on black-subtracted green luma:
   - `contam(tile, frame) = hp_sd / (HP_NOISE_GAIN * model_sigma)` — the shipped
     `structure_contamination` (`flat_ratio.rs`), at `HP_BOX_SIDE = 9`,
     `HP_NOISE_GAIN = sqrt(1 - 1/81)`;
   - `cg(tile, frame) = sqrt(max(0, raw_rms^2 - noise_rms^2))` — the shipped
     `detail_metrics` corrected gradient (`merge_cmd.rs:305`).
4. **Flat ROI** = the tile minimising `max over sampled frames of contam`. The
   max, not the mean, so the tile is flat in **every** sampled frame rather than
   on average — a tile that is flat in most frames and textured in one is not a
   flat ROI for a sweep that averages frames.
5. **Detail ROI** = the tile maximising `max over sampled frames of cg`. The max,
   because the detail must be resolved **somewhere in the bracket**; a detail
   region that is blurred in the middle frame is exactly the case the merge
   exists to serve.

Both ROIs are reported with their achieved statistics, and the achieved
`contam` is carried next to every noise number as its disclosed bound (§6, K1).

---

## 5. Arms, stacks and the ladder

**Stacks, chosen by a rule fixed here**, to span the measured `n_eff/N` range
(fact 629) and include M73's subject for continuity:

| stack | N | why it is in |
| --- | --- | --- |
| `wrapped-text-1` | 130 | M73's subject; the **lowest** `n_eff/N` in the corpus (0.0095) and the origin of fact 1036 |
| `109MSDCF` | 22 | the corpus's most-measured stack; **highest** `n_eff/N` at gate 2 (0.1314) |
| `coffee-bean` | 105 | highest absolute `n_eff` at gate 2 (14.386, M52) |
| `foam` | 100 | M52: **cannot reach `n_eff = 3` anywhere** on the 0.5–4.0 ladder — an extreme |
| `bee-1` | 299 | largest N; tests whether the tradeoff shape depends on bracket length |

**Ladder:** gates **0, 1, 2, 4, 8, 16, 32, 64**. Gate 0 is the pure-selector
anchor (K3). Gates 1–64 match M73 §8's ladder so the two are directly comparable.

**Reported against `mean n_eff`, not against gate.** M52 measured that the gate
achieving a chosen `n_eff` varies **28.9×** across the corpus, so a gate is not
portable between stacks; M67's fact 14 requires `n_eff/N` beside any such number
and M73 §8 followed it. Gate is the knob; `n_eff` is the physical axis.

**Arms:**

- **G1** — the ladder on all five stacks with the G0 ROIs. The registered arm.
- **G2** — the efficiency decomposition `eff(T) = HP_RATIO(T) / sqrt(n_eff(T))`.
  Derived, reported for every rung. It asks how efficiently the admitted frames
  actually average, which is the quantity reading (b) is a claim about.

---

## 6. Controls, each with its consequence fixed now

| id | control | bar | consequence if NOT MET |
| --- | --- | --- | --- |
| **K1** | the flat ROI is actually flat | achieved `contam < 1.10` on the selected tile | **Not fatal, but disclosed.** `flat_ratio.rs` establishes the HP ratio is *upward-blind, never upward-fooled*: contamination is **exactly** the factor by which a ratio of two such sds **under-reports** a noise change. Every `ΔN` is then reported as a **lower bound** with the achieved factor printed beside it |
| **K2** | the detail ROI actually has detail | selected detail tile's `cg` >= **3×** the selected flat tile's `cg`, same frame | the two ROIs are not distinct region classes, the decomposition is vacuous, and the milestone reports **INDETERMINATE** rather than a verdict |
| **K3** | selector anchor | at gate 0: `mean n_eff` == 1.000, and `HP RATIO` within **[0.90, 1.10]** | the noise statistic is not measuring averaging. M62 fact 890 measured `merge --gate 0` at **0.9768×** on the shipped invariant, so this has a known anchor. **Verdict becomes INDETERMINATE** |
| **K4** | monotonicity | `mean n_eff(T)` non-decreasing across the ladder | the sweep is not a sweep; report as a defect and stop |
| **K5** | ROI selection is not noise-driven | selecting on even-indexed vs odd-indexed sampled frames returns the **same or an adjacent** tile, both ROIs, all stacks | ROI choice is unstable, and every per-stack verdict is reported with that instability attached |

**The known-answer control I do not have, named rather than glossed.** The
**static burst is the obvious variance-side arm and it does not exist.** M62's
`src/07-real-burst.py` records *"the real branch is not run because no real burst
exists"*; `docs/captures-needed.md` §12 still lists it as REQUESTED, with M69's
note that the milestone was chartered on the belief it had been delivered. Had it
existed it would have arbitrated **only the variance side**, where `sqrt(30)` is
exactly known — and, per M62 fact 916, it would have arbitrated **nothing** on the
bias side, because a static burst has every frame in focus, no focus variation and
therefore no interior optimum. **K3 is the replacement and it is weaker**: it
anchors the statistic at one end of the sweep rather than certifying its scale.

---

## 7. The decision rule, fixed now

Per stack, relative to the shipped gate:

```
dN(T) = HP_RATIO(T)   / HP_RATIO(4.0)      noise benefit of opening
dD(T) = RETENTION(T)  / RETENTION(4.0)     detail cost of opening
```

**Bars:**

- **Material noise gain:** `dN >= 1.10`.
- **Material detail cost:** `dD <= 0.98`.

**Why 0.98 and not a rounder number.** `merge_cmd.rs:1524` registers
`DETAIL_COLLAPSE_FLOOR = 0.90` for outright collapse, and records that ordinary
gate-to-gate drift on this metric was **MEASURED at 0.2% (`109MSDCF`) and 0.6%
(`119MSDCF`) across gate 0 to 2.0**. A 2% bar therefore sits **3–10× above the
metric's own measured drift** and an order of magnitude above the shipped
collapse line. Both bars are fixed here and will not be moved.

**Verdicts, per stack:**

- **(a)-SUPPORTED** — there exists `T > 4` with `dN >= 1.10` **and** `dD > 0.98`.
  Free variance reduction is available above the shipped gate.
- **(b)-SUPPORTED** — for every `T > 4`, either `dN < 1.10` **or** `dD <= 0.98`.
  Either there is nothing to gain, or the gain is paid for in resolved detail.
- **INDETERMINATE** — K2 or K3 not met.

**Corpus verdict.** Reported as the **per-stack split, never as a bare majority**.
**If the stacks disagree, that disagreement is the headline and not a nuisance**:
it is direct evidence on the orchestrator's question of whether the right gate is
a single number at all, and SYNTHESIS fact 1045 (within-stack response-SD
dispersion of 1.70–3.99×) predicts that a single global gate cannot be right for
every pixel even within one image.

**Additionally reported, not a decision:** the **knee** — the largest `T` at which
`dD > 0.98` — and the `dN`, `n_eff` and `n_eff/N` at that point, per stack.

---

## 8. What would make me conclude reading (a) is wrong

Stated as observables, in advance:

1. `dN` never reaching 1.10 anywhere on the ladder — admitting more frames does
   not measurably reduce flat-ROI noise, so there is no information being
   discarded to recover.
2. `dN` reaching 1.10 only at rungs where `dD <= 0.98` — the variance is bought
   and paid for, which is what a knee at or below gate 4 looks like.
3. `eff(T)` falling steeply below 1 as `T` rises — admitted frames are not
   contributing independent samples, which is the mechanism reading (b) asserts.

And what would make me conclude reading (b) is wrong: any rung above gate 4 with
a material noise gain at no material detail cost, on a majority of stacks.

---

## 9. The circularity, and where it bites

**The gate is denominated in `FOCUS_NOISE_SD`, and M69 measured that constant to
be a texture-dependent quantity carrying a 4.06× span across texture scale, with
a within-stack per-pixel dispersion of 1.70–3.99× (SYNTHESIS facts 1043, 1045).**
So "gate 4" is **not one tolerance**. It is a different effective tolerance on
each stack and, more awkwardly, on each *pixel* of each stack.

- **Where it bites:** any claim of the form *"the right gate is T"*. A single
  number cannot be right across a dispersion that large, and I will not report one.
- **Where it does not bite:** the **shape** of the tradeoff read against
  `mean n_eff`. `n_eff` is a counted physical quantity — how many frames were
  actually averaged — and is not denominated in the constant. Sweeping the gate
  and reporting against `n_eff` removes the between-stack part of the circularity
  entirely. It does **not** remove the within-stack part: at one gate, different
  pixels of one frame are effectively gated at different tolerances, and both my
  ROIs are spatial regions that each average over many such pixels.

**A second, independent model dependence, and it cancels by construction.**
`RETENTION` is built on `corrected_rms = sqrt(raw^2 - model_noise^2)`, and M69
fact 24 measured the shipped model **over-predicts read noise by 8–27%**, which
would depress `corrected_rms`. The reference `base` is a single frame and is
**fixed across the whole sweep**, so it divides out of `dD(T) =
RETENTION(T)/RETENTION(4.0)` **identically**. `dD` is therefore immune to the
reference frame's noise mis-model. It is *not* immune to the mis-model in the
merged numerator, which shrinks as `T` grows because `model_noise` carries the
`1/sqrt(n)` — so the residual bias runs along the sweep axis and its size is
reported rather than assumed.

---

## 10. Scope — what this milestone will not do

- **No spectra, no frequency-domain anything.** M70 is live on the frequency-domain
  form of fact 1036. If this milestone finds itself computing a transform it will
  stop and route the question instead.
- **No re-derivation of M73 §8's ladder**, which already measured `n_eff` against
  gate on `wrapped-text-1/2`. That is cited, not repeated (rule 40).
- **No choosing of an operating gate.** M73 §8 declined to pick a point off its own
  curve and the same reasoning applies here with more force, given §9.
- **No ruling on M62's certification.** Not mine.
- **No edit to** `SYNTHESIS.md`, `AGENTS.md`, `OWNER-QUESTIONS.md`, or
  `docs/research/M70-through-focus-spectrum.md`.

---

## 11. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo clean -p strehl-core -p strehl-cli -p strehl-plugin
cargo build --release --bin strehl        # must print Compiling

$env:PYTHONIOENCODING='utf-8'
python experiments\M77-gate-sweep\src\01-rois.py     # arm G0, input frames only
python experiments\M77-gate-sweep\src\02-sweep.py    # arms G1/G2, calls the shipped binary
python experiments\M77-gate-sweep\src\03-decide.py   # applies section 7 verbatim
```

`D:\personal\macro` is read-only and is never written to.
