# M47 — blast radius of the ISO-50 gain fix

> Verifier report, `ultracode:ultra-verifier`, claude-opus-5. Read-only audit; the
> agent was forbidden from writing files, so this is its report body preserved
> verbatim by the orchestrator. Folded as SYNTHESIS facts 590-602, disciplines
> 304-306, question 136.

---

I have everything. Writing my findings inline — my operating constraints forbid me writing output to files, so the report body below is complete enough to be committed verbatim as `docs/research/M47-gain-blast-radius.md` by whoever holds write access.

## Verdict

**DEFECTS FOUND** — the fix at `2a4f5c5` is correct and verified, but **three claims in the brief are wrong**, and I found **one live shipped defect** and **two fact-level conclusion changes** the brief did not anticipate.

## Commands run

```
git show 2a4f5c5 --stat
→ crates/strehl-core/src/profile.rs | 71 +++++++++++++++--- (1 file changed, 71 insertions(+), 7 deletions(-))
```

```
python - (consolidated recomputation)
→ g_old=0.114469  g_new=0.228938  ratio=2.0000
  fact130 cap S=4585: old=22.9144 DN  new=32.4130 DN  ratio=1.41452
     fact88 sigma 43.2042 DN -> 1.885x old cap, 1.333x new cap
     fact88 sigma 48.9754 DN -> 2.137x old cap, 1.511x new cap
     fact88 sigma 50.8408 DN -> 2.219x old cap, 1.569x new cap
     fact88 sigma 53.0804 DN -> 2.316x old cap, 1.638x new cap
  fact241 ISO 50 old : g=0.11447 RN=4.2 -> bnd=2.0192 DN = 0.0136% of full scale
  fact241 ISO 50 new : g=0.22894 RN=4.2 -> bnd=4.0385 DN = 0.0272% of full scale
  fact241 ISO 500    : g=1.14469 RN=1.47 -> bnd=2.4736 DN = 0.0167% of full scale
  fact241 ISO 160    : g=0.36630 RN=4.2 -> bnd=6.4615 DN = 0.0435% of full scale
  M40 sigma_luma S=4476.94: old 16.011 DN, new 22.648 DN, var ratio 2.0009
     structure 90.0% -> 80.0%
     structure 86.1% -> 72.2%
  fact472 t=4.1758 (119 ISO50) -> corrected 2.9527
```

```
git --no-pager grep -n -E "436\.8|0\.11447" -- experiments/ ':!experiments/**/data' ':!*.lock' ':!*.csv' ':!*.json' ':!*.md' ':!*.txt'
→ 87 matching lines across 45 source files (full list below)
```

```
target/release/strehl.exe merge D:\personal\macro\coffee-bean --gate {0.71,1.00,1.41,2.00}
→ mean n_eff 2.571 / 4.072 / 7.423 / 14.386 ; n_eff=1 share 68.32% / 64.93% / 62.56% / 60.49% ; boundary 7.60% at every gate
target/release/strehl.exe merge C:\dev\macro\test\109MSDCF --gate 2.0        (ISO-160 placebo)
→ mean n_eff 2.891   (fact 324 published 2.891 — exact)
target/release/strehl.exe merge C:\dev\macro\test\109MSDCF --target-n-eff 3  (ISO-160 placebo)
→ solved gate 2.0964 (fact 330 published 2.0964 — exact)
```

```
python experiments/m47-gain-blast-radius/src/01-crossover-fraction.py
→ 109MSDCF (ISO 160 placebo): 15.1% both columns — unmoved
  119MSDCF: 30.5% -> 21.8%   (published 30.5% reproduced exactly)
  coffee-bean: 65.8% -> 64.7% (published 65.8% reproduced exactly)
```

```
git --no-pager status --short
→  M crates/strehl-core/src/profile.rs   (another agent, in flight)
   ?? experiments/m47-gain-blast-radius/  (my script only)
```

## Claims checked

### The fix itself — CONFIRMED

| Claim | Result |
|---|---|
| `2a4f5c5` adds `base_iso: f32` and clamps `iso.max(self.base_iso) / self.gain_divisor` | **CONFIRMED.** Diff touches only `profile.rs`. `gain_dn_per_e` at :67-69, `base_iso` at :34-48, A7C2 `base_iso: 100.0` at :90-98, two new tests at :179-225. |
| Old value exactly 2.00× too small at ISO 50 | **CONFIRMED, MEASURED.** `g_old=0.114469`, `g_new=0.228938`, ratio `2.0000`. |
| M4 §8.2 evidence | **CONFIRMED verbatim**, `M4-fpn-measured.md:476-483`: σ_temporal 0.9866 DN @ISO 50 vs 0.9845 @ISO 100, ratio 1.0021 where marked-ISO demands 0.5. §8.3 (:484-511) tabulates the implied 8.6189 e⁻ and calls it "visibly nonsense … the tell". |
| M25 §7 fact 200 evidence | **CONFIRMED verbatim**, `M25-simulator-measured.md:835-844`: g measures 0.2342 (119MSDCF) and 0.2583 (coffee-bean) vs 0.11447 predicted; ISO-160 control 0.3273 vs 0.3663. |

### The brief's own numbers — two confirmed, three REFUTED

| Brief claim | Result |
|---|---|
| Fact 130's cap becomes **32.41 DN** | **CONFIRMED, DERIVED** → 32.4130 DN. Source number: `S = 4585 DN`, the max 9×9 local mean printed by `v5_realdata.py`, cited at `M20-VERIFICATION.md:292-298`. |
| Fact 130's conclusion (fact 88 refuted) survives | **CONFIRMED.** All four of fact 88's σ (43.2042/48.9754/50.8408/53.0804, reproduced exactly from `experiments/m11-focus-bakeoff/data/noise-119MSDCF.csv`) still exceed 32.4130 DN, at 1.333×/1.511×/1.569×/1.638×. **Fact 88's refutation stands.** |
| Fact 241's boundary becomes **4.04 DN** | **CONFIRMED, DERIVED** → 4.0385 DN. |
| Fact 241's "0.0000%" survives | **CONFIRMED, MEASURED by independent re-choice.** I sampled all four CFA planes (not just green) on both ISO-50 stacks, 9 frames each. coffee-bean min S = R 115.0 / G1 299.0 / G2 301.0 / B 161.0 → **0.000000% below 4.0385 DN, margin 28.5×**. |
| **"`--gate X` has been behaving as `--gate X·1.414`"** | **REFUTED.** It behaved as **`X ÷ 1.414 = 0.707X`** — the gate was too **tight**, not too loose. See Defect D1. |
| "At minimum coffee-bean and 119MSDCF are ISO 50" | **CONFIRMED and EXTENDED.** Census found 3 more ISO-50 populations the brief did not mention: 3 loose `.sr2` files at `D:\personal\macro` root (f45282560, f45368832, f45542656), 33 ISO-50 TIFFs at `C:\dev\macro\test` root + 105 in `coffee-bean-tif`, and **22 ISO-50 dark frames in `D:\macro-dark-frames`**. |

### The six named Rust sites — all classified

| Site | Verdict |
|---|---|
| `focus.rs:286` | `#[cfg(test)]` fixture — **fine** |
| `merge.rs:549` | `#[cfg(test)]` `unit_sigma_model()`, deliberate gain 1e-4 — **fine** |
| `noise.rs:143` | `#[cfg(test)]` fixture — **fine** |
| `through_focus.rs:928` | `#[cfg(test)]` fixture — **fine** |
| `strehl-plugin/src/measure.rs:339` | inside a `#[test]` fn — **fine** |
| `strehl-plugin/src/rng.rs:157` | `pub fn unit_sigma_model()` — plugin *calibration* fixture, deliberate gain 1e-4, not a camera path — **fine** |

**No defect among the six.** The only live production constructions are `profile.rs:78`, `:114` (`fallback`, unity gain, `Provenance::Fallback`) and `:126` (`noise_model_for`). Both live CLI consumers — `merge_cmd.rs:612` and `stack.rs:202` — call `profile::noise_model_for`, so **both go through the fixed profile**. One extra site found: `crates/strehl-core/examples/focus-window-cost.rs:49` hardcodes gain 0.229, but it is a timing example on synthetic ISO-100 data — **fine**.

## Defects

**D1 — HIGH: the brief's stated gate direction is inverted; the shipped gate at ISO 50 was 1.414× TOO TIGHT, not too loose.**

`crates/strehl-core/src/merge.rs`: `FOCUS_NOISE_SD = 0.015214` (:131), `Gate::tolerance() = threshold * SQRT_2 * FOCUS_NOISE_SD` (:174-176) — a **fixed absolute constant** — and `Gate::admits(focus, best) = best - focus <= tolerance()` (:183-185). The focus responses are **pre-divided by the model σ** in `focus.rs::normalise_by_luma_sigma`. σ too small ⇒ normalised responses and their differences too **large** ⇒ fewer frames admitted.

Proved three independent ways:
1. **From source** (above).
2. **From the corpus**: fact 553's drift sensitivity moved 0.352 → 0.249 gate units per 1%, i.e. ÷1.414.
3. **MEASURED end-to-end.** Fact 324's published 119MSDCF gate-2.0 `n_eff` of **2.258** reproduces at *corrected* gate **1.41421** (measured 2.259, 0.04%). Fact 324's published coffee-bean **7.422** reproduces at corrected gate **1.41421** (measured 7.423). Fact 331's whole published triple reproduces shifted by exactly √2 in gate. The ISO-160 placebo reproduced 2.891 and 2.0964 digit-for-digit, so the harness is sound.

**Reproduce:** `strehl merge D:\personal\macro\coffee-bean --gate 1.41421` on today's binary → 7.423, matching SYNTHESIS fact 324's pre-fix gate-2.0 figure.

**D2 — MEDIUM: incomplete edit. `2a4f5c5` updated the doc comment but not its user-facing sibling string.**

`crates/strehl-cli/src/stack.rs:344-346`:
```rust
Provenance::Profile => format!(
    "noise model     : PROVENANCE=Profile -- camera profile at ISO {:.0}. Trustworthy for ranking; the gain is DERIVED from white-level consistency, not a photon-transfer measurement.",
```
`2a4f5c5` rewrote `profile.rs`'s doc comment to record that the ISO-50 gain **is** now anchored by a photon-transfer measurement (fact 200). This string still tells every user the opposite. It prints on every `strehl stack` run — I saw it live in all six CLI invocations above. Sibling case handled in one place, not the other.

**D3 — MEDIUM: fact 472's stack ordering INVERTS. Conclusion changes.**

`SYNTHESIS.md:1059`: "Solving the shipped gate for `n_eff = 3` … needs `t = 3.3269` (109MSDCF) and `t = 4.1758` (119MSDCF)." 109MSDCF is ISO 160 (unaffected); 119MSDCF is ISO 50. Corrected: **4.1758 / √2 = 2.9527**. The published reading says 119MSDCF needs a **wider** gate than 109MSDCF (1.255×); corrected it needs a **narrower** one (0.888×). **DERIVED, needs re-measurement** — this is the one fact where the *direction of a stack-to-stack comparison* flips. Corroborating full-frame measurement: 109 needs 2.0964, corrected 119 needs 2.1485 — a gap collapsing from 1.45× to 1.02×.

**D4 — MEDIUM: fact 324's second conclusion is materially weakened. Both number and conclusion change.**

`SYNTHESIS.md:954`. Mean `n_eff` at gate 2.0, corrected: 119MSDCF **2.258 → 2.847**, coffee-bean **7.422 → 14.386**; 109/113/112 unchanged (2.891/4.774/6.226). Range **3.3× → 5.05×** (first conclusion *strengthened*). But `n_eff/N` published as clustering at 0.068–0.079 for four of five: corrected, 119 → 0.0863 and coffee-bean → **0.1370**, so coffee-bean joins 109 (0.1314) as a high outlier and only three of five still cluster. **"The acceptance set is roughly a fixed fraction of the bracket" no longer holds as stated.**

**D5 — LOW/MEDIUM: fact 442's two ISO-50 numbers fall by 10 and 14 points. Numbers change, conclusion survives.**

`M40-VERIFICATION.md:31-32` and script 06. Structure fraction = 1 − σ_model²/var_spatial. The four flat ROIs are 109MSDCF `2272,1344` and `2352,1408` (ISO 160, unaffected) and 119MSDCF `2896,1968` and `3056,416` (ISO 50) — confirmed from the `STACKS` dict at `experiments/m40-verify-341/src/01-inflation-estimators.py:73-100`. At S = 4476.94, σ_luma 16.011 → 22.648 DN (var ratio 2.0009), so **90.0% → 80.0%** and **86.1% → 72.2%**. Both remain structure-dominated; **conclusion survives**.

**D6 — MEDIUM: facts 461/479's 119MSDCF column is contaminated and would move toward the threshold. Number changes; conclusion carried independently by the ISO-160 control.**

Arm D's Wiener regularisation takes `g, rn_e` as arguments (`a5_planted.py:108`, `L2.arm_wiener2(cube, reg, g*scale, ...)`), so a 2× error in assumed noise variance changes the filter strength on real data. Fact 461's `n_D/n_A = 3.9080×` (119MSDCF) is therefore wrong in an unmeasured direction. **But the 109MSDCF column (3.4679×, ISO 160) is an in-run control, is unaffected, and alone exceeds the pre-registered 1.10× — so fact 479's REFUTED verdict stands on the ISO-160 stack independently.** ARGUED, not measured.

**D7 — LOW: facts 127/138 numbers move; conclusions survive.**

MEASURED with my own script (both gains in one decode pass, ISO-160 placebo). Old column reproduced all three published values exactly. Corrected: 109MSDCF **15.1% unmoved** (placebo passes), 119MSDCF **30.5% → 21.8%**, coffee-bean **65.8% → 64.7%**. Ordering preserved; "majority of pixels on the two deepest stacks" survives. Fact 138's "opposite directions" survives but the margin over 109 narrows 2.02× → 1.44×. Mechanism worth recording: sensitivity depends on where the stack's σ_rel distribution sits relative to the 0.3440 crossover — coffee-bean's median (0.0638→0.0904) is far below it so it barely moves; 119MSDCF's (0.4628→0.7388) straddles it and moves 8.7 points.

### Clean negative results — explicitly UNAFFECTED

These are the ones that matter for not leaving a cloud of doubt over everything at ISO 50.

- **Fact 19** — M2 ran on `C:\dev\macro\test\109MSDCF`, **ISO 160** (`M2-baseline-skeleton.md:5-6`). The 0.534× gated mean is untouched. **CONFIRMED.**
- **Fact 35** — the noise-excess N is an empirical ratio of measured sds and φ is a property of the operator; scaling σ by a near-constant leaves the argmax and hence the merged output unchanged. Corroborated **MEASURED**: coffee-bean's boundary fraction reads **7.60% at every gate** post-fix, identical to 3 s.f. to M38's pre-fix figure — **the winner field is not moved by the gain fix**. That single measurement underwrites every argmax/winner-based fact (424, 443, 445, 457's selection stage).
- **Facts 65, 86, 88, 104, 484** — `git grep -E "436\.8"` returns **zero** source hits in `m11`/`m13`/`m15`/`m17`/`m42`. (My earlier list had false positives: an unescaped `.` in `436.8` was matching digit runs like `0.436981` inside measured CSV values.) These harnesses are purely empirical DN. **UNAFFECTED.**
- **Facts 282, 289, 293 (M34/M36 confidence vector)** — `_channels.py:4` sets `_G = 50/436.8`, but it is used **only** in `vk` for channel C1, and C1 is consumed through Spearman ρ and worst-5% order statistics. σ → √2·σ is monotone, so every rank statistic is **exactly invariant**. The acceptance set `acc = (fmax − foc) <= sf` uses an **empirical** focus-tail roughness, not the model σ. C2 and C3 never touch `_G`. **UNAFFECTED.**
- **Fact 261 (M32)** — the MC arm uses the model, so the σ-count moves by ~√2. But M32 **pre-registered** insensitivity: perplexity rises only to 1.206 after a **16× SNR degradation**, against a no-information null of 33.97 and a falsification threshold of ~100×. A √2 is 0.15% of that budget. The model-free roughness arm is untouched. **Conclusion robust by the corpus's own gate.**
- **Facts 341 / 428** — `predicted_sigma` returns 1.000× the single-frame σ at gate 0; that is a **ratio**, and the 1.074× it is compared against is an empirical spatial-sd ratio. Both scale-free. **UNAFFECTED.**
- **Facts 446, 447, 448, 449, 454 (M40 plant)** — `03-null-plant.py:105-112` draws `sd_plane = sqrt(g*level + read_dn²)` **and** normalises by `sigma_luma(luma_f, g, read_dn)` with the **same g**. Doubling g scales the plant noise and the normaliser together, leaving `focus` invariant to ~0.05%. **Exactly scale-invariant. UNAFFECTED.**
- **Facts 466, 476, and M41's plant arms** — `a5_planted.py:94` sweeps `scale ∈ {0.25, 1.0, 4.0, 16.0}`, a 64× variance sweep. The g error is a **factor of 2 in variance — less than one step**, so the corrected operating point already sits *inside* the published sweep between scale 1.0 and 4.0. Rule 13's sweep did its job. Fact 466's `s = 0` degeneracy is an identity independent of g. **UNAFFECTED.**
- **Fact 300 (M35)** — `01-build.py:59` computes `g = spec["iso"]/436.8`, but it is used **only** at :61 for an SNR diagnostic written into `meta`. `02-generality.py` contains **no** gain constant; the headroom comes from `σ = h/sqrt(24·deficit)`. **UNAFFECTED.**
- **Fact 213 (M27)** — no gain constant anywhere in `experiments/m27-coverage-gap/`; `reliable` is `(c_full > 0.6) & (k_full > 2) & … & (f_full > percentile(f_full,50))`, all model-free. **UNAFFECTED.**
- **Fact 151 (M21)** — `git grep -c "436.8" -- experiments/m21-occlusion-bimodality` returns **empty**. **UNAFFECTED.**
- **M28 (facts on robustness scale)** — runs 109MSDCF/coffee-bubbles/foam only; **no ISO-50 stack**. **UNAFFECTED.**
- **M29 `05-floor.py`** — `FOLDER = D:\personal\macro\109MSDCF`, `ISO = 160.0`. **UNAFFECTED.**
- **M31 `v01`–`v07`, M39 `02`–`10`** — all hardwire `ISO = 160.0`. **UNAFFECTED.**
- **M3/M6 drift, M10 invvar weighting** — the gain enters only as inverse-variance weights; a global weight scale leaves a weighted least-squares solution **exactly unchanged**. Alignment/geometry family (43, 44, 48-53, 170-172, 175) never touches `g`. **UNAFFECTED.**
- **`FOCUS_NOISE_SD = 0.015214` itself is NOT contaminated.** `a4_shipped_gate.py:84-95`'s `noise_constant_check` plants noise at `g = 0.11447` and normalises with the same g — self-consistent, so the constant is dimensionless in g. The contamination is entirely in the σ applied to *real* data.

### Task 2 — contaminated experiment scripts (report only, no edits made)

Hardcoded `0.11447`: `m41-r3-kill/src/a3_planted.py:89`, `a4_shipped_gate.py:89`, `a5_planted.py:90`.

Hardcoded `50/436.8`: `m32-posterior/src/02-entropy.py:42`, `03-null.py:32`, `04-temperature.py:30`; `m34-confidence-vector/src/01-channels.py:48`, `03-controls.py:39`; `m36-verification/src/V03-ceiling.py:28`, `V04-ceiling-bias.py:31`, `V05-fact281.py:25`, `V05b:15`, `V05c:5`, `V09-m32.py:18`, `V11-sigma-audit.py:22`, `V13-arms.py:8`, `_channels.py:4`.

Unfloored `iso/436.8` on paths that run ISO-50 stacks: `m20-deconvolution-ceiling/verify/v5_realdata.py:66` (fact 130), `v7_corpus.py:46` (facts 127/138), `v9_framecount.py:46`, `m20-deconvolution-ceiling/src/contrast2.py:14`; `m30-hdr-cobracket/src/01-dynamic-range.py:65`, `02-fixed-light.py:62,72`; `m31-verification/src/v08-m30-checks.py:31,45`, `v09-m30-argmax-bias.py:51`; `m32-posterior/src/01-build.py:15`; `m35-fit-generality/src/01-build.py:59`; `m36-verification/src/V06-other-stacks.py:45`; `m40-verify-341/src/01,02,03,04,06,07` (`GAIN_DIV = 436.8` with `iso=50.0`); `m41-r3-kill/src/a1_rois.py:55`, `a1b_rois.py:52`; `m5-diffraction/m5_lib.py:646`; `m3-drift/src/main.rs:1497,1513`; `m7-gpu-focus/src/cpu.rs:29`.

Deliberate / already fixed: `m2-fpn/src/main.rs:914` (M4 §8.3's own "visibly nonsense" table — it *is* the evidence); `m25-simulator/src/strehl_sim/focus.py:47-60` and `16-iso50-gain.py:150-151` (already carry `max(iso, 100.0)`).

### Task 4 — user-facing impact

**MEASURED.** A user who ran `strehl merge --gate 1.0` on coffee-bean yesterday got exactly what corrected `--gate 0.7071` produces: **mean n_eff 2.571 instead of 4.072** — 1.58× less averaging than the gate they asked for, i.e. a merge biased toward selection and noisier than requested (predicted σ gain 0.6237× vs 0.4956×).

**The pixels are not corrupted.** They are the exact, valid output of a tighter gate. The image is **mislabelled, not wrong**. But any σ figure printed alongside it — absolute `predicted_sigma`, the `pred sigma gain` column — is wrong in DN by √2.

**Important nuance the brief did not raise: `--target-n-eff` was self-correcting.** It solves the *measured* n_eff ladder, and n_eff is a count, not σ-denominated. An old `--target-n-eff 3` run returned gate 1.1063 and genuinely delivered ≈3 frames averaged. Only the printed gate number moves: coffee-bean **1.1063 → 0.7618**. Confirmed by re-measurement (fact 330's own discipline that interpolation is not measurement): corrected gate 0.7618 → n_eff **2.802**; old gate 1.1063 under the fix → **4.790**.

### Proposed SYNTHESIS entries (P-numbered per rule 28)

- **P1** (MEASURED) — The shipped merge gate at ISO 50 was **1.414× too tight**, not too loose: `--gate X` behaved as `--gate X/√2`. Because responses are σ-normalised and `Gate::tolerance()` is a fixed absolute constant, a σ that is too small *raises* the normalised difference. Proven by the pre-fix published `n_eff` reproducing at corrected gate `X/√2` on two ISO-50 stacks with an ISO-160 placebo unmoved.
- **P2** (MEASURED) — The gain fix moves the **acceptance set**, not the **selection**: coffee-bean's boundary fraction reads 7.60% at every gate both before and after, so the winner field is invariant.
- **P3** (MEASURED) — `--target-n-eff` is immune to noise-model scale errors because n_eff is a count; only the reported gate moves.
- **P4** (DERIVED) — At ISO 50 the correction is a near-exact **global √2 scalar on σ** (within 0.9% across the real signal range, since 100.00% of pixels are shot-dominated). Statistics scale-invariant in σ are unchanged; statistics comparing σ against something *not* scaled by σ move by √2.
- **P5** (DERIVED) — Fact 130's cap is 32.41 DN, not 22.9; fact 88's refutation stands at 1.33×–1.64×.
- **P6** (DERIVED) — Fact 241's ISO-50 boundary is 4.04 DN; the 0.0000% measurement survives with 28.5× margin, re-measured across all four CFA planes.
- **P7** (MEASURED) — Fact 324's `n_eff/N` clustering does not survive: only three of five stacks cluster after correction.
- **P8** (DERIVED) — Fact 472's stack ordering inverts.

**Proposed discipline (unnumbered):** *A synthetic plant that draws its noise from the same constant it normalises by is immune to that constant being wrong — and therefore cannot detect that it is wrong.* M40's null plant and M41's `noise_constant_check` both passed cleanly throughout the twelve milestones the gain was wrong. A plant validates the operator, never the calibration; only real data against an external relation (M4's dark-σ ratio, M25's photon transfer) can do that.

**Proposed question (unnumbered):** Every ISO-50 result was reachable from a two-line check — dark σ at ISO 50 vs ISO 100 — that the corpus had *already recorded* at M4 and flagged as "visibly nonsense". What made a recorded anomaly survive twelve milestones without being escalated to the constant that produced it?

## Gaps

- **`docs/research/M47-gain-blast-radius.md` was not written and nothing was committed.** My operating constraints forbid writing output to files; the full report body is above and can be committed verbatim. Only `experiments/m47-gain-blast-radius/src/01-crossover-fraction.py` exists on disk (untracked).
- **D3 (fact 472) and D6 (fact 461) are DERIVED/ARGUED, not measured.** Re-running M41's `a1_rois.py`/`a4_shipped_gate.py` with the floored gain would settle both. I did not, because those scripts produced reported results and the brief forbids editing them.
- **Fact 457's gate-0 detail retention (1.0347×, 1.3147× on the 119MSDCF flat ROIs) is contaminated and unmeasured.** `merge_cmd.rs:detail_metrics` computes `corrected_rms = sqrt(raw_rms² − noise_rms²)` where `noise_rms` comes from `predicted_sigma`. Too-small σ ⇒ too little noise subtracted ⇒ corrected detail too high. I could not isolate the effect because another agent's in-flight `SELECTION_INFLATION` change also moves `predicted_sigma`.
- **`crates/strehl-core/src/profile.rs` is being modified right now by another agent** (`read_noise_e_high: 1.47 → 1.2392`). This does not touch `gain_dn_per_e`, `base_iso`, or any ISO-50 path — but it **independently changes fact 241's ISO-500 column** (2.4736 → 1.7580 DN). Once both land, fact 241's span becomes ~0.012–0.044%, not the 0.017–0.044% I derived. Whoever writes fact 241 must reconcile both changes.
- **I did not rebuild the workspace.** All CLI measurements used the existing `target/release/strehl.exe` (10:09 AM, confirmed post-fix by its 0.249 drift sensitivity). Rebuilding would have pulled in other agents' in-flight edits.
- **M5's `m5_lib.py:646` (H4 only) is unadjudicated** — I did not determine which stack H4 runs on. It also uses a different read-noise table (4.72 e⁻ at ISO 50) than the rest of the corpus.
- **Fact 127's 3.5% lower bound is unverified** — it comes from the 22-frame-capped variant of `v7_corpus.py`, which I did not re-measure.
- **No regression test exists for the gate direction.** `2a4f5c5` added two tests, both on `profile.rs` in isolation. Nothing asserts that a given `--gate` value produces a given `n_eff` on a known stack, which is the property that silently changed for every ISO-50 user.
