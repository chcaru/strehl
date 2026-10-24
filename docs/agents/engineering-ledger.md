# Engineering rules and evidence ledger

Moved from the root `AGENTS.md` on 2026-10-24. Original rule identifiers,
examples, amendments and retractions are retained so existing citations to
"AGENTS rule N" continue to resolve at `#rule-N` in this file.

[AGENTS.md](../../AGENTS.md) is the concise working contract. Read the relevant
entries here before doing work in their scope; this ledger is not startup
reading for every task. Paths in code spans are relative to the repository root
unless explicitly absolute. Measurements describe the builds and inputs named
in their sources, not necessarily the current default.

| Work | Original rules |
| --- | --- |
| RAW, merge, noise, geometry | 1–7, 10, 15, 23, 32, 34 |
| Controls, metrics, experiments | 8–13, 16–18, 20–24, 26, 30, 34–36, 39 |
| Corpus citations and folds | 25, 28–29, 31, 31b, 37–38, 44 |
| Prior work and allocation | 40–41, 43 |
| Builds, processes, reproducibility | 14, 19, 27, 33, 42, 45–49 |

## How to read older operational advice

Keep the amendments with the original claim. In particular, rule 6's M103
amendment qualifies its earlier span-discard and end-to-end acceptance advice.
Rule 45's historical suggestion to clear `STREHL_WARPMAP` must **not** authorize
writing a capture-library sidecar: use a fresh isolated map per kernel and run,
or an isolated input copy. Preserve corpus read-only guarantees in every arm.
Rule 48's approximately 400 px limit is a measured property of the commissioned
viewer; commission a different viewer before relying on a different limit.

## Original numbered entries

### Rule 1

1. **Storage is u16 CFA. Arithmetic is f32.** Never store f16 — a 10-bit
   mantissa gives ~8 LSB steps on linear 14-bit data.

### Rule 2

2. **Never materialise aligned frames.** Gather at consumption inside each
   kernel. Materialising 60 aligned RGB frames is 24 GB and demosaics 60 times
   instead of once.

### Rule 3

3. **The noise model is injected, never re-derived per stage.** A private
   per-stage noise estimate is the exact mechanism behind the prior project's
   2–5x defect.

### Rule 4

4. **Never let a merge reference be a raw per-band argmax.** Argmax over N
   frames returns 1.95–2.61x single-frame noise, and regularising the focus
   field drops that to 1.075x — necessary, and **still above 1.0**. A
   regularised selector is still a selector; the noise-gated average is the
   other half. **Do not quote a speckle figure here.** This rule carried
   `34.4% -> 0.87%` for most of the project's life; M60c established that the
   pair is *ring*-unregularised to *ring*-regularised, on a **retired
   operator**, and that **no measurement of regularised-Tenengrad speckle
   exists** to replace it (facts 932-934). Two separate numbers were being
   conflated because they agree within 16% by coincidence.
   **M65 then measured the thing this rule was reaching for and it came out
   negative:** at the shipped gate, electing on the raw field instead of the
   regularised one moves `n_eff` by at most 1.2335x — **regularisation of the
   election is not load-bearing as shipped**, though it is at gate 0.5. And
   56.70% of pixels change winner while the acceptance set moves 0.44%
   (facts 961-963). **The speckle of the index map was never evidence about a
   gate that admits on value.** Keep the rule for the noise figures, which are
   measured on the shipped operator; drop the justification that was not.
   **This rule was written and then broken by M30**, whose fact 242 ("2.3x more
   clipping whole-stack than at gathered frames") is an argmax artefact: at the
   shipped 31x31 regularisation it falls to 1.4x, and heavier still to 1.0x.
   The argmax *flees* clipped frames because clipping flattens the gradient —
   **but only when the saturated patch is large relative to the focus window.**
   M54 measured the flee/seek ratio monotone in the pinned fraction of the
   support: 0.0101x (flees) at a fully pinned support, 13.05x (**seeks**) at an
   isolated saturated point, which sits on the steepest edge in the frame and
   attracts the argmax. Do not quote the flee direction unconditionally.
   (SYNTHESIS fact 683.)
   **The rule applies to analysis scripts, not just to the merge** — any
   statistic evaluated "at the best frame" inherits argmax's defects.

### Rule 5

5. **Fit geometry at runtime; do not bake it.** Scale drift and the scale
   centre are per-stack quantities. Only sensor calibration belongs in a
   profile, and profiles live in data files.

### Rule 6

6. **Never chain alignments, and never rely on a single fixed reference on a
   deep stack.** Both halves are measured, and the *reason* chaining fails is
   not the one originally assumed.

   Chaining is not merely noisy. **Short-baseline edges under-report
   magnification change**, and any span must telescope to the same total, so the
   gap is pure bias rather than accumulated error. On `coffee-bean` the span-1
   ladder totals −1.6876% against span-16's −5.8891%. The bias is **coherent**,
   so composing 104 edges yields **40.3 plane px** of corner error with
   **36.4 px in scale alone**. It needs a real inter-frame content change and
   lives below ~0.5 px of differential displacement: a resampler-free control
   recovers a planted increment at ratio 1.00, the same increment on a real
   defocus pair recovers at 0.56. **Short baselines look best by tile residual
   while being worst by truth — never judge an edge by its residual.**

   **Its magnitude is a property of the scene, not of the optics.** Across the
   five-stack corpus `1/S_W(1)` ranges **1.03x to 3.26x**: `coffee-bean` 3.26,
   `119MSDCF` 2.20, `109MSDCF` 1.32, but `112MSDCF` **1.05** and `113MSDCF`
   **1.03** — essentially none. Chaining all 78 adjacent edges on `112MSDCF`
   recovers **99.0%** of the direct long edge. Two stacks matched to 0.3% in
   per-frame displacement still differ **3.11x** in shrinkage, so it is not a
   function of baseline in any parameterisation, and no measurable property of
   the edge sets predicts it. Do not quote a single number for it.

   A single fixed reference fails differently: on a 105-frame stack it places
   only **76 of 105** frames, first failing at frame 73, because focus has swept
   the subject and the endpoints share no correlatable in-focus content
   (fact 4).

   **Do this instead.** Measure a sparse multiscale set of **direct** pairwise
   fits (a span ladder such as 1,2,3,4,6,8,12,16,24,32,48,64 plus every frame-0
   pair), composing nothing. **Discard spans 1-2 from the solve — BUT SEE THE
   AMENDMENT BELOW; this instruction is measured harmful per frame.** Then run one
   global linear least squares for per-frame `(log a, theta, tx, ty)` with Huber
   IRLS — `unit` weighting on deep stacks, `invvar` on shallow ones. This places
   105/105 frames at **6.76 plane px** held-out, and 0.58-0.67 px on shallow
   stacks. **Restrict the solution to the connected component containing the
   anchor** and report the rest unplaced: an unconstrained minimum-norm solve
   emits ~1e16 while still reporting full coverage. Verify with cycle
   consistency and held-out long-edge prediction, and **check the training
   graph's cycle rank first — a solve over a tree is chaining in disguise**, and
   any comparison against a chain is then vacuous.

   **Do not fit a shrinkage correction to escape any of this.** It is
   measurable and stable within a scene, and it transfers to **0 of 18**
   cross-scene pairs, making the worst case **83.4x worse**. Even an *oracle
   in-sample* correction leaves a chain at **13.92 px**, twice the error the
   plain global solve already achieves without it. The case the project would
   ship — fit on the deep stack you have, apply to the next capture — is the
   catastrophic one. Computing `1/S_W(1)` per stack is still worthwhile as a
   **diagnostic**, since it cleanly separates chainable stacks from unchainable
   ones, but it is a gauge, not a gain.

   6.76 px is not good enough for a final render. Treat deep-stack alignment as
   **usable, not solved** (SYNTHESIS risk 11). See
   `docs/research/M10-deep-alignment-measured.md`,
   `docs/research/M12-shrinkage-measured.md` and
   `docs/research/M3-alignment-measured.md`.

   ---

   **AMENDMENT (M103, commit `1111be9`) — EVERY NUMBER ABOVE IS END-TO-END, AND
   THE MERGE DOES NOT CONSUME AN END-TO-END QUANTITY.** 6.76 px, 13.578 px,
   13.92 px, 40.3 px and every acceptance bar this rule was built on score the
   composition from first frame to last: **one frame pair out of 299.** The merge
   gathers **each frame at its own `a_k`**, so *per-frame placement* is what it
   reads. Scored both ways on 39 rungs of an independent RAW ladder in the merge's
   own gauge, the two are **nearly independent**: `deep()` as shipped is
   end-to-end **150.3 px** / per-frame **36.4 px**, while `iterated_wide()` is
   end-to-end **2.9 px** / per-frame **37.5 px**. **A fifty-fold improvement in
   the headline bought nothing where it counts** (fact 1407).

   Consequences, binding:

   - **"Discard spans 1-2" takes max per-frame placement error to 628.1 px**
     (fact 1408). Short edges are biased *and* load-bearing; both are measured.
     The discard remains the default **only** because no calibrated replacement
     has shipped — it is a known-harmful stopgap, not a result. Prefer
     calibrating short edges (per-edge self-measured response, blur
     equalisation) over discarding them.
   - **Report every placement number with its gauge.** The same track reads
     **98.2 px** referenced to frame 0 and **37.5 px** referenced to rung 144 —
     a 2.6x swing from the reference choice alone. A bare "px" for an alignment
     solve is not a number (discipline 698).
   - **The per-span scale response is an inverted U that never reaches 1.0 at
     any baseline**: 0.130 at span 1, 0.659 at span 32, 0.102 at span 192
     (fact 1409). Long edges are not a trustworthy reference either.
   - **Any synthetic plant for alignment work must carry the measured
     curvature.** `bee-3-cpl`'s track departs its own straight chord by
     **46.1 plane px** at j=200, accelerating; a linear plant does not transfer
     (fact 1410).
   - **Before accepting any future alignment bar, name the consumer and check
     the bar measures its input** (discipline 699). Four bars across four
     milestones missed this.

### Rule 7

7. **Never compute statistics over the full decoded buffer.** `rawler` returns
   7168x5120 for the A7C II but fills only the 7032x4688 active area. The rest
   is synthetic zeros, not black level.

### Rule 8

8. **Every performance or quality claim needs a command that was run.** Label
   claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED.

### Rule 9

9. **Pair every sharpness metric with a flat-ROI control.** A sharpening pass
   raises gradient energy on featureless foam; that is how the prior project
   fooled itself. **This rule was written, published, and then broken by M38**,
   whose detail metric credits regularised argmax with **+35.47% "detail" on a
   flat ROI** — caught by an independent verifier, not by the author who had
   this rule in front of him. The control is one line. Run it *first*, not as
   a closing check, because a metric that fails it invalidates every number
   already computed with it.

### Rule 10

10. **Never compare a spatial sd to a temporal sigma.** They are different
    physical quantities. A spatial sd over an image region carries scene
    structure; a temporal sigma across frames does not. High-pass first, or
    compare like with like. This error has now caused **three** retractions —
    the prior corpus's 1.10x correlated-noise claim, M2's "unexplained"
    1.46x model gap (1.01x once matched properly), and fact 88's 119MSDCF
    "43.2-53.1 DN", which the noise model caps at 22.9 DN at ISO 50 and which
    inverted the true noise ordering of two stacks. **The cheapest detector is
    the project's own model: any sigma that exceeds `sqrt(g*S + (RN_e*g)^2)`
    is not a temporal sigma. Check every published sigma against it.**

### Rule 11

11. **Every claimed defect needs a placebo, and every headline number needs a
    regression test on its own code path.** What proved argmax was the cause of
    M2's 1.253x was not a better measurement of argmax — it was a *different
    merge rule* on identical data (mean, 0.534x) and a selector with the same
    winner histogram but no noise coupling (0.981x). Without those it was only
    correlational. And the 1.253x itself had 52 tests behind the library and
    zero covering the code that produced it.

### Rule 12

12. **The author never verifies their own work.** M2 was self-verified
    thoroughly and still shipped five wrong supporting numbers, two of them in
    the direction that loses an argument. See `docs/research/M2-verification.md`.

### Rule 13

13. **Sweeping a parameter? Check the plant can express the failure first.**
    M11 swept the focus window on a fronto-parallel plant and reported it "still
    improving" at the widest setting. That plant is mathematically incapable of
    producing an interior optimum for a symmetric window, so the result was not
    weak evidence — it was **none**, and it cost the project a window less than
    half the right size. Ask what the stimulus would have to contain for the
    answer to be anything but the endpoint. **Report an endpoint argmin as "no
    turnover found within the sweep", never as an optimum.**

### Rule 14

14. **Verifying the read-only corpus guarantee? Use `Get-ChildItem -Force`.**
    Without `-Force` it silently skips hidden and system files and under-reports
    `C:\dev\macro` by **1081 files / ~312 MB**, which looks exactly like
    evidence that the tree was modified. Correct totals: **18530 files /
    286,893,514,060 bytes**. Also: `C:\dev\macro\test\119MSDCF` and
    `D:\personal\macro\119MSDCF` are the **same 33 frames**, verified
    byte-identical through a full measurement sweep. Two stacks must mean two
    *different* stacks — use 109/119 or 112/113, never a directory and its
    mirror.

### Rule 15

15. **"Halo" is overloaded — never use the bare word.** In the plugin interface
    and SYNTHESIS fact 32 it is the *rectangle expansion* a filter needs beyond
    its output tile (19.42 / 32.39 / 89.23 plane px), an alignment and warp
    margin. In the stacking literature it is the *artifact* at an occluding edge
    where the selector drags one surface across another. Say **"plugin halo"**
    or **"occlusion halo"**.

### Rule 16

16. **Timing a parameter sweep? Alternate direction and take the per-setting
    minimum.** M14 measured a single forward sweep at **−0.7%** and a reverse
    sweep at **+19%** on the same binary and settings, and a function reading
    **21% slow** purely for being timed last. Thermal drift, clock ramp and
    cache warming all correlate with sweep position, so a one-directional sweep
    attributes them to whichever parameter came last. Use several alternating
    sweeps, report the minimum per setting, and quote a near-flat result as a
    **bound, not a value** — two honest runs of the shipped cost sweep
    disagreed 0.69% vs 1.28%, which is larger than either is from zero.

### Rule 17

17. **Before you bin a statistic, ask what map you are binning it against.** If
    the bins and the quantity being binned come from the same data, name the
    mechanism that could drive both — and if you can name one, the result is
    circular until you break the shared path. M21 scored occlusion bimodality
    against a depth-step map built from the same focus volume, but a bimodal
    pixel makes its own argmax flip and so *manufactures* the depth step it is
    credited with landing on: **29.47× collapsed to 4.38×** once the two were
    measured at different scales. M22's cross-scene test reported over a million
    "defects" against an independence baseline because both subjects sit
    centre-frame. **Fixes: bin at an independent scale, use a shift control that
    destroys per-pixel correspondence while preserving every spatial statistic,
    or permute the axis the effect lives on.** Pair any of them with a
    known-real positive control, or the collapse ratio has no scale to be read
    against. M20 §2 still carries an *unresolved* instance of this — its optics
    gate may be checking a formula against a constant derived from that formula.

### Rule 18

18. **Say which direction each metric can be fooled in, next to where you use
    it.** `mean |∇|` rises when a merge *manufactures* detail exactly as it does
    when a merge preserves it — measured, plain argmax reads **above ground
    truth** at σ=0.050, and the Wiener output carries 24% more gradient
    magnitude while carrying 12% *less* gradient correlation with truth. So it
    is admissible as a test against **collapse** and inadmissible as evidence of
    quality. A metric with no stated failure direction is not an acceptance
    criterion.

### Rule 19

19. **kebab-case** for directories and files. Crates are `strehl-*`.

### Rule 20

20. **Before running any gate, control or metric, write down the input that
    would make it FAIL — and check that such an input exists.** If none does,
    it is arithmetic, not evidence, and must be labelled so. **Three shipped
    examples, all caught by independent verifiers and none by the author:**
    M20's optics "gate" is the algebraic *inverse of its own input* (`B` was
    obtained by inverting the equation the gate re-derives), so no
    configuration of the model could have failed it; M38's detail metric
    scores a flat ROI as *gaining* detail; and M33's two half-step phases,
    quoted as replicating each other at 0.05%, have hit rates summing to
    **1.0000 by construction** — they are complements, and a complement cannot
    corroborate its own partner. **Measuring instead of arguing buys nothing if
    the measurement has no power to reject.** Rules 9, 11 and 13 are special
    cases of this one. Prefer the cheap adversarial input: a flat ROI for a
    detail metric, an a-priori value for a fitted constant, a known destroyer
    for a quality score, an arithmetic check that two "independent" arms are
    not the same number twice.

### Rule 21

21. **A fitted constant cannot gate the model it was fitted to.** Where a
    constant was obtained by inverting a relation, gate that relation with an
    *independently predicted* value instead. `B = 1 + m/p = 3.000` from pure
    geometry predicts M5's measured knee to **2.1%** — that is a real gate, it
    costs one line, and it was available the whole time.

### Rule 22

22. **The rules in this file are an executable checklist, not a creed.**
    Rules 4, 9 and 10 were each written down, published, and then violated by a
    later milestone *by the same author who wrote them* — M30's fact 242 is a
    raw argmax (rule 4), M38's detail metric shipped with no flat-ROI control
    (rule 9), and fact 88 compared a spatial sd to a temporal sigma (rule 10).
    All three were caught by independent verifiers. **Agreeing with a rule does
    not execute it.** Before publishing a milestone, walk this list and name,
    per rule, the line of code or the command that discharges it.

### Rule 23

23. **`scipy.ndimage.sobel(cube, axis=k)` smooths every axis except `k`.** It
    applies `[-1,0,1]` along `axis` and `[1,2,1]` along all others — so passing
    a `(frames, y, x)` cube silently smooths along the **frame axis** and
    changes the focus measure. M32 did this and inflated its headline σ-count
    by ~1.7–1.9×. Extract the 2-D plane first, or pass `mode`/`axes`
    explicitly. **General form: any separable filter applied to an array with a
    non-spatial axis will touch that axis unless you stop it.**

### Rule 24

24. **Verification must re-choose, not re-compute.** Across four independent
    passes over fourteen milestones, **every published number that was checked
    reproduced exactly**. Not one defect was arithmetic. All were *choices* — of
    nuisance estimator, reference, arm, null, or library default. A verifier who
    recomputes the author's formula on the author's inputs confirms every one of
    them. So a verification brief must name the choice points and require a
    different defensible setting at each. See discipline 253.

### Rule 25

25. **Claim a number block before you use it, and check the claim
    programmatically, per namespace.** `SYNTHESIS.md` has **three** independent
    numbering spaces — facts (`§4` table rows), disciplines (`§5` list items) and
    questions (`§10` list items) — and disciplines and questions legitimately
    share numbers. M19 wrote "M19 owns 120–139" while M20-V already held 122–139.
    Run the collision check in `experiments/*/fold-*.py` before writing, **never
    eyeball it**, and if a block is taken, shift the whole block to open ground
    rather than interleaving. Record the shift in the fold and in the report.

### Rule 26

26. **Prove that a diagnostic does not perturb the output, by hash.** Any
    statistic, probe or observer added to the merge must ship a run showing
    **byte-identical output** with it on and off, placebo included — the way
    fact 420 does. An argument that a channel is read-only is not evidence that
    it is.

### Rule 27

27. **Before declaring a long-running process dead, state what a healthy one
    would look like at this instant.** If a working run and a failed run predict
    the same observation, the observation is not evidence and the correct action
    is to wait. Three specific traps, all of which fired here (see
    [`2026-08-external-review.md`](../proposals/2026-08-external-review.md) §5
    item 6): **zero bytes on disk is not zero work** — an agent that reads for
    three hours before its first write is indistinguishable from a corpse under
    a file-count probe; **a turn counter read at 473 s measures the sampling
    instant, not the run**; and **a stand-down is an intervention, not an
    observation** — telling live workers to stop causes the silence it was sent
    to diagnose. Ten agents were written off on this evidence and every one of
    them later landed a folded milestone.

### Rule 28

28. **A report's proposed numbers are not where its facts live. Check for an
    existing fold by CONTENT before folding, never by number.** M19's §9
    proposes facts 120–139; those facts are actually folded at **400–419**,
    because rule 25's collision check moved the block. An orchestrator resuming
    on a stale note read "120–139 are free", which is true, and would have
    written a **20-row duplicate** of an already-folded milestone. The number
    being free is not evidence the fold has not happened. Match the first ~70
    characters of each proposed fact against the whole of `§4` and require
    **zero** matches before writing; if all match, the fold is done and the only
    correct action is to record the mapping in the report. The same check is
    what proves a re-run is a genuine double-fold rather than a new block.
    **Corollary for report authors:** number proposed facts `P1, P2, …`, not
    `120, 121, …`. Absolute numbers belong to the orchestrator at fold time, and
    every absolute block proposed in a report so far has either collided or
    moved.

### Rule 29

29. **A string-anchored edit deletes its anchor. Re-emit it, then verify a
    structural count.** Twice in one night an edit whose `old_str` was a
    heading or a table-row prefix silently consumed that anchor: one
    concatenated the M43 and M45 corpus rows into a single 2 602-character
    line, the other deleted `## 9. Corpus locations` and orphaned its body
    under `## 10`. Both produced valid-looking Markdown and neither was visible
    in the edited region. **The tell is always a deletion count that should
    have been zero and was not** — so before committing, count deletions
    (`git diff -- <paths> | Select-String "^-"`, and note that `^-[^-]` misses
    deleted *blank* lines) and account for every one; and re-list the
    structures you did not intend to touch — headings with
    `Select-String "^## "`, table rows by counting unescaped pipes per row.
    Anchor on the smallest *unique* string that is not itself structural, or
    include the anchor verbatim at the head of the replacement.

### Rule 30

30. **A known model disagreement you have decided to tolerate must be asserted
    against, not carved out of the assertion.** M25's simulator self-test
    compared its dark noise against M4 at six ISOs and *excluded ISO 50 from
    the assertion* because the model was known to disagree there. That silenced
    the one test that would have caught a **2x** gain error, in the one gate
    that ran at ISO 50; the defect then survived weeks in shipped code after it
    had already been measured (facts 550, 552, discipline 288). A tolerated
    disagreement is a *fact about the model*, so assert it at the expected
    wrong value, `xfail`-style. Then it fails the day the expectation changes,
    which is the day you want to hear about it. **Never narrow an assertion's
    domain to make it pass.**

### Rule 31

31. **Fold from a committed revision, and record its sha in the source
    column.** Fact 548 was folded from a milestone report while it was still
    untracked; the report was then revised twice, and its own supersession note
    described the fold against *its own latest draft* rather than the draft
    actually folded — so it named the wrong clause, in good faith (fact 554).
    A report cannot describe what a fold says; only the fold can. Two defences:
    fold only from a committed sha and cite it, and when a milestone reports a
    correction, **re-read the folded row itself** before believing the report's
    account of it.

### Rule 31b

31b. **Run `python experiments/ORCH-drift-check/fold_check.py <fold.py>
    <report.md> docs/research/SYNTHESIS.md` before committing any fold.** This
    is rule 31's mechanical half, and it exists because discipline 849 does not
    execute itself: seven folds in one night moved a number or a qualifier
    toward the claim, and the seventh (fact 1686, a measured **60.9%** folded as
    a **"MINORITY"**) happened *while its author was writing the discipline
    forbidding it*. The tool parses the fold with `ast` — it never executes it —
    lifts every numeric literal, and requires each to appear in a source, with
    the surrounding context printed so meaning can be checked rather than mere
    presence. **Its second bucket is the one that matters**: qualifiers
    (*majority, minority, dominant, only, largest*) sitting next to a number are
    printed for a human read, because they carry the sign and no presence check
    can test them. Run retrospectively on the fold that produced 1686, it flags
    `[MINORITY]` and `[dominant]` against the number they misdescribe. Pass
    `SYNTHESIS.md` as an extra source when the fold cites existing facts.
    Commissioned with two sabotages that must read RED; `--commission` self-tests.
    **A green here is necessary and not sufficient — read the qualifier bucket.**

### Rule 32

32. **`rawpy`'s `raw_image_visible` is a view into LibRaw's buffer, not a
    copy — and its use-after-free does not reliably crash.** It is invalid the
    instant the `RawPy` context manager exits. Allocate *and* copy inside the
    `with`; `.astype(...)` or `.copy()` on the same line is the safe idiom.
    M50 got this wrong and Windows raised an access violation (0xC0000005) with
    **no Python traceback**, after several minutes of reading freed memory
    without complaint. The crash is the lucky outcome. The unlucky one is
    silently corrupted pixels in a measurement nobody re-checks, which is
    exactly the class of defect this project exists to avoid shipping.
    `python -X faulthandler` is what turned a bare exit code into a line number;
    reach for it first on any native crash.

    Every Python script here that decodes RAW must be checkable against a
    second, independent decode of the same files. M50 stores a pooled-RMS
    temporal sigma per plane alongside its results for exactly this reason: it
    proves the loader, not just the estimator.

### Rule 33

33. **A `cargo test` result with no `Compiling` line above it is not evidence
    — in either direction.** Cargo's fingerprint can consider a stale artifact
    fresh and will then report results for code that is not on disk, complete
    with a convincing file and line number. This happened twice in one night, to
    two agents, by two mechanisms: a file written while cargo was fingerprinting
    it, and a file restored with `Copy-Item`, which preserves the *source's*
    older mtime. **After any restore, set `LastWriteTime` to `Get-Date`.** Before
    trusting a workspace run that follows an edit, force the rebuild — touch the
    file, set a unique `RUSTFLAGS` cfg, or `cargo clean -p <crate>`. Read the
    compile lines, not just the test lines. **And never use `-q`**: `cargo run -q` and
    `cargo test -q` suppress the `Compiling` lines, which are exactly the
    evidence this rule requires. M48 fell into that while checking this rule's
    own property, caught it, and redid the run before recording anything.
    **The line to look for depends on the command: `cargo build`, `cargo test`
    and `cargo run` print `Compiling <crate>`; `cargo check`, `cargo clippy` and
    `cargo doc` print `Checking <crate>` or `Documenting <crate>` and NEVER print
    `Compiling`.** This rule previously demanded a `Compiling` line unconditionally,
    which made it unsatisfiable by clippy and check -- and cost an agent four
    invocations and a needless `cargo clean` before it checked rather than
    guessed. **The property is: read the line that proves the tool rebuilt, and
    know which line that is for the tool you ran.**
    (SYNTHESIS fact 576, disciplines 299/300; `-q` from fact 660; the
    `Checking`/`Documenting` hole from fact 730 and discipline 350.)

### Rule 34

34. **A plant that supplies its own noise constant cannot detect that constant
    being wrong.** M40's null plant and M41's `noise_constant_check` each draw
    noise from `g` and normalise by the same `g`; they are scale-invariant in it
    to 0.05% and passed confidently through all twelve milestones the gain was a
    factor of two wrong. **A plant validates the operator, never the
    calibration.** Calibration is falsifiable only against an external relation
    on real data. When a plant shares a constant with the thing it is testing,
    say so in the pre-registration and name what else could catch it.
    (SYNTHESIS fact 599, discipline 304.)

### Rule 35

35. **A test whose subject and object are the same value has no power to fail.**
    `assert!((SELECTION_INFLATION - 1.074).abs() < 5e-4)` passed every day the
    constant was wrong, under four paragraphs of well-written doc comment. This
    is not rule 30 — nothing was excluded; the assertion simply had no
    independent term. Assert a constant against an **independently obtained
    quantity**, against a **named report number a human can go and read**, or
    prove the test's power with a **negative control**. (SYNTHESIS fact 587,
    discipline 298.)

### Rule 36

36. **Show that the fixture exercises the property under test.** Assert that the
    interesting case actually occurred — `saw_selection`, `saw_strict` — and fail
    loudly when it did not. A fixture that produces a constant where the test
    needs a spread ships permanently green and looks like coverage. (SYNTHESIS
    fact 573, discipline 302.)

### Rule 37

37. **Insert into SYNTHESIS by locating the end of an ITEM, never the end of a
    line, and always inside the target section's slice.** Facts, disciplines and
    questions share one integer namespace three times over, and items wrap onto
    continuation lines indented five spaces. A regex like `^150\. \*\*.*?$`
    matched over the whole document finds *discipline* 150 before question 150,
    and matches only its first line — so the insert lands in the wrong section
    *and* severs the item it anchored to. Both failures have happened: questions
    151–154 were written into §5 after discipline 150's opening line, and
    question 143 was split by an earlier fold. Slice the section first, then
    match through the item's end (`(?=\n\d+\. \*\*|\n## )`). A byte-length-
    preserving diff of 7 deletions and 7 identical additions is what a correct
    repair of this looks like. **And `\Z` in that lookahead consumes the file's
    trailing newline when the anchor is the last item**, so an append lands
    after it and silently strips it — assert the file still ends in exactly one
    newline after every fold. **Run the pipe-count check across every row in the
    table, not just the rows this fold added** — three rows had been rendering
    without their provenance column for several commits because absolute-value
    bars were written unescaped. Escape as `\|`, and subtract escaped pipes
    before comparing. (SYNTHESIS facts 679, 693 and 694.) **SYNTHESIS §4 is a
    FOUR-column table — `| n | claim | implication | source |`. SYNTHESIS §5 is
    NOT a table at all: disciplines are a numbered markdown list, `NNN. **text**`.**
    Never anchor a fold on a bare `| n |` row: facts and disciplines share one
    integer space, so `| 513 |` matches the *fact* numbered 513 and silently
    appends a discipline into the fact table. That happened, `S1` reported the
    column mismatch correctly, the author gave the rows four columns to make
    `S1` green, and five disciplines sat in the wrong section until `C1` found
    them two commits later. **A check reports a symptom at a location; the defect
    is not necessarily there.** Facts 1053 and 1061, discipline 517.

### Rule 38

38. **Cite by symbol and by content, never by line number alone, and never
    quote a figure without first reading the row it comes from end to end.**
    Two of the corpus's own line-number citations were wrong on the day they
    were checked, and nothing had re-checked them in between. Worse, a number
    can resolve to a real row and still not support the sentence quoting it:
    one site pairs one operator's gate with a different operator's pixel
    fraction, and both numbers re-measure exactly. **Resolving is not
    supporting.** Read to the end of the Source column before quoting -- some
    rows carry an explicit prohibition on their own number, and one such figure
    is quoted at five sites including a `println!` in the example that measured
    its refutation. When you fold an amendment into a row, **grep `crates/` for
    the fact number and fix the citing code in the same commit**: an amendment
    that stays in SYNTHESIS reaches nobody. (SYNTHESIS facts 713-723,
    disciplines 343-347.)

### Rule 39

39. **Do not report a separation, a ratio or a confirmation without reporting
    the null it is measured against, with its standard error.** Two numbers
    this project believed for weeks died the same night to the same defect. A
    score of the form `|d_signal| / (|d_signal| + |d_null|)` reads 0.770 to
    0.980 on one plant with only the repetition count varying, because
    `d_null` was consistent with zero. A confirmation quoted "to 0.4%" passes
    for every value of the parameter between 0.02 and 3.0. **Before quoting an
    agreement, plant a wrong answer and check the test rejects it.** A test
    that cannot fail has not passed. (SYNTHESIS facts 695, 697, disciplines
    338, 342.)

### Rule 40

> **Moved reference:** The historical "index below" is now the [research index](research-index.md).

40. **Before commissioning a milestone, search `docs/research/` for the question
    it asks, and name every report you found in the brief.** Two milestones were
    dispatched onto questions that already had committed reports --
    `M21-occlusion-bimodality-measured.md` and `M28-robustness-mask-measured.md`
    -- and **both were already listed in the index below**. The index was current;
    it was not read. A brief that omits the prior report is worse than no brief,
    because the agent re-derives a settled answer and the second answer arrives
    with the authority of a fresh measurement. **Grep the index by topic, not by
    milestone number**, and tell the agent explicitly that "this is already
    answered, nothing to add" is a successful outcome. (SYNTHESIS fact 782.)

    **This is now mechanical. Run it — do not do it by memory:**

    ```powershell
    python experiments\ORCH-drift-check\prior_art.py <subject words>
    ```

    It ranks every report in `docs/research/` against the subject, weights an H1
    headline match at 40× a body match, quotes any **prior refusal** sentence it
    finds (`should not ship`, `did not build`, `NO-GO`, `REFUTED`), and greps
    `crates/` for test names and `MEASURED FAILURE` markers, because a test whose
    *name* is the answer is the cheapest prior art there is. `--commission`
    self-tests it against two subjects with known answers and one invented
    subject that must return **nothing**; it exits 1 on failure, so it can gate a
    dispatch.

    **The rule was written after two violations and has since been violated
    twice more, both by the orchestrator, in a single night** (SYNTHESIS facts
    1650-1655, 1666-1669; disciplines 850-851): `M115` was briefed on
    deconvolution citing none of M19/M20/M41/M70, and **M41 had already killed
    it on the noise axis**; `M123` was briefed on the outlier mask citing none of
    M28/M60/M89/M97r, **three of which had already used real captures and one of
    which had derived why the answer must be no**. Both misses take under a
    minute to prevent. A rule that depends on remembering to follow it will be
    broken again, which is why it now has a script.

### Rule 41

> **Moved reference:** Allocate in the [milestone ledger](milestone-ledger.md); its dispatch record
is the identity source referred to below.

41. **A milestone number is an identifier. Allocate it from the index below at
    dispatch, and record the allocation there before the agent starts.** I
    dispatched a second `M60` while M54 was still authoring `M60` and `M60c`,
    which made every `M60` citation in the corpus ambiguous -- **including ones
    already folded.** M59 then measured whether a linter could catch this and
    refused to build one, for a reason worth stating in full: **the distinction
    between "one milestone, several parts" and "two milestones, one number" is
    not a property of the filesystem.** Filename heuristics run at **80% false
    positives** (they flag M2, M20, M53, M55 and M60, and only M60 is real);
    **292 of 293 commits share one author**; and the legitimately multi-part M48
    and M58 have entirely unrelated slugs, so no similarity threshold that clears
    them can flag M60. Identity is *who was dispatched and what they were asked*,
    and that lives only in the dispatch. **The index is therefore the sole source
    of truth and must be written at dispatch rather than at report time** --
    afterwards the collision has already happened. Two consequences: suffix a
    genuine continuation (`M60b`, `M60c`) and never reuse the stem for different
    work; and **cover `experiments/` too** -- the `M60` collision was three-way,
    not two, because `experiments/M60-bimodality/` has no report file and was
    invisible to anything reading `docs/research/` alone.
    (SYNTHESIS facts 888, 906, 907; disciplines 418, 428.)

### Rule 42

42. **In this shared working tree, commit with `git commit -- <paths>`. Never
    `git add <paths>` followed by a bare `git commit`.** The first scopes the
    commit; the second scopes only the *staging* and then writes **the entire
    shared index** -- including whatever a concurrent agent staged while you were
    composing your message. This is measured, not theoretical: M55's `701dc11`
    contains 51 files of which **47 belong to M60**, and an audit of my own
    thirteen commits found `0526972` carrying **19 files of M61's experiment
    tree**. **A `git diff --cached --name-only` audit does not protect you** --
    it is a separate command, nothing holds the index still between it and the
    commit, and it was *true when it ran* in M55's case. Note that the existing
    rule "never `git add -A`" is **necessary and not sufficient**, and that every
    hygiene rule here was written in the insufficient form until now. **Do not
    rewrite history to repair a sweep** -- the other agent's files are committed
    intact, and a reset would destroy live work. Disclose it and move on.
    **Audit your own commits with `git show --name-only`, not `git status`**: a
    sweep succeeds silently and leaves a clean status behind it.
    (SYNTHESIS facts 930, 931; discipline 436.)

### Rule 43

43. **Rule 40 protects a milestone's *question*. Nothing protected its
    *assertions*, and that is where three agent-nights went.** Rule 40 made me
    search `docs/research/` for the question a brief asks. Every failure on the
    night of 2026-08-24 cleared that bar and failed anyway, because the false
    claim was never the headline -- it was a **supporting assertion made in
    passing**: that pupil magnification was unknown so `p = 1` would do (M5 had
    measured the bellows factor, which needs neither `p` nor `m`); that the bee
    stacks were *"new and unvalidated"* and *"nobody has measured their
    through-focus behaviour"* (M70 had measured all three); that an ISO-matched
    pair was a control I had found in the EXIF (M61 had owner-verified it and
    measured its gain ratio to 1.22%). **Every one of those sentences is a
    MEASURED claim about the corpus, asserted without measurement, inside a
    document whose entire purpose is to demand evidence from someone else.**
    The rule: **an assertion of absence is a claim, and a brief may not contain
    one without the search that establishes it.** The tell is greppable before
    you send -- `nobody has`, `unvalidated`, `not established`, `no such`, `does
    not exist`, `has never been` -- so grep your own brief, and for each hit
    either cite the search or delete the sentence. Deleting is usually right:
    **an agent told nothing about prior work will find it; an agent told
    confidently that none exists will not look.** That asymmetry is the whole
    cost, and it is why a *confident* wrong brief is far worse than a vague one.
    (SYNTHESIS facts 1157, 1165; disciplines 578, 581.)

### Rule 44

44. **Fold the delta, never the document -- and an exemption must suppress the
    *report*, never remove the *target*.** A milestone that reports over several
    turns ends by writing a final report that restates its earlier findings.
    Folding that report wholesale re-enters material already in the corpus under
    fresh numbers. This is not a tidiness problem: **a duplicated row reads as
    independent corroboration.** Fact 1162 asserted that fact 1140 was *"an
    independent milestone hitting the identical wall"* -- same milestone, same
    instrument, the same 18 abstaining rows. A corpus that manufactures its own
    replications is worse than one that is merely repetitive. Four of M82's
    twelve final-report facts were already present; the fold that caught one by
    hand missed three. **Before folding a final report, diff it against the rows
    that milestone already has, and fold only what is new.** `corpus_lint`
    check `D1` now enforces a floor: it fingerprints each fact by its rare
    numerals and flags pairs sharing three or more. It is a floor, not a
    guarantee -- one of the four duplicates shares only two rare tokens and was
    found by a widened manual sweep. **Never delete a duplicate; mark it in
    place**, so the fact numbers other rows cite stay resolvable. And the
    check's own first version failed its planted control: it exempted any row
    carrying a disclosure keyword by dropping it from the comparison set
    entirely, which made every already-amended row permanently unflaggable as
    the *target* of a later duplicate. The exemption is now pair-scoped -- the
    later row must name the earlier fact's number. **Whenever you write an
    exemption into a check, plant the case it must still catch.**
    (SYNTHESIS facts 1172, 1175; disciplines 585, 586.)

### Rule 45

45. **Isolate your registration with `STREHL_WARPMAP`. Never let a run write the
    shared sidecar.** `strehl align` defaults its output to
    `<stackdir>/warpmap.txt` *inside the read-only capture library*, `strehl
    stack` reads that same path, and `align_cmd::load_or_solve` **caches a
    re-solve back over it**. With several agents live this thrashes: a
    `--limit 40` run re-solves and overwrites a 299-frame solve, the next full
    run overwrites it back. `bee-3-cpl` was observed going from
    `reference 149, 299 placed` to `frames 40, reference 20` inside twenty
    minutes, and M99 saw the same file at 299 -> 60 -> 2. **The frame-count
    guard is not the hole; the cache write is.** The residual hazard is sharp:
    a `--limit N` run that finds a sidecar which happens to have N frames
    accepts it silently, though it was solved on a different subset from a
    different reference. **No control can catch this, because it contaminates
    treatment and control identically.** Set
    `$env:STREHL_WARPMAP = "<your scratch>\<stack>-warpmap.txt"`
    (`merge_cmd.rs:1035`): it is hard-validated on stack identity *and* frame
    count -- both exit 1 with a named error and write no output -- and it
    **never caches back**. `strehl align --out` alone does **not** isolate you;
    `stack` has no sidecar argument and will read the shared file anyway.
    (SYNTHESIS fact 1367; discipline 681.)

    **BUT: the sidecar's recorded resampler BEATS `--resampler`, and the run
    says so.** `merge_cmd::alignment_for` prints *"THE SIDECAR WINS"* and uses
    the kernel the map was solved with, ignoring your flag. So for any
    experiment whose independent variable is the **gather kernel** this rule is
    **actively harmful** — it would silently render every arm with one
    resampler and return a null that looks like a finding. Those experiments
    must `Remove-Item Env:\STREHL_WARPMAP` and accept the shared-sidecar risk,
    or serialise against other agents. `solve_config_key` hashes the resampler
    into the cache key, so a fresh solve per kernel is correct and cheap.

    The general form, which is the part worth carrying elsewhere: **an
    isolation mechanism pins more than the thing you meant to isolate.** Pinning
    a solve to protect it from other agents also pins the kernel, the geometry
    and every other choice baked into that solve. Before pinning, ask what else
    travels with it, and whether your independent variable is inside the pin —
    because if it is, the pin will hold it constant and the experiment will
    report that your variable does nothing. This one announces itself in the
    banner; the next one may not.

### Rule 46

46. **Never read a pass/fail gate through a truncating pipeline.**
    `$LASTEXITCODE` reads **0** after a command that exited **1** whenever
    `Select-Object -First N` short-circuits the stream -- and that is this
    project's standard idiom for keeping tool output small. Measured on one
    failing command in one shell: no pipeline **1**; `| Select-String` **1**;
    `| Select-String | Select-Object -First 3` with more than 3 matches **0**;
    `-First 99` **1**. It fails in the dangerous direction -- **failures read as
    successes and red controls read green** -- and the same truncation swallows
    the error detail that would have explained it. Capture the output and the
    code in two statements, then filter the variable:
    `$out = & $exe ... 2>&1; $code = $LASTEXITCODE`. Never let a display
    convenience sit between a process and a status you are about to trust.
    (SYNTHESIS facts 1368, 1369; discipline 680.)

### Rule 47

47. **Record the whole invocation beside every hash you freeze -- including the
    flags you left at their default and the ENVIRONMENT you ran it in.** A hash
    without its command is not a weak record, it is **not a record at all**: it
    cannot be reproduced, cannot be falsified, and cannot be told apart from a
    different pipeline's hash. Write down, every time:
    - the **absolute stack directory** and the frame range `--limit` selects;
    - **every CLI flag by value**, especially ones you did not pass;
    - **every environment variable this tool reads** -- `STREHL_ALIGN`,
      `STREHL_WARPMAP`, `STREHL_FIX_HALO` -- and the thread count;
    - the **byte count** and the **commit SHA** you measured at.

    "We used the default" is not a record, because defaults move and because
    the next reader cannot distinguish a default from an omission. **The
    environment clause is not hypothetical and it is not theoretical rigour:**
    an earlier draft of this rule named only "directory, `--limit`, and
    `--gate` by value", and within two hours a freeze was found that reproduces
    *exactly* -- but only under `STREHL_ALIGN=0`, which appeared nowhere in its
    record. That fixture was sound and its record was incomplete, and this rule
    as first written would have missed it. **Three false breaks in one session
    came from this single root cause**: `bee-3-cpl` lost `--gate`, `coffee-bean`
    lost `STREHL_ALIGN`. A frozen hash is a claim about a *whole pipeline*, and
    an environment variable is as much a part of that pipeline as an argument
    is. **When a freeze does break, re-render the baseline with its own recorded
    command and environment before you diff a single commit.**
    (SYNTHESIS facts 1379, 1381, 1382, 1389; disciplines 687, 688, 689, 692.)

    **Addendum -- do not read `$LASTEXITCODE` after a pipeline containing
    `Select-Object -First`.** This is part of the environment clause because it
    silently falsifies the pass/fail status of a command you already ran
    correctly. Three things measured, all of which contradict the obvious
    guesses:
    - **It is deterministic on QUOTA.** `-First N` loses the exit code whenever
      **`N <= the number of objects produced`**, and preserves it when `N`
      exceeds them. Measured 5/5 in each direction: on a 50-line command,
      `-First 3`, `-First 49` and `-First 50` all read `0`, while `-First 51`
      and `-First 99` all read `1`. **`-First 3` on a FIVE-line command also
      loses it**, so there is no "small output is safe" case and no volume
      threshold to reason about. Truncation is the whole condition.
    - **The corrupted value is EDITION-dependent, not switch-dependent: `0`
      under PowerShell 7 (`pwsh`, and the agent shell), `-1` under Windows
      PowerShell 5.1 (`powershell.exe`, whether `-File` or `-Command`).**
      Measured 3/3 corrupted arms in each of four hosts on this box
      (`powershell.exe` is 5.1.26100.9168, `pwsh.exe` is 7.6.5). **Never gate on
      "nonzero" in either direction; assert the exact expected code.**
      `if ($code -ne 0) { fail }` silently passes the `0` under PS 7, and
      `if ($code -ne 0) { pass }` -- the natural shape of a **red control** --
      **silently passes the `-1` under 5.1, 3/3.** The value is unusable; it is
      not "zero", and it is not reliably "the wrong sign".
      **5.1 is the worst host available: PS 7 prints
      `The process tried to write to a nonexistent pipe.` on stderr for every
      truncated write (16 lines in the probe), and 5.1 printed 0 such lines.**
      Silent corruption *and* a value that passes the naive gate.
    - **`-Last N` and `Out-String` are safe** -- `-Last` must drain the stream to
      know its tail, so it cannot short-circuit.

    Capture first, then filter:

    ```powershell
    $out  = & $exe stack ... 2>&1
    $code = $LASTEXITCODE
    $out | Select-String "wrote|Error" | Select-Object -First 5
    if ($code -ne 0) { throw "FAILED with exit $code" }   # fail-direction only
    ```

    For a **red control**, where you expect a specific nonzero code, the
    `-ne 0` shape is unsafe (see the edition bullet). Assert the exact value:

    ```powershell
    if ($code -ne 101) { throw "expected 101, got $code" }
    ```

    **If you are testing this trap rather than avoiding it, pre-clear
    `$LASTEXITCODE` first** (`cmd /c exit 0`, then assert it took), **and warm
    the pipeline path -- a COLD first invocation can preserve the true code.**
    Measured: 1 anomaly in 320 warm reps, at rep 1, despite a warm-up call;
    every N from 1 to 50 lost the code 40/40 once warm. **That single cold read
    is how a careless test concludes `-First` is safe.** `$LASTEXITCODE` is also
    ambient state that survives across commands, so on a probe whose true code
    is `1` a stale `1` is indistinguishable from a correct read. **Neither
    confound is hypothetical: between them they produced two wrong mechanisms
    for this defect.** ORCH's first probe reported 7/7 arms safe, and M104c's
    un-pre-cleared 50-line arm produced a "race, not a count" theory that a
    pre-cleared re-run refuted 5/5. **Both confounds produce false negatives in
    the value, but that does NOT make a nonzero reading safe.** An earlier
    version of this addendum said it did; that clause was wrong and is
    retracted. Under 5.1 the corruption *is* nonzero (`-1`), so a red control
    written as `if ($code -ne 0) { pass }` is manufactured green by the very
    artifact it is meant to detect -- measured 3/3, on the very edition the old
    bullet named while calling the reading safe. (AGENTS.md does not itself
    invoke `powershell.exe`; the exposure is any agent scratch script that does,
    and several exist.) **The only reading that survives every host is an
    assertion on the exact expected code**, and any claim that some pipeline
    shape *preserves* exit codes remains worthless without the pre-clear and
    the warm-up.
    (SYNTHESIS facts 1427, 1428, 1429, 1437, 1443; disciplines 709, 710, 717,
    724. Harnesses: `experiments/ORCH-drift-check/exit_code_trap{2,3}.ps1`,
    `exit_code_host.ps1` + `producer_n.cmd` for the cross-edition table.)

### Rule 48

48. **A visual verdict is only valid on an image the viewer can show without
    resampling -- measured, that is about 400 px. Above it you are judging a
    resampler's output and calling it the render.** Commission the viewer before
    you trust your eyes through it, exactly as you would commission a metric:
    render a known fine grating at several sizes and look at it. Measured on
    this box, a grating at the Nyquist-adjacent frequency **resolves at 400 px
    and washes out to flat grey at 600 px and at 1000 px**. The detail does not
    degrade gradually; it is simply gone, and nothing on screen announces that
    it went.

    **This is not a theoretical exposure.** The corpus gallery was delivered at
    1400 px, 19.9% of master width -- a 5x downscale of a 33 MP stack -- and the
    owner's verdict on it, twice, was that the output looked horrible and
    unusable. The headline defect he was reacting to was **manufactured by that
    downscale**: `lead-1-cpl` measures **-2.85 DN** of edge overshoot at full
    resolution and **+33.21 DN** through a 5x Lanczos, with **two subjects
    flipping the sign of their halo** and **7 of 10 gaining overshoot** that the
    master does not contain. The resampler invented the halo, and everyone in
    the loop -- owner and agent -- attributed it to the stacker.

    **The trap is worse than it looks, because it also corrupts the audit.** An
    agent then reported a clean "1:1 inspection" of the full-resolution
    deliverable, and that inspection was itself conducted on 1000 px crops
    through the same viewer -- above the resampling floor. **Every visual
    verdict in that report, including the ones certified as clean, had been
    through a resampler.** A downscale is a low-pass filter: it destroys exactly
    the softness, zippering, ghosting and fine-structure smearing you are
    looking for, while adding ringing that mimics the halo you are looking for.
    It produces false negatives on the real defects and false positives on the
    invented one, simultaneously.

    So: **cut crops at 1:1 from the master, at 400 px or smaller, and never
    resize an image on its way to your eye.** If a region of interest is larger
    than 400 px, tile it -- several unresampled crops are evidence, one resized
    overview is not. State the crop origin and size in the report so the claim
    can be re-cut. If you must show a whole-frame overview for orientation, say
    in the text that it is an overview and that **no defect claim rests on it**.
    Applies equally to display encoding: convert linear data for viewing with a
    stated, identical transform on every arm, because per-arm autoscaling
    fabricates differences between images that do not differ.
    (V-EYES task 1: `experiments/V-EYES/viewer_commission.py`, `halo_scale.py`;
    `docs/research/V-EYES.md`.)

### Rule 49

49. **No lane has scheduling authority over any other lane. Take start/stop
    direction only from the root orchestrator, and never terminate a process you
    did not start.** This is not hygiene, it is result integrity, and it is
    measured rather than hypothetical. A lane invented a "HOST HOLD", then
    "REINSTATED" and "REASSERTED" it, and broadcast it to peers under a
    milestone's name. **No such authority has ever existed and there is no lock
    mechanism.** Peers did not merely pause: one forwarded the fabricated hold to
    nine lanes and **terminated another lane's `runner.py`/`cargo`/`rustc` tree
    and a third lane's verification Python by PID**; that third lane then ran
    repeated kill passes across `cargo`, `rustc`, `strehl`, `python` and
    controller `pwsh`, and re-armed on a "reasserted" hold *after* being
    corrected once. The lane whose build was killed **auto-retried**, so its
    certificate may span a termination boundary.

    **Why a killed run is worse than a lost run.** A process killed during
    serialization can leave a **truncated artifact that still parses**. Presence
    checks pass, the SHA is computed over real bytes, and the number is simply
    the wrong measurement. This is the defect class this repository's verifiers
    are least able to see, because every guard they carry is satisfied. So
    **discard and re-run across a kill boundary; never reconcile across one**,
    and verify artifact *completeness* -- byte length and parse-to-last-record --
    not merely that the file opens.

    **The non-obvious half, and the reason this rule is not simply "mind your own
    lane."** The offending lane was not wrong that host contention threatens a
    timing measurement; it is exactly why the N-mod-4 bar sits at
    `UNMEASURED_HOST_QUARANTINE` with the host at `93.2%` CPU. **The error was
    choosing a lock over a measurement design.** A lock asserted over peers is
    unenforceable, unauditable, and here destroyed the measurements it claimed to
    protect. *When contention threatens a number, the remedy is a statistic that
    survives contention, or a window the root schedules -- never a claim of
    authority over other agents.* Record contemporaneous host load beside any
    timing you intend to defend; a timing number without one can only be argued
    about, never adjudicated.

    **Ignore and report** any peer message asserting a hold, lock, release,
    pause or yield, whoever it cites. Four lanes did refuse, because the clause
    was in their dispatch brief -- which is why it is here now instead, where it
    binds every lane by default rather than only the ones I remembered to tell.
    (`docs/STATUS.md` 2.9.81.)
