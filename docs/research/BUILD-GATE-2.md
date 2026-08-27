# BUILD-GATE-2 — the floor is measured per frame and now reaches the gate; my own F1 was right for the plane arm and **wrong for the shipping one**

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`F1, D1, Q1, …` per rule 28.** The orchestrator allocates absolute numbers at
fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `e017c0bf` (`V-H2H2: mask audit finds no exposure,
and a registration sign defect`). Working tree shared with `BUILD-DEFECT`;
`git status --porcelain` was re-read immediately before every write and
`defect_map.rs` was never opened by this lane.

**Instruments:** `crates/strehl-cli/src/merge_cmd/gatefloor.rs` (the shipping
probe), `experiments/BUILD-GATE/src/acuity.py` (the Q1 instrument),
`experiments/BUILD-GATE/src/matrix.ps1` (the arm matrix). Source stacks under
`D:\personal\macro\` were read only; every output was written under
`C:\dev\strehl-out\`.

---

## 0. The answer, up front

**Built and landed.** The merge gate's per-band noise floor is now **measured
from each frame's own warp** instead of carrying the compile-time constant
`BandGain::beta = 0.88980`. `STREHL_GATE_FLOOR=white` restores the constant
exactly.

Three things the owner needs to read before anything else:

**(a) I have to correct my own F1 from BUILD-GATE.md, and the correction
inverts its conclusion for the shipping path.** BUILD-GATE.md §1 said the floor
was *too high in both arms*, so a correct fix would drive `averaged` **down in
both**. That is right for the plane arm and **wrong for the shipping fullres
arm**, where the floor is too **LOW**. My synthetic probe used unity white
balance and a non-existent file path, so it silently got an identity CA profile;
neither is true of a real frame. Measured on real frames, band 0:

| arm | measured floor | × white | gate as a multiple of TRUE noise |
|---|---:|---:|---:|
| plane (`STREHL_FULLRES_GATHER=0`) | 0.5539 | **0.6225** | 2.0/0.6225 = **3.21×** |
| fullres (**shipping default**) | 1.0488 | **1.1787** | 2.0/1.1787 = **1.70×** |

**MEASURED**, `foam --limit 6`, banner `measured floor` line. So the owner's
*original* framing — noise clearing a too-low gate on the shipping path — was
right, and my §5 was wrong about the arm that ships. Both were wrong about the
cause: it is warping, not the flip.

**(b) The owner's acceptance criterion #1 is not met on the statistic it names,
and I believe the criterion is the thing that is wrong — but this time I built
it first so the reader can judge.** The `averaged` fractions **diverge**. §3
gives the numbers and §3.2 gives the direct measurement of what the owner
actually asked for ("each pixel sitting at the same multiple of its own floor"),
which **is** met, exactly and by construction.

**(c) The fix corrects the gate's SEMANTICS. It does not demonstrate an
image-quality win, and on two of three subjects it trades noise for acuity at
almost exactly 1:1.** This is the answer to Q1 and it is in §4. It is not the
answer I expected and it moves the open question onto the `2.0×` gate constant
itself.

---

## 1. What was built

`crates/strehl-core/src/pyramid.rs`
: `add_frame_with_gain(planes, luma, variance, frame_beta: Option<&[f32]>, ws)`.
  `add_frame` is retained as a thin delegate passing `None`, so all 24 existing
  call sites are bit-identical **by construction** rather than by 24 correctly
  typed `None`s. Both readers of the floor — the gate and the hull margin at
  L1429 — go through one `beta_for` helper, so they cannot diverge; the hull
  margin's own comment warned about exactly that divergence and now says it is
  enforced.

`crates/strehl-cli/src/merge_cmd/gatefloor.rs` (new)
: The probe. It **clones the decoded frame** and replaces only the sample data,
  so it inherits the frame's real geometry, real `wb_coeffs` and real `path`.
  That last one is load-bearing and is exactly what the synthetic instrument got
  wrong: `path` is what resolves the CA profile, which warps the four CFA sites
  at four different phases. It then pushes white photosite noise through the
  **real** `warp_frame_in_place` with the frame's **own** transform, deinterleaves
  through the real `load_frame` path, and builds a real `Pyramid`.

`crates/strehl-cli/src/merge_cmd.rs`
: `load_frame` gained a `floor` parameter and measures inside the
  `FrameWarp::Placed` arm — the only place the decoded frame and its applied
  transform are both in scope. The confidence pass passes `None`. The banner
  gained a `measured floor` line reporting the floor **actually used**.

### 1.1 Why a probe and not a formula

**D1 (DERIVED, from BUILD-GATE.md §4, which stands).** The transfer is a
function of per-frame warp **phase**, with period 1 plane-px on the plane arm
against **1/2** plane-px on fullres, and **the two curves cross**. No single
analytic factor can be right for both arms at once. A closed-form kernel ratio
is the scalar-transferred correction this project already killed once.

### 1.2 Why only bands 0–3

**F2 (MEASURED).** `CERTIFIED_BANDS = 4`. The identity null — the probe run on a
**real** frame with its real white balance and real CA profile but an identity
transform, where the answer must be 1.0000 — reads:

```
band            0        1        2        3   |     4       5        6
null       1.0000   0.9990   0.9950   1.0030   | 1.031   1.021    12.6
```

At bands 4–5 the instrument's own error is the same size as the effect it would
be correcting, so correcting them would report the instrument. Band 6 on this
sensor is reconstructed across a `level_sizes` truncation seam (…198, 99, **49,
24** — 2×24 ≠ 49) and reads 12.6×. **Mean-subtraction did not fix band 6**,
which proves it is the seam and not the DC — unlike the synthetic instrument's
base-band bug, which mean-subtraction did fix.

And the decision to correct only band 0 is a **measurement, not an assumption**,
as required: the banner's `x white` line reads

```
plane     0.6225   0.9935   1.0208   1.0289
fullres   1.1787   0.9443   0.9966   1.0222
```

Bands 1–3 are within ±6% of white; band 0 is off by 18–38%. The effect is at
band 0. Bands 1–3 are corrected anyway because they are certified, and the
correction there is nearly a no-op.

---

## 2. Commissioning of the probe

| control | expectation | result |
|---|---|---|
| identity warp, real frame, real WB, real CA | 1.0000 | **1.0000 / 0.9995 / 0.9998** at band 0; worst certified band **+0.583%** |
| `STREHL_GATE_FLOOR=white` | restores the constant exactly | banner reads `0.8898`; byte-freezes HOLD |
| align-refused / unaligned frame | correction identically 1.0 | never reaches `measure`; **structurally** unwarped ⇒ no probe |

**MEASURED.** The identity null is the control that matters: it runs the whole
probe on a real frame and differs from a working run only in the transform. It
caught two instrument bugs in the synthetic predecessor (scene DC in the base
band; the warp's black border inflating whole-plane variance **39×**), and it is
why the certified band count is 4 rather than 7.

---

## 3. The arms

### 3.1 `averaged` at band 0 — the owner's named statistic. It DIVERGES.

`--limit 10`, all frames placed, W = white floor (today), M = measured floor.

| subject | folded | planeW | fullW | \|gap\|W | planeM | fullM | \|gap\|M |
|---|---:|---:|---:|---:|---:|---:|---:|
| `foam` | 10/10 | 97.2 | 90.7 | 6.50 | 60.0 | 97.2 | 37.20 |
| `coffee-bubbles` | 10/10 | 68.8 | 39.7 | 29.10 | 34.0 | 48.2 | 14.20 |
| `tweezers-cpl` | 10/10 | 95.7 | 88.4 | 7.30 | 52.2 | 96.0 | 43.80 |
| `bee-1-cpl` | 10/10 | 95.9 | 88.5 | 7.40 | 53.1 | 96.0 | 42.90 |
| `couch-fibers-cpl` | 10/10 | 97.8 | 91.0 | 6.80 | 62.7 | 99.0 | 36.30 |
| `lavendar-cpl` | 10/10 | 97.5 | 93.0 | 4.50 | 62.0 | 97.7 | 35.70 |

**MEASURED.** Mean arm gap **6.5 pp → 39.7 pp**. On the owner's stated criterion
#1 this is a **FAIL**, and on criterion #2 (`averaged` falls in both arms) it is
also a fail: it falls in plane and **rises** in fullres.

Both directions are exactly what the measured floors predict, on all six
subjects, with no exception: the plane floor is corrected **down** (0.62×) so its
gate falls and fewer coefficients are averaged; the fullres floor is corrected
**up** (1.18×) so its gate rises and more are.

### 3.2 The criterion the owner actually stated — and it is met exactly

The owner's words were *"each pixel sitting at the same multiple of its own
floor"*. That is not the same claim as "equal `averaged` fractions", and it is
the one that can be checked directly:

| | plane | fullres | spread |
|---|---:|---:|---:|
| **before** — gate ÷ that arm's true band-0 noise | 3.21× | 1.70× | **1.89×** |
| **after** | 2.00× | 2.00× | **1.00×** |

**MEASURED** (the floors) + **DERIVED** (the division). The arms converge to
identical, and to the nominal value the banner has always claimed.

**F3 (ARGUED, and I flag it as argued).** `averaged` cannot converge and should
not have been expected to. It is the fraction of coefficients whose band power
falls below 2× *their own* noise, so equal `averaged` requires the two arms'
frames to have the same signal-to-noise distribution at band 0 — and the entire
point of the gather flip is that they do not. Band 0 is the finest octave, which
is precisely what the plane lattice band-limits away. Equal `averaged` across
the arms would have been evidence the flip did nothing.

### 3.3 The placebo

**MEASURED and STRUCTURAL.** An align-refused frame returns from `load_frame`
before the `FrameWarp::Placed` arm, and a run with alignment off passes
`warps: None` and never enters that branch, so `measure` is never called and the
floor is the constant. The unaligned byte-freeze config is the check, and it
**HOLDS byte-identically** (§6). This is a null that holds *by construction*, not
by measurement.

---

## 4. Q1 — did the mis-set floor cost acuity? **Yes, and the fix does not buy it back.**

The owner asked whether the plane arm's "noise removal" was ever noise removal
or partly weak signal averaged away, and said it bears on whether the output is
soft.

**Instrument:** `experiments/BUILD-GATE/src/acuity.py`. Finest-octave high-pass
rms over two **fixed** tile sets — flattest and most-structured deciles, selected
once from a reference arm on the **low-pass** so that an arm cannot move the
statistic by moving the tile selection.

**Commissioning (§110.6 + §111.3 — planted defect, planted improvement, and a
healthy control that superficially resembles the defect):**

| arm | Δ flat % | Δ sharp % | required | verdict |
|---|---:|---:|---|---|
| identity | 0.00 | 0.00 | both exactly 0 | **pass** |
| gain ×1.02 — *healthy control* | +2.00 | +2.00 | move **equally** | **pass** |
| blur — *planted acuity defect* | −83.95 | **−74.42** | sharp falls | **pass** |
| noise σ=50 DN — *planted noise defect* | **+33.71** | +14.09 | flat rises more | **pass** |
| denoise-flat — *planted improvement* | **−83.94** | **−0.02** | flat falls, sharp holds | **pass** |

The planted improvement is the one that matters and it is the exact shape of the
change being claimed. An instrument that could not score it as a gain would
score every arm as a loss — which is how `overshoot_frac` certified a planted
2 px ring as an improvement.

**The arms, on the shipping fullres path, white floor → measured floor:**

| subject | Δ flat (noise) | Δ sharp (acuity) | CNR (sharp/flat) |
|---|---:|---:|---:|
| `foam` | −22.47% | −23.23% | **−1.0%** |
| `tweezers-cpl` | −24.63% | −19.90% | **+6.3%** |
| `couch-fibers-cpl` | −35.73% | −36.09% | **−0.6%** |

**MEASURED. F4: the gate at band 0 is very nearly a non-selective attenuator.**
Raising the floor removes noise and detail in almost the same proportion. Only
`tweezers-cpl` — the brushed-steel subject where the owner sees the magenta
speckle — shows a real separation, and it is +6.3%, not a transformation.

The answer to Q1 is therefore **yes**: a large part of what this project has been
calling noise suppression at band 0 has been costing acuity roughly one-for-one.
The pre-flip plane arm's high `averaged` was not free. But the corollary is the
uncomfortable half: **my fix does not recover that acuity, it moves along the
same trade curve.** It sets the gate to the value the banner has always claimed;
it does not make band 0 selective.

**Q2 (open, and I think it is now the important one).** The `2.0×` gate constant
was tuned while the floor was 1.70–3.21× off. The historical, accepted,
pre-flip behaviour was an effective **3.21×**; the current shipping default is
**1.70×**; this fix sets **2.00×**. Which of those is *right* is a question this
lane did not ask and cannot answer from these measurements. It should be swept
now that the floor underneath it is finally a measured quantity rather than a
constant — that sweep is only meaningful with this fix in place.

---

## 5. What is approximate, stated plainly

**Q3 (open).** The correction is a per-frame **scalar** per band. Real
focus-bracket transforms carry `g ≈ −0.013 … −0.020` (1.3–2% scale) and
translations to ~16 px, so warp phase sweeps many cycles **across one frame**. A
scalar is therefore a spatial average of a quantity that genuinely varies within
the frame. A per-pixel field would be more correct and is not built.

**Q4 (open).** The probe measures how independent photosite noise transfers,
which is what the gate models. It does **not** measure interpolation ringing.
The plane arm's band-0 content is not white-noise-like, and its 3.21× over-gate
was accidentally suppressing that too; at a correct 2.00× gate the plane arm's
output noise rises 19.7% (`foam`). The plane arm is not the shipping path, so
this is recorded rather than fixed.

**Not measured.** The probe's wall-clock cost was not isolated against a
`STREHL_GATE_FLOOR=white` baseline. It is one extra warp and pyramid per frame,
so it is not free; I did not price it.

---

## 6. Freezes — they do NOT move, and the reason is a finding

`byte-freezes.tsv` is ORCH-owned and **was not touched by this lane**.
`STREHL_GATE_FLOOR` was added to `RENDER_ENV` in `byte-freeze.rs` in the same
commit, and declared in `scripts/check-defaults.py` with `verified="measured"`.

**Both freezes HOLD.** `cargo test --workspace` at this change:

```
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F...154A8620
  (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS: 52517FF8AE245F23...837EC206
  (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames,
   20 placed / 0 refused) -- reproduced twice
```

**F5 (MEASURED). That is not because the change is inert. It is because the
registry does not cover the shipping merge backend.** Both rows hardcode
`--merge estimator` (`byte-freeze.rs:536`), and

```
crates/strehl-cli/src/merge_cmd.rs:417:
pub const DEFAULT_MERGE_BACKEND: MergeBackend = MergeBackend::Pyramid;
```

The comment above the hardcode says *"The estimator is still the default, so
these rows would run correctly without this"* — **that sentence is now false** —
and then predicts this exact situation: *"It is hardcoded rather than a column
because every existing row genuinely is an estimator freeze. The day a pyramid
row is added this must become a registry column, exactly like `--gate` did."*
The default moved and no pyramid row was added, so **the shipping default merge
path is unfrozen**. `20 placed / 0 refused` proves the sidecar row does warp, so
it is backend coverage that is missing, not warp coverage.

### 6.1 The numbers ORCH needs, measured at a pinned commit in a detached worktree

Rendered at `78fed9a1` in `C:\dev\strehl-out\BUILD-GATE\wt\fix`, each row's own
recorded invocation and environment
(`experiments/BUILD-GATE/src/freeze_arms.ps1`). `--gate` and `--photometric` are
estimator-only and the tool **refuses** them under `--merge pyramid` rather than
ignoring them, so the pyramid arms use `--pyramid-gate 2.0` and no photometric
stage.

| row | backend | floor | sha256 |
|---|---|---|---|
| `…-unaligned` | estimator | — | `88712017FE31362F…` **= frozen, reproduced** |
| `…-unaligned` | pyramid | white | `C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65` |
| `…-unaligned` | pyramid | **measured** | `C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65` |
| `…-sidecar` | estimator | — | `52517FF8AE245F23…` **= frozen, reproduced** |
| `…-sidecar` | pyramid | white | `D28428A12601DA9EC388F1A02416C1E24E6BE8AF30A179F24ACD4FA8E7A38054` |
| `…-sidecar` | pyramid | **measured** | `ECF4390CC5DD90AE065D064339E59BDE35CA603C99CCCF46D8095749E657D090` |

**This is a specificity control pair, not two results.** The unaligned pyramid
arms are **byte-identical** — no warp runs, so `measure` is never called and the
floor is the constant, exactly as §3.3 says it must be. The sidecar pyramid arms
**differ**. The change moves precisely the render where a warp exists and moves
nothing else, which is the signature predicted from the call site before the
render: the probe is invoked in one place, the `FrameWarp::Placed` arm of
`load_frame`.

**Instrument bug caught by its own control.** The first version of
`freeze_arms.ps1` compared two empty strings when a render had failed and
printed `IDENTICAL` — a null that passes by not happening. It is now an explicit
`UNMEASURED` arm. Both frozen estimator hashes reproducing bit-exactly is what
licenses the pyramid rows above: it shows the harness rebuilds the registry's
own invocation correctly.

---

## 7. Files

| file | change |
|---|---|
| `crates/strehl-core/src/pyramid.rs` | `add_frame_with_gain`, `beta_for`; gate and hull margin read one helper |
| `crates/strehl-cli/src/merge_cmd/gatefloor.rs` | **new** — the per-frame probe |
| `crates/strehl-cli/src/merge_cmd.rs` | `load_frame` measurement site; `BandWorker` accumulation; banner `measured floor` line |
| `crates/strehl-cli/tests/byte-freeze.rs` | `STREHL_GATE_FLOOR` into `RENDER_ENV` |
| `scripts/check-defaults.py` | `STREHL_GATE_FLOOR` declared, `verified="measured"` |
| `experiments/BUILD-GATE/src/acuity.py` | the Q1 instrument, commissioned |
| `experiments/BUILD-GATE/src/matrix.ps1` | the arm matrix |
| `experiments/BUILD-GATE/src/freeze_arms.ps1` | the byte-level arms at a pinned commit |

---

## 8. Verification

| check | result |
|---|---|
| `cargo test --workspace` | **711 passed, 0 failed** (113 + 5 + 531 + 35 + 26 + 1) |
| both byte-freezes | **HOLD**, reproduced twice each |
| `cargo clippy --workspace --all-targets` | **81 warnings against an 81 baseline** measured at `e017c0bf` in a detached worktree — net zero introduced |
| `python scripts/corpus_lint.py --root .` | **OK — no violations** (also fixed a pre-existing `S4` mixed-line-ending violation on `merge_cmd.rs`) |
| `python scripts/check-defaults.py` | `STREHL_GATE_FLOOR` declared, `verified="measured"` |

