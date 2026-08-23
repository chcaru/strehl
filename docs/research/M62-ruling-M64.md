# M62 ruling on M64 — the estimator as the shipped default

**Verdict: `CERTIFY`.**

Issued by M62 as acceptance authority, against the criteria committed in
`experiments/M62-sqrt-n/PREREGISTRATION-M64.md` at `b94649c`, which predates
M64's first commit `bd050ff`. **The battery was run unmodified**; the only new
files are a post-hoc diagnostic spec and an evidence extractor, both labelled and
neither able to affect the verdict.

I implemented none of M64's work and propose no fix to anything below.

| | |
| --- | --- |
| binary under test | sha256 `ef6849cf8024b1c2…`, built fresh by me at HEAD `d18fbd9f`, `crates/` clean |
| decision arm `DEFAULT` | **5.431624** (−0.8326 % vs √30; pre-registered tolerance ±2 %) → **PASS** |
| efficiency | **1.000076** (band [0.98, 1.02]) → **PASS** |
| determinism | byte-identical, sha256 `96f71f10…` → **PASS** |
| guard G, `109MSDCF` | `n_eff/N` = **0.22668** (< 0.95) → **PASS** |
| power | `SELECTOR-same-binary` **0.976815**, `n_eff` = 1.0 → **POWER-OK** |
| baseline it replaces | `REJECT`, blocking on `DEFAULT` (invocation exited 1) |

---

## 1. What I verified myself rather than accepting

The brief told me to check M64's claims rather than take them. All four hold.

- **`experiments/M62-sqrt-n/` untouched.** `git diff b94649c HEAD -- experiments/M62-sqrt-n`
  is empty and the worktree is clean for that path. (MEASURED.)
- **The copied harness files are SHA-256 identical — and there are six, not
  four.** `harness.py` `A3D2B12087B9…`, `10-acceptance.py` `22FA7C3AF05C…`,
  `11-focus-guard.py` `CE76C27E58D9…`, `acceptance-spec.json` `57D69F697F20…`,
  plus `01-pick-latent.py` `E769701AF6E9…` and `dngwrite.py` `F99BADABDACC…`.
  M64 undercounted its own copying in the conservative direction. (MEASURED.)
- **All five M64 commits are ancestors of HEAD.** (MEASURED.)
- **Fact 915's defect is fixed, independently reproduced.**
  `strehl stack D:\personal\macro\coffee-bubbles --out x.tif`, no other flags:
  exit **0**, **49 449 626 bytes** — matching M64's figure exactly — shape
  3516×2344×3 `uint16`, and byte-identical on re-run. (MEASURED.)

**I did not measure the binary that was sitting in `target/release/`.** `cargo
build --release` reported `Finished in 0.10s` with no `Compiling` lines, so I
could not tell whether it was built from this tree. I built into my own
`build-m64/` target dir instead, saw all four `strehl` crates compile in 57.36 s
(rule 33), and used that. This also avoided disturbing the shared `target/` that
five other live agents are using.

## 2. The battery

Every instrument arm reproduced my pre-M64 baseline **to full float64 equality**,
so the harness did not move under the change:

| arm | M64 | baseline | verdict |
| --- | --- | --- | --- |
| `A0-ladder:1 … :30` | 1.000693306 … 5.479128597 | identical | PASS ×7 |
| `B1a-const-selector` | 1.000693306 | identical | PASS |
| `B1b-random-selector` | 0.999607525 | identical | PASS |
| **`DEFAULT`** | **5.431624** ± 0.006199 | *was UNSUPPORTED* | **PASS** |
| `SELECTOR-shipped` | 5.431624 | was 0.769033477 | **NO-POWER** |
| `SELECTOR-same-binary` | 0.976815368 | identical | POWER-OK |
| `ESTIMATOR-explicit` | 5.477677513 | identical | PASS |

Between-seed sd 0.006163 on the decision arm; bootstrap SE 0.006199.

Two things in that table are worth more than the headline.

**`ESTIMATOR-explicit` and `SELECTOR-same-binary` are bit-identical to their
pre-M64 values.** M64 changed which path is default without perturbing the
explicitly gated paths at all. That is a stronger regression result than anything
M64 claimed for itself. (MEASURED.)

**`DEFAULT` and `SELECTOR-shipped` returned the same number because they wrote
the same bytes** — identical output SHA-256. `stack` and `merge` are one path,
verified at the byte level rather than inferred from the alias declaration.
(MEASURED.)

## 3. The guard, and M64's widening of it

**The widening is sound and I accept it.** It drove `--stack`/`--frames` exactly
as I built them, the script is byte-identical to mine, and my script *asserts*
the frame count against the corpus table, so a wrong `--frames` would have raised
rather than silently mis-measured (discipline 388). All seven counts are correct.

**I reproduced its worst case exactly**: `coffee-bean` `n_eff/N` =
`0.3010857142857143`, on my own build, with my own guard. (MEASURED.)

**Does widening change what the guard certifies? No, and it cannot.** Requiring
*more* stacks to pass the same threshold with the same statistic is monotone: it
can only turn a pass into a fail, never a fail into a pass. M64 made my
certification harder to obtain and easier to lose. (DERIVED.)

Three scoping corrections, none of which change the verdict:

- **It is 7 of 12, not "all seven corpus stacks."** The corpus table has twelve
  stacks. The five omitted — `bee-1`, `bee-2`, `bee-3` (299 each),
  `wrapped-text-1` (130), `wrapped-text-2` (120) — are the five largest, all from
  23 Aug. The claim should read "the seven stacks run", and the guard's 3.16×
  margin means the omission is unlikely to matter, but it is untested and should
  not be described as complete. (MEASURED / ARGUED.)
- **`109MSDCF` was never nominated as a worst case.** I named it because it is
  the ISO-160 stack the gain was fitted on — best-characterised, not hardest. It
  being beaten by `coffee-bean` is not a correction to my specification.
- **The worst case is the one stack whose filter state is unresolved.**
  `coffee-bean` is CPL-UNKNOWN (fact 845, discipline 409). Here it is
  **unaffected**: `n_eff` is a focus statistic, a polariser bears on speculars
  and clipping, and the claim is "all pass" rather than anything resting on
  `coffee-bean` alone. Recording it because the retraction asked that stacks be
  named rather than the corpus generalised over. (ARGUED.)

## 4. Ruling on the four questions

### Q1 — Is `DEFAULT` satisfied in the sense I meant, or merely no longer erroring?

**Satisfied in the sense I meant, and I can say something stronger than PASS.**

My criterion had three parts and all three bind: no tuning flags, within 2 % of
√30, efficiency in [0.98, 1.02]. The invocation carried no `--gate`; `--flat-roi`
is a diagnostic I proved non-perturbing by SHA-256 in M62 §, and `--out` is how
you get output at all.

The efficiency figure separates two things the headline conflates. The merge
admitted **29.539 of 30** frames per pixel on average, and having admitted them
it averaged them at efficiency **1.000076** — it wasted essentially nothing of
what it took. **The entire 0.83 % shortfall against √30 is the gate declining
0.461 frames per pixel, not any defect in the averaging.** That is a design
choice about admission, not an arithmetic error. Had efficiency come in at, say,
0.93 with the same 5.43, I would have passed the headline and rejected on the
band — which is why the band is there. (MEASURED / DERIVED.)

### Q2 — Gate 8 scores 5.4777, the shipped default 4.0 scores 5.4316. Suboptimality?

**Not a suboptimality. Shipping 4.0 is correct conduct, and optimising toward
8 would have been grounds for me to reject.** This is the one place my own
instrument is actively dangerous, and I measured it rather than argued it.

Post-hoc sweep of `--gate` on the static burst, one seed, same binary:

| gate | 0 | 0.5 | 1 | 2 | **4 (default)** | 8 | 16 | 64 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ratio | 0.9773 | 1.3616 | 1.9710 | 3.7610 | **5.4354** | 5.4849 | 5.4849 | 5.4849 |
| `n_eff` | 1.0 | 2.966 | 6.804 | 18.434 | **29.539** | 30.0 | 30.0 | 30.0 |

**The score is monotone non-decreasing in gate and saturates at gate 8**, where
`n_eff` reaches N and cannot go higher. So the argmax of my objective over the
gate is not a point — **it is the entire half-line [8, ∞)**. (MEASURED.)

A static burst has no focus variation, so admitting another frame is always
weakly better and there is no interior optimum. **A gate tuned to maximise my
number is a gate tuned to admit everything, which on a real focus stack is
exactly the degeneracy I pre-registered guard G to catch.** My battery and my
guard would then be in direct contradiction, and the guard is the one that speaks
to the product.

So the 5.4777 − 5.4316 gap is **not evidence about the gate. It is my harness's
blind spot, quantified.** M64 shipping the value it pre-registered, in the
presence of a visible number that rewarded moving it, is the correct behaviour;
moving it would have been optimising against the instrument. That the gap is
visible at all is a property of my plant, not a defect in theirs. (DERIVED.)

### Q3 — Focus-correctness: inside or outside what I certify?

**Outside. Squarely, and I want this unambiguous.**

Guard G reads the binary's **self-reported** `n_eff`. M64 volunteered this and it
is correct. G therefore establishes that the merge still *discriminates between
frames* on real data — `n_eff/N` between 0.014 and 0.30 across seven stacks
against 1.000 on the burst from the same binary — and **establishes nothing about
whether the frames it admits are the right ones.**

**A `CERTIFY` from me means, and means only:**

1. On a synthetic static burst whose noise is drawn from the merge's own model,
   the no-flags default path reduces noise by 5.4316× against an arithmetic truth
   of 5.4772×, and performs the averaging of what it admits at efficiency 1.0001.
2. Its output is byte-deterministic.
3. It has not become degenerate: it still varies `n_eff` on real focus stacks.
4. A selector control on the same binary still scores ≈1.0, so the battery
   retained the power to fail.

**A `CERTIFY` from me does not mean:**

1. **That the sensor model is calibrated.** Arm A draws noise from the same `g`
   and `RN_e` the merge gates with, so it measures efficiency and is circular
   with respect to calibration (rule 34). Only the owner's real §12 burst tests
   that, and it is what closes fact 808.
2. **That the merge selects the right frames.** Focus-correctness is unmeasured
   here, and per M64 unmeasured in the corpus. **This is a real, open hole in the
   project and my certificate must not be read as covering any part of it.**
3. **That `DEFAULT_GATE = 4.0` is the right value.** Q2 shows my instrument
   cannot arbitrate it.
4. Anything about detail, resolution, alignment, outliers or occlusion.

### Q4 — M64 says its in-crate fixture cannot arbitrate the gate's value because it saturates faster than my burst. Agree or refute?

**I refute it by strengthening it.** The conclusion is right and the reason given
is too weak, in a way discipline 448 names precisely: a conditional that implies
an escape hatch which does not exist.

"The fixture saturates faster than M62's burst, so *the fixture* cannot arbitrate
the value" implies a slower-saturating fixture could. **It could not. My burst
saturates too — at gate 8 (§Q2), and it is the best-conditioned static plant in
the project.** The limitation is not a property of that fixture being worse than
mine; it is structural to *every* static burst, mine included, because a static
burst has no focus variation and therefore no interior optimum in the gate.

The general result is: **no static-burst harness can arbitrate the gate's value.**
It should be stated that way, unconditioned, rather than as a shortcoming of one
fixture. (DERIVED, from the measured monotone-and-saturating sweep.)

## 5. Discipline 433 applied to my own criteria — what each forecloses

Mine, so I owe it the audit.

- **`estimator_rel`, two-sided ±2 %.** Forecloses scoring *above* √N. On this
  plant that is arithmetically impossible, so the foreclosure is a harness
  self-check rather than a constraint on any merge. Correct as written.
- **`efficiency_band` [0.98, 1.02].** Same shape, same justification: >1.02 would
  mean the merge beat the arithmetic bound of what it admitted, which indicts my
  reference or my ROI, not the merge.
- **Guard G, `n_eff/N < 0.95`.** This one **genuinely forecloses** a legitimate
  case: a stack with so little focus variation that admitting nearly everything
  is *correct* would be rejected. The foreclosure is not activated here — all
  seven measured stacks lie in 0.014–0.30, a 3.16× margin — but it exists, and G
  should be read as assuming its test stack has real focus variation.
- **`selector_ceiling` as POWER not PASS.** **This run is the measured
  vindication of fixing it.** I changed it pre-emptively at `b94649c` because a
  required ceiling on `SELECTOR-shipped` forecloses the hypothesis under test.
  `SELECTOR-shipped` then moved 0.769033 → 5.431624. **Under my own superseded
  `spec_version 1.0`, this battery would have mechanically REJECTED M64 for
  doing exactly what it was dispatched to do.** The foreclosure was not
  hypothetical and discipline 433 caught it with one commit to spare.

## 6. On fact 926 / discipline 438 — does my battery need input-side power?

**Yes, and M55 is right that mine is the weaker construction.** I assign
`NO-POWER` from an arm's *score* against a ceiling, which is output-side; M55
assigns it from a roll-null on the *input*. Output-side assignment cannot
distinguish "this arm has power" from "everything collapsed toward 1.0". My
instrument arms give partial protection — a global collapse would trip them and
return CANNOT-CERTIFY first — but a failure confined to the CLI arms would not be
caught.

**This ruling is unaffected, and I can show that rather than assert it.** I
already *record* the input-side quantity without *using* it: `SELECTOR-same-binary`
reported `n_eff` = 1.0, which is the input-side condition for a pure selector,
while scoring 0.976815, the output-side condition. Both hold and they agree, so
the power claim behind this CERTIFY rests on either construction. (MEASURED.)

**I am not making the change now.** My own §6 bars amending the spec after seeing
the diff, and I am barred from implementing generally. Recording it as owed work
for whoever holds the instrument next.

## 7. Rule 42 self-audit

Rule 42 post-dates my last commit. **I used the unsafe pattern too** — `b94649c`
was `git add <paths>` followed by a bare `git commit -F`. Audited: **0 foreign
files**, all 24 paths under `experiments/M62-sqrt-n/`. No damage, and disclosed
rather than left for someone to find. This commit uses `git commit -- <paths>`.

I did not modify `AGENTS.md` or `SYNTHESIS.md`; the orchestrator maintains those
tables and has already been adding my rows.

## 8. Claim labels

MEASURED: every ratio, SHA-256, byte count, frame count, `n_eff`, the gate sweep,
the identity of the copied files, and the reproduction of `coffee-bean`.
DERIVED: the monotone-saturating argument that no static burst can arbitrate the
gate; that widening a guard to more stacks cannot weaken it; the attribution of
the 0.83 % shortfall to admission rather than averaging.
ARGUED: that the five unrun stacks are unlikely to matter given a 3.16× margin;
that `coffee-bean`'s unresolved filter state does not bear on a focus statistic.
