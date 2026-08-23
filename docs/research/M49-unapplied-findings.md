# M49 — the research-to-code gap

> Verifier report, `ultracode:ultra-verifier`, claude-opus-5. Read-only audit; the
> agent was forbidden from writing files, so this is its report body preserved
> verbatim by the orchestrator. Folded as SYNTHESIS facts 575-589, disciplines
> 298-303, questions 133-135.

---

I have completed the audit. Below is the full deliverable, in my required format, with the M49 report body inline.

---

## Verdict

**DEFECTS FOUND** — and one procedural finding that changes how the rest should be read: **the tree moved under me mid-audit.** HEAD advanced `b402977` → `ce92597` and two of the three files at issue were rewritten by other agents while I was reading them.

---

## Commands run

```
cd C:\dev\blog\death-of-software\projects\strehl; git --no-pager log --oneline -6
→ ce92597 M25 section 11: pre-register the multi-scale occluder test (question 132)
  2474e5d M46 pre-registration: is there an admissible detail metric on this sensor?
  2243995 M25 was right: I blamed a detector using a plant that had just failed on that axis
  b402977 M51: the unverified backlog is 101 findings, 18 of them shipped
```

```
git --no-pager show HEAD:crates/strehl-core/src/merge.rs | Select-String 'SELECTION_INFLATION: f32 ='
→ pub const SELECTION_INFLATION: f32 = 1.074;

Select-String -Path crates\strehl-core\src\merge.rs -Pattern 'SELECTION_INFLATION: f32 ='
→ crates\strehl-core\src\merge.rs:110:pub const SELECTION_INFLATION: f32 = 1.0;

(Get-Item crates\strehl-core\src\merge.rs).LastWriteTime → Sunday, August 23, 2026 11:03:18 AM
```

```
Select-String -Path crates\strehl-core\src\focus.rs -Pattern 'WINDOW_RADIUS: usize|\.sqrt\(\)'
→ 83: pub const WINDOW_RADIUS: usize = 13;
→ 160:             out[y * w + x] = (gx * gx + gy * gy).sqrt();
   (focus.rs is CLEAN in git status — this is HEAD)
```

```
Select-String -Path crates\strehl-core\src\profile.rs -Pattern 'read_noise_e_high|gain_divisor|base_iso'
→ 92: gain_divisor: 436.8,
→ 93: base_iso: 100.0,
→ 95: read_noise_e_high: 1.47,
→ 96: second_base_iso: 400.0,
   (profile.rs is CLEAN in git status — M48 has NOT landed)
```

```
cargo test --workspace                       [11:03:00, and again 11:04:48, and again 11:05:07]
→ test result: FAILED. 102 passed; 2 failed
  merge::tests::the_selection_penalty_is_absent_until_it_is_measured ... FAILED
  through_focus::tests::predicted_sigma_is_the_calibrated_model_with_no_selection_penalty_yet ... FAILED

cargo test -p strehl-core --lib the_selection_penalty_is_absent
→ test result: ok. 1 passed; 0 failed; 103 filtered out

$env:RUSTFLAGS='--cfg m49_audit_probe'; cargo test --workspace     [11:05:24 → 11:05:57]
→ Compiling strehl-core / strehl-plugin / strehl-raw / strehl-cli
→ test result: ok. 37 passed
→ test result: ok. 104 passed
→ test result: ok. 33 passed
→ test result: ok. 8 passed
→ test result: ok. 1 passed        (183 total, 0 failed, 0 ignored)
```

```
python (inline) — extract SYNTHESIS §4 between "## 4. " and "## 5. "
→ 357 fact rows, numbers 1–566, zero duplicate numbers

python (inline) — cross-check every `fact N` citation in crates/**/*.rs against §4
→ 58 distinct fact numbers cited in code; 0 cited numbers absent from §4
  (this is the check that FAILS to catch the profile.rs collision — see Defect 10)
```

```
Select-String -Path crates\*\src\*.rs -Pattern '^\s*(pub )?const [A-Z_0-9]+\s*:'
→ 50 const declarations (full inventory in the report body below)

rg -i '\b(align|warp|register|homograph|affine|translat)\w*' crates/strehl-cli/src/merge_cmd.rs
→ 2 hits, both the English word "Registered" in prose. No alignment code exists.
```

---

## Claims checked

| Claim I was given | Result | Evidence |
|---|---|---|
| `SELECTION_INFLATION = 1.074` at `merge.rs:87` is refuted and still shipped | **CONFIRMED at HEAD, REFUTED as a description of the working tree** | `git show ce92597:...merge.rs` → `= 1.074`. Working tree at 11:03:18 → `merge.rs:110 = 1.0`, with a new test `the_selection_penalty_is_absent_until_it_is_measured` (merge.rs:679) and a rewritten `through_focus.rs:1883` assertion. M18 is landing the revert **right now**. My method caught it; I also caught that the premise is 90 minutes stale. |
| `WINDOW_RADIUS` still 13 and the operator is still the magnitude form | **CONFIRMED, but the framing needs correcting** | `focus.rs:83` = 13, `focus.rs:160` = `(gx*gx + gy*gy).sqrt()`. File is clean in git. **However:** fact 60's own consequence column says "Use a 27×27 box", it is marked **VERIFIED**, and fact 483 reads *"For `\|grad\|` it is 6/6 → w13 with zero spread."* w13 is the correct radius **for the shipped operator**. The un-applied item is the *operator*; the radius follows it. OWNER-QUESTIONS' own correction agrees: "not a shipped-default defect". |
| `read_noise_e_high = 1.47` is +18.4% and M48 owns the fix | **CONFIRMED not-applied; M48 has not landed** | `profile.rs:95` = 1.47, file clean in git at 09:40:42. Fact 557: 1.2414 e⁻ RMS basis → +18.4%. |
| "Finding only these two means you found nothing new" | **8 further NOT APPLIED items found**, listed below | |
| A systematic mechanism exists beyond the two diagnosed | **YES — a third, distinct one, and I can name it** | See §5 of the report body. |

---

## Defects

### CRITICAL — the workspace is red at this moment, and it can be *made* to look green

`cargo test --workspace` at 11:03, 11:04:48 and 11:05:07 all returned **2 failures**. The identical test run with a filter (`cargo test -p strehl-core --lib the_selection_penalty_is_absent`) **passed**. The failures were cargo fingerprint staleness: M18 wrote `merge.rs` at 11:03:18 *while cargo was compiling it*, so the workspace-feature artefact was fingerprinted against the pre-write file and cargo considered it fresh. Forcing a fresh fingerprint with `RUSTFLAGS='--cfg m49_audit_probe'` gave **183/183 green in 33 s**.

This matters beyond today: in this repo a "workspace tests pass" claim from an agent that did not force a rebuild is **not evidence**. The failure was silent, reproducible three times, and pointed at a real file and line number that was not actually wrong.

### The ranked NOT APPLIED table

Ranked by effect on **output**, worst first. "Sizable" means the number is quoted from a measured fact or derived from one; "not sizable" means it needs a run I did not perform.

| # | Finding | File:line (read by me) | Discrepancy in its own units | Fact | Effect on output |
|---|---|---|---|---|---|
| 1 | **The flat-ROI acceptance invariant is computed from a statistic the corpus forbade for this purpose.** `flat_roi_stats` returns `stacked_sigma / single_sigma`, a ratio of two **raw spatial** sds against one arbitrary reference frame (`frames.len()/2`). This *is* ACCEPTANCE INVARIANT 1. | `strehl-cli/src/stack.rs:681`, consumed at `merge_cmd.rs:978-991` | Under-reports a noise explosion by **6.3×** (22.767× raw vs 144.391× high-pass). Takes a **1.60× range** over the free choice of denominator frame (1.0000–1.5989 on 119MSDCF). Reference frames are **50.9–90.0% scene structure** by variance. | 469, 441, 442, 455 | **Sizable, and it is the worst thing here** — not because it changes pixels but because it is the gate that would have caught everything else changing pixels. A 6.3× under-report means a merge could get 6× noisier and still print PASS. |
| 2 | **`read_noise_e_high = 1.47`** | `strehl-core/src/profile.rs:95` | +18.4% (RMS basis) / +36.5% (typical-pixel basis) vs 1.2414 / 1.0772 e⁻ | 557 | **Sizable, and smaller than it sounds.** DERIVED by me: g(100)=0.228938; read term 1.47·g=0.336539 DN vs 1.2414·g=0.284205 DN. σ moves **−15.6% at S=0**, **−0.68% at S=10 DN**, **−0.07% at S=100 DN**. Fact 241 measured **0.0000%** of pixels below the read-noise boundary on three stacks. So on this corpus the merged output barely moves. Contrast the gain defect: 41.4% in σ, 23.68% of subpixels. |
| 3 | **`read_noise_e_low = 4.20` has an un-owned shape error.** Fact 557's second clause: −2.3% at ISO 100 but **+10.4% at ISO 200** and **+11.4% at ISO 250**, and "no scalar can fix" it. M48 is named as owning `read_noise_e_high`. **Nobody is named as owning this.** | `strehl-core/src/profile.rs:94` | +10.4 / +11.4 pp at ISO 200/250 | 557 | Sizable at those ISOs; the corpus has no ISO 200/250 stack, so effect on shipped output today ≈ 0. Flagged because it is the exact shape of the two defects that started this audit. |
| 4 | **The clip mask never reaches the focus volume or the gate.** Fact 203's consequence is "Mask samples at/above the container max **before the focus volume** and propagate the mask". `green_luma_with_clip` deliberately writes luma **identical** to `green_luma`; `Estimator::fold` takes no clip parameter. The mask reaches only the `--stats` confidence union (`merge_cmd.rs:1631/1634/1693`) and the census (`merge_cmd.rs:1160`). | `strehl-core/src/plane.rs` (`green_luma_with_clip`), `strehl-core/src/merge.rs` (`Estimator::fold`) | Always-clipped pixels read cross-frame focus contrast **1.0000 — its maximum** — against 0.5398 never-clipped, at pixels carrying zero information. n=616 measured. | 203 | **Sizable in population, not yet in DN.** `coffee-bean` 1.26% of pixels ≥15360; `coffee-bubbles` 62,054 pinned at container max. On `109/119/112/113` it is **zero**. Fact 203 calls it "a maximum-severity hole". |
| 5 | **`SELECTION_INFLATION = 1.074`** (at HEAD only) | HEAD `ce92597` `merge.rs:87`; worktree `merge.rs:110` now `1.0` | Refuted on four independent grounds: no defined meaning (units), exceeds its own 1.0451× ceiling, spans 0.9841–1.2732 across six ROIs, drove the corrected metric to **−11.63 DN where truth is 0** | 440, 443, 446, 454, 455 | Being fixed as I write. |
| 6 | **`selection_inflation(n>1)` is a step where the measurement is a smooth decay.** Retained in the worktree revert (both branches now 1.0). | `strehl-core/src/merge.rs:107` | Measured 1.0770/1.0591/1.0454/1.0383/1.0319/1.0293/1.0286/1.0220 for n=1..8 | 448, 458 | Sizable: a **7.4-point discontinuity** through the **41.66%** of the plane at n=1. The worktree doc now states this explicitly and keeps the shape deliberately — this is *documented* not-applied, which is the honest state. |
| 7 | **`merge_cmd.rs:936` prints Jensen's inequality as a result.** Prints `1.0 / mean.sqrt()` — i.e. `1/sqrt(mean n)` — under the header "pred sigma gain 1/sqrt(n)". Never calls `predicted_sigma`. | `strehl-cli/src/merge_cmd.rs:936` (fact 452 cites `:912`; **the line has drifted, the content matches verbatim**) | Understates `mean(1/sqrt(n))` by **4.22 / 5.88 / 4.70 / 2.43 %** at gates 0.5 / 1.0 / 2.0 / 4.0 | 452, 453 | **User-facing only** — I read the call site; the value goes to `eprintln!` and nowhere else. It reports a *better* noise gain than the merge achieves. |
| 8 | **The CLI prints a baseline its own corpus could not reproduce.** `"PASS is <= 1.000x. The argmax baseline measured 1.253x here (fact 19/23)"` | `strehl-cli/src/merge_cmd.rs:990-991`; same claim at `merge.rs:4` and `merge.rs:10`; `strehl-cli/src/stack.rs:613` | Fact 343, same 22 frames, same flat ROI, shipped operator: **1.0678× unregularised, 1.0739× regularised**. 1.253 overstates the baseline by **1.173×**, inflating the headline win from a defensible **17%** to a printed **29%**. | 343 (which explicitly QUALIFIES 320) | User-facing only. The word "here" makes it a claim about *this ROI*, which is precisely what fact 343 measured and refuted. |
| 9 | **The refuted `k = 5.94` is still printed twice and asserted twice in prose.** | `merge_cmd.rs:1398`, `merge_cmd.rs:1464`; prose at `through_focus.rs:124` ("**5.94x larger than FOCUS_NOISE_SD**, and that is the whole trade") and `:514`; worked example at `strehl-plugin/src/lib.rs:18` | Fact 500: dividing 0.090400 (unregularised) by 0.015214 (regularised) "mixes a window-radius change with the presence of a 17×17 box". Honest quantity = 0.027613 → **k = 1.815**. Overstatement **3.273×**. | 500 (supersedes 437) | User-facing only. **The constant `FINE_FOCUS_NOISE_SD = 0.090400` is CORRECT as consumed** — the fine field is deliberately unregularised and `bimodality_sigma` divides by `√2 · FINE_FOCUS_NOISE_SD`. Only the ratio and the inference from it are refuted. This distinction matters and is easy to get wrong. |
| 10 | **`profile.rs` cites a fact number that resolves to a different fact.** Doc comments at `profile.rs:25, 40, 45` cite "M25 fact 200" / "fact 200a". §4 fact 200 is **M26's white-balance row**. M25's report-local fact 200 folded as **§4 fact 550**. | `strehl-core/src/profile.rs:25, 40, 45` | A silent collision: my automated check "is every cited number a real §4 fact?" returns **clean**, because 200 *is* a real fact — about something else. | rule 28 | Not sizable; it is a booby trap for the next auditor. Note this is in a file about white balance *and* gain, so the wrong reading is locally plausible. |
| 11 | **`--target-n-eff` cannot produce an image.** `--out` requires exactly one `--gate` (`merge_cmd.rs:582-588`) and writes `p2.est[0]` (`merge_cmd.rs:894`). `report_target_solve` (`merge_cmd.rs:183-226`) interpolates over the requested rungs and prints *"Re-run with --gate {g} to confirm"*. | `merge_cmd.rs:582-588`, `:894`, `:183-226` | Fact 324: "The threshold must be **solved per stack** against a target n_eff." At gate 2.0 mean n_eff runs 2.258 / 2.891 / 4.x across stacks. | 324 | **Not sizable without a run.** The honest reading: the solver exists, is correctly labelled INTERPOLATED, and is not wired to the output path. A user producing an image is always using a fixed, non-transferable gate. |
| 12 | **The fact-502 calibration seam is built, tested and off the shipped path.** `crates/strehl-cli/Cargo.toml` does **not** depend on `strehl-plugin`. `Gate::tolerance()` uses the compiled-in `FOCUS_NOISE_SD`. | `crates/strehl-cli/Cargo.toml` (read in full) | Fact 439: across seven operators the constant the gate is denominated in spans **10.4×** (0.644 to 6.680). | 502, 436, 438, 439 | Not sizable today — no third-party operator ships. It is load-bearing the moment the tenengrad-sq triple lands (fact 509: **1.528×** silent gate rescale). |
| 13 | **The `tenengrad-sq` operator was never landed.** | `focus.rs:83`, `focus.rs:160` | Fact 511 verbatim at HEAD. Fact 483: 0/6 subsets choose w13 for tenengrad-sq. | 103, 104, 483, 490, 511 | **Sizable, and it is small.** Fact 104 is explicit: candidate (c)'s quality gain is **not robust** — 15/30 cells, median paired Δ −0.27 DN, **sign test p = 1.00**; "sell as quality-neutral, never as a quality win". Fact 490: w13→w11 costs +0.0041 N (0.38%). The un-applied consequence is the **blind spot** (fact 73: exactly zero focus discrimination on an untextured monotone edge), not general sharpness. **NOT APPLIED is currently the safe state**, because fact 509 makes a partial application a 1.528× silent gate error. |

### Two things I checked that turned out to be APPLIED, against my expectation

- **`gain_divisor = 436.8` is *not* a fourth wrong sensor constant.** I opened `M25-simulator-measured.md` §5.9 (rule 31) rather than trusting the code comment. The primary table reads `109MSDCF | 160 | measured g 0.3273 | −10.7%`. §4.1's own licence row says **"Keep — the relation survives it at true gain steps"**, and §10 item 8 says "**Only the slope is trustworthy**: the intercept is inflated by residual scene texture". So the corpus's decision was *keep*, and keep is what shipped. DERIVED sizing if it ever moves: 0.3663/0.3273 = **+11.92%** in g → σ ∝ √g → **+5.79%** in σ → gates run **5.5% tight**.
- **The ISO-50 fix is present and asserted at the right value.** `profile.rs:68` `iso.max(self.base_iso) / self.gain_divisor`, `base_iso: 100.0`, and a test `extended_iso_reads_out_at_base_gain` asserting the exact 2.05×. Rule 30 satisfied — the tolerated wrong case is asserted, not carved out.

### Unlicensed constants — every numeric literal that materially affects output

I enumerated all 50 `const` declarations plus the material inline literals. **Licensed** (I read the fact and the code): `REGULARISER_RADIUS = 8` → 17×17 (facts 84, 86, 36, 42); `FOCUS_NOISE_SD = 0.015214` (fact 509 confirms provenance: `|grad|` at w13 under r8); `WINDOW_RADIUS = 13` (fact 60, VERIFIED, for the shipped operator); `FINE_WINDOW_RADIUS = 2` (facts 152, 425); `TOP_K = 4` (fact 422); `FINE_FOCUS_NOISE_SD = 0.090400` (measured in-crate); `CONTAINER_MAX_DN = 16383` vs `white = 15360` (fact 202, with `usable_white_level_is_not_the_container_maximum` at `noise.rs:188` and `clip.rs:32` forbidding unification); `PROCESS_FLOOR_BYTES = 15_099_494` = 14.4 MiB and `DECODER_SCRATCH_BYTES = 38_797_312` = 37.0 MiB (facts 33, 22, 34); `bytes_per_pixel()` = **60** — I added the terms by hand: 2+4+12+4+16+8+4+2+8 = 60, matching fact 421; `DEFAULT_SPECKLE_TOLERANCE = 2` (fact 23's reference points are quoted at this tolerance, and the doc says so); `confidence_tail` 0.05 (fact 282); the `0.125` Sobel scale (documented as matching the M11 harness); default gate ladder `[0.5, 1.0, 2.0, 4.0]` (facts 324, 437, 458 all quote these rungs).

**Unlicensed — no §4 fact names these values:**

| Constant | File:line | Status |
|---|---|---|
| `SIGMA_EPS = 1e-3` — **two independent copies** | `focus.rs:121` and `strehl-plugin/src/measure.rs:59` | No fact. ARGUED guard. I sized when it binds: it fires when green-luma σ < 1e-3, i.e. `g·RN_e < 1.414e-3`. On A7C2 at ISO 100 that quantity is **0.3365 DN — 238× above the guard**. It cannot bind on the shipped profile. Two copies that can drift is the defect, not the value. |
| `PEAK_SEPARATION = 2` | `through_focus.rs:104` | No fact names 2. DERIVED from the triple's geometry in the doc comment. |
| `DETAIL_COLLAPSE_FLOOR = 0.90` | `merge_cmd.rs:1331` | Direction licensed by fact 24 (−58%/−53%). The **value** is justified against "the orchestrator's simulation" and "MEASURED tonight: 0.2% on 109MSDCF" — **neither is a folded fact**. |
| `DETAIL_RISE_FLAG = 1.50` | `merge_cmd.rs:1340` | **No fact at all.** Justified against "1.257x and 1.027x tonight", unfolded. |
| `MIN_INTERIOR_SAMPLES = 10_000`, `MAX_RELATIVE_SEM = 0.05`, `SELF_CHECK_SEM_LIMIT = 4.0` | `calibrate.rs:60, 66, 76` | No fact. ARGUED. Off the shipped path (defect 12). |
| `PLACEBO_SEED = 0x4D31_385E` | `merge_cmd.rs:1751` | No fact. Arbitrary by design, but it makes the placebo's outcome a function of one unmeasured number. |
| `MEMORY_BUDGET_BYTES = 6 << 30` | `strehl-cli/src/stack.rs` | 6 GiB appears in §3.2 prose; I found no §4 fact row asserting it. |
| `AMPLITUDE = 20.0 * FOCUS_NOISE_SD` | `through_focus.rs:1499` | Test-only. No fact. |

Everything else in the inventory is a structural constant (`NO_FRAME = u16::MAX`, flag bits, `SOBEL_RADIUS = 1`, `REGULARISER_WIDTH`, `SUPPORT_RADIUS`, `STATS_RADIUS`) that carries no measured content.

### Is there a systematic mechanism beyond the two already diagnosed?

**Yes. There is a third, and it is a different mechanism from rules 30 and 31.** I state the parts separately by evidence class.

**MEASURED (I read the specific lines):** Rule 30's mechanism — an assertion narrowed to dodge a known-wrong case — appears **once** in shipped Rust: the retired `the_merged_estimate_is_never_noisier_than_a_single_frame`. It is gone, and its replacement `averaging_beats_one_frame_and_selection_does_not` (merge.rs:954) asserts that **both branches actually occur** (`saw_selection`, `saw_averaging`), so it cannot pass vacuously. Rule 31's mechanism — a report describing a fold against the wrong draft — I found **zero** further instances of in code.

**MEASURED:** the mechanism that actually explains my list is **a refuted constant whose test asserts it against itself**. Before M18's edit today, `merge.rs:639` read:

```rust
fn the_selection_inflation_constant_is_the_measured_one() {
    assert!((SELECTION_INFLATION - 1.074).abs() < 5e-4,
        "gate-0 selection measured 1.074x (fact 320) and 1.075x independently (fact 23)");
```

That test **pinned the refuted value** and passed every day. Its justification chain was refuted at two separate links — fact 320 is "QUALIFIED BY FACT 343", and fact 23's 1.075× is a *spatial* sd ratio being multiplied into a *temporal* σ (fact 440, a rule-10 units violation). Nothing in the build could go red, because the assertion's only referent was the constant. This is **not** rule 30 — the domain was never narrowed. It is the inverse: **a test whose subject and object are the same value**. It has no power to fail by construction, and the well-written doc comment above it made it look like the most carefully-defended line in the file.

**MEASURED:** a second, distinct shape — **a consequence that reaches one consumer and not its siblings.** Fact 341's repair reached `predicted_sigma` but not `merge_cmd.rs:936` (fact 452 is literally titled "There is a FOURTH consumer"). Fact 203's mask reached the confidence union and the census but not the focus volume. Fact 502's seam reached `strehl-plugin` but not `strehl-cli`'s dependency list. Facts 343 and 500 reached SYNTHESIS but not the four `eprintln!` sites that print the refuted numbers. In every case the *file that was edited* was correct afterwards.

**ARGUED (this is my inference, not a measurement):** the two founding cases and my eleven are one population with one property — **a measurement that refutes a shipped value produces a fact row and a report, and nothing in the build turns red.** The corpus has no mechanism that links a §4 row to a compiled artefact. My own automated cross-check demonstrates the limit: 58 fact numbers cited across the crates, **100% of them resolve to a real §4 row**, and one of them (`profile.rs`'s "fact 200") resolves to the wrong one. Number-validity is checkable and worthless; content-validity is what matters and is only checkable by a human reading both.

**Clean negative, stated plainly:** I did **not** find evidence that anyone hid, minimised or mis-stated a result. Every single one of items 5, 6, 9, 12 and 13 is *documented in the code itself*, at length, with the refuting fact numbers cited. `merge.rs:74-108` is four paragraphs explaining why the constant it declares is wrong. `strehl-plugin/src/lib.rs:23` says "Facts 509-511: this project's own first pending operator change". The corpus is not deceiving itself. It is writing the correction down in the doc comment instead of in the value.

---

## Gaps

- **`docs/research/M49-unapplied-findings.md` was NOT written, and nothing was committed.** My operating constraint forbids writing findings to files; the complete report body is above and can be pasted verbatim. Nothing in the repo was created, modified or deleted by me. A transient scratch file I made early was removed and `git status` re-verified.
- **My own numbered facts/disciplines/questions, numbered LOCALLY from 1** (the orchestrator renumbers on fold), are the numbered rows of the ranked table above (**M49-F1 … M49-F13**), the unlicensed-constant table (**M49-F14 … M49-F21**), and: **M49-Q1** — who owns `read_noise_e_low`'s shape error? **M49-Q2** — should `flat_roi_stats` be replaced with the high-pass residual sd of fact 469 before any further merge claim is published? **M49-D1** — a test whose only referent is the constant it asserts has no power to fail; it must assert against an *independently obtained* quantity or against a named report number.
- **My own errors and near-misses.** (1) I read `merge.rs` at ~10:50 and again at ~11:02 and got **different files**, and my first draft would have reported `SELECTION_INFLATION = 1.074` as a live worktree defect. It is not — M18 landed the revert mid-audit. I caught this only because a test failed. (2) I nearly reported `FINE_FOCUS_NOISE_SD = 0.090400` as a wrong constant; it is correct as consumed, and only the *ratio* is refuted. (3) I nearly reported `WINDOW_RADIUS = 13` as wrong; fact 483 says it is 6/6 correct for the operator that actually ships. (4) My "every cited fact number exists" check returned clean and I nearly reported it as a pass; it is the exact check that cannot see the `profile.rs` collision. (5) I initially assumed `read_noise_e_high` would be a large output effect; deriving it gave **−0.07% at S=100 DN** and fact 241 gives **0.0000%** of pixels where it dominates.
- **No end-to-end merge run was performed.** Every sizing above is either quoted from an already-measured fact or derived by me from the noise model. Items 1, 4, 11, 12 are **not sizable** without running the binary on a real stack, and I say so rather than estimating.
- **The long tail of §4 was adjudicated from the row text, not from a per-fact code read.** I individually verified against code roughly 70 of the 357 rows. The unbuilt-component blocks (alignment 1/3/5/16/17/18/43–54, hot pixels 160–162, robustness mask 220–224, reshoot advisor 210–213, deconvolution 140–145/400–419/461–479, HDR 240–243/433–435) I classified NOT APPLICABLE-unbuilt on the strength of the row plus one confirming grep each; fact 473 independently confirms `merge_cmd.rs` contains no alignment, warp or registration, which I re-verified.
- **`profile.rs` and `merge.rs` are moving targets.** M48 had not landed at 11:04:38 (`profile.rs` mtime 09:40:42, clean in git). If M48 lands while this report is being read, item 2 is stale in the same way my first draft of item 5 was. Any consumer of this report should re-run the four `Select-String` commands at the top before acting.
- **I did not read** `merge.rs` 715–1102 in full, `focus.rs` 330–887, `through_focus.rs` 200–380 and 720–1790, `strehl-cli/src/stack.rs` 180–1276, or `merge_cmd.rs` 200–470 / 1000–1280 / 1440–1616 / 1720–2198. Findings in those ranges would be additional, not contradictory.
- **`probe_cmd.rs` and `stack_cmd.rs` named in the brief do not exist.** `crates/strehl-cli/src/` contains `main.rs`, `merge_cmd.rs`, `stack.rs`, `image_out.rs`.