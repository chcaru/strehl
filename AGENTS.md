# AGENTS.md — strehl

Noise-aware RAW focus stacker. Rust. CFA-native. Pluggable focus measures, merge
strategies and alignment models. Camera and lens knowledge is a **profile** — a
data file, not a plugin: measurement kept reclassifying "camera constants" as
per-stack quantities that are cheaper and more accurate to fit at runtime. See
`SYNTHESIS.md` §3.4.2 for exactly what survives.

Read [`docs/research/SYNTHESIS.md`](docs/research/SYNTHESIS.md) before changing
anything architectural. It is the decision record and it lists what lost.

## Licence discipline — read this before opening any other repository

This project is **MIT OR Apache-2.0**. Reading GPL source would contaminate it.

**Never open, read, browse, or copy from:**

| Project | Licence |
| --- | --- |
| enfuse / enblend | GPL-2.0 |
| `align_image_stack`, Hugin | GPL-2.0 |
| EPFL Extended Depth of Field | GPL-3.0 |
| ChimpStackr | GPL-3.0 |
| darktable (**including `exif.cc`**) | GPL-3.0 |
| RawTherapee, ART, Filmulator | GPL-3.0 |
| `librtprocess` | GPL-3.0 |
| ExifTool Perl source | GPL-3.0 |
| `rawler` / `dnglab` **source** | LGPL-2.1 — link only, do not read |

**Safe to read:** PetteriAimonen/focus-stack, z-stackr, stackaroni, `rawkit`
(all MIT/Apache-2.0).

**Do not link:** `dssim` (AGPL). Use `ssimulacra2` and `butteraugli` instead.

ExifTool's *tag tables* are not an independent specification — the pages are
generated from GPL source. Tag IDs, offsets and enum values are uncopyrightable
facts and may be used; the surrounding prose may not. Never read the Perl.

`rawler` is LGPL-2.1 and we link it. Ship it dynamically linked, or publish
object files or a reproducible build. Do not statically link it into a
monolithic binary and ship only that binary.

## Rules

1. **Storage is u16 CFA. Arithmetic is f32.** Never store f16 — a 10-bit
   mantissa gives ~8 LSB steps on linear 14-bit data.
2. **Never materialise aligned frames.** Gather at consumption inside each
   kernel. Materialising 60 aligned RGB frames is 24 GB and demosaics 60 times
   instead of once.
3. **The noise model is injected, never re-derived per stage.** A private
   per-stage noise estimate is the exact mechanism behind the prior project's
   2–5x defect.
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
5. **Fit geometry at runtime; do not bake it.** Scale drift and the scale
   centre are per-stack quantities. Only sensor calibration belongs in a
   profile, and profiles live in data files.
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
   pair), composing nothing. **Discard spans 1-2 from the solve.** Then run one
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
7. **Never compute statistics over the full decoded buffer.** `rawler` returns
   7168x5120 for the A7C II but fills only the 7032x4688 active area. The rest
   is synthetic zeros, not black level.
8. **Every performance or quality claim needs a command that was run.** Label
   claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED.
9. **Pair every sharpness metric with a flat-ROI control.** A sharpening pass
   raises gradient energy on featureless foam; that is how the prior project
   fooled itself. **This rule was written, published, and then broken by M38**,
   whose detail metric credits regularised argmax with **+35.47% "detail" on a
   flat ROI** — caught by an independent verifier, not by the author who had
   this rule in front of him. The control is one line. Run it *first*, not as
   a closing check, because a metric that fails it invalidates every number
   already computed with it.
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
11. **Every claimed defect needs a placebo, and every headline number needs a
    regression test on its own code path.** What proved argmax was the cause of
    M2's 1.253x was not a better measurement of argmax — it was a *different
    merge rule* on identical data (mean, 0.534x) and a selector with the same
    winner histogram but no noise coupling (0.981x). Without those it was only
    correlational. And the 1.253x itself had 52 tests behind the library and
    zero covering the code that produced it.
12. **The author never verifies their own work.** M2 was self-verified
    thoroughly and still shipped five wrong supporting numbers, two of them in
    the direction that loses an argument. See `docs/research/M2-verification.md`.
13. **Sweeping a parameter? Check the plant can express the failure first.**
    M11 swept the focus window on a fronto-parallel plant and reported it "still
    improving" at the widest setting. That plant is mathematically incapable of
    producing an interior optimum for a symmetric window, so the result was not
    weak evidence — it was **none**, and it cost the project a window less than
    half the right size. Ask what the stimulus would have to contain for the
    answer to be anything but the endpoint. **Report an endpoint argmin as "no
    turnover found within the sweep", never as an optimum.**
14. **Verifying the read-only corpus guarantee? Use `Get-ChildItem -Force`.**
    Without `-Force` it silently skips hidden and system files and under-reports
    `C:\dev\macro` by **1081 files / ~312 MB**, which looks exactly like
    evidence that the tree was modified. Correct totals: **18530 files /
    286,893,514,060 bytes**. Also: `C:\dev\macro\test\119MSDCF` and
    `D:\personal\macro\119MSDCF` are the **same 33 frames**, verified
    byte-identical through a full measurement sweep. Two stacks must mean two
    *different* stacks — use 109/119 or 112/113, never a directory and its
    mirror.
15. **"Halo" is overloaded — never use the bare word.** In the plugin interface
    and SYNTHESIS fact 32 it is the *rectangle expansion* a filter needs beyond
    its output tile (19.42 / 32.39 / 89.23 plane px), an alignment and warp
    margin. In the stacking literature it is the *artifact* at an occluding edge
    where the selector drags one surface across another. Say **"plugin halo"**
    or **"occlusion halo"**.
16. **Timing a parameter sweep? Alternate direction and take the per-setting
    minimum.** M14 measured a single forward sweep at **−0.7%** and a reverse
    sweep at **+19%** on the same binary and settings, and a function reading
    **21% slow** purely for being timed last. Thermal drift, clock ramp and
    cache warming all correlate with sweep position, so a one-directional sweep
    attributes them to whichever parameter came last. Use several alternating
    sweeps, report the minimum per setting, and quote a near-flat result as a
    **bound, not a value** — two honest runs of the shipped cost sweep
    disagreed 0.69% vs 1.28%, which is larger than either is from zero.
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
18. **Say which direction each metric can be fooled in, next to where you use
    it.** `mean |∇|` rises when a merge *manufactures* detail exactly as it does
    when a merge preserves it — measured, plain argmax reads **above ground
    truth** at σ=0.050, and the Wiener output carries 24% more gradient
    magnitude while carrying 12% *less* gradient correlation with truth. So it
    is admissible as a test against **collapse** and inadmissible as evidence of
    quality. A metric with no stated failure direction is not an acceptance
    criterion.
19. **kebab-case** for directories and files. Crates are `strehl-*`.
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
21. **A fitted constant cannot gate the model it was fitted to.** Where a
    constant was obtained by inverting a relation, gate that relation with an
    *independently predicted* value instead. `B = 1 + m/p = 3.000` from pure
    geometry predicts M5's measured knee to **2.1%** — that is a real gate, it
    costs one line, and it was available the whole time.
22. **The rules in this file are an executable checklist, not a creed.**
    Rules 4, 9 and 10 were each written down, published, and then violated by a
    later milestone *by the same author who wrote them* — M30's fact 242 is a
    raw argmax (rule 4), M38's detail metric shipped with no flat-ROI control
    (rule 9), and fact 88 compared a spatial sd to a temporal sigma (rule 10).
    All three were caught by independent verifiers. **Agreeing with a rule does
    not execute it.** Before publishing a milestone, walk this list and name,
    per rule, the line of code or the command that discharges it.
23. **`scipy.ndimage.sobel(cube, axis=k)` smooths every axis except `k`.** It
    applies `[-1,0,1]` along `axis` and `[1,2,1]` along all others — so passing
    a `(frames, y, x)` cube silently smooths along the **frame axis** and
    changes the focus measure. M32 did this and inflated its headline σ-count
    by ~1.7–1.9×. Extract the 2-D plane first, or pass `mode`/`axes`
    explicitly. **General form: any separable filter applied to an array with a
    non-spatial axis will touch that axis unless you stop it.**
24. **Verification must re-choose, not re-compute.** Across four independent
    passes over fourteen milestones, **every published number that was checked
    reproduced exactly**. Not one defect was arithmetic. All were *choices* — of
    nuisance estimator, reference, arm, null, or library default. A verifier who
    recomputes the author's formula on the author's inputs confirms every one of
    them. So a verification brief must name the choice points and require a
    different defensible setting at each. See discipline 253.
25. **Claim a number block before you use it, and check the claim
    programmatically, per namespace.** `SYNTHESIS.md` has **three** independent
    numbering spaces — facts (`§4` table rows), disciplines (`§5` list items) and
    questions (`§10` list items) — and disciplines and questions legitimately
    share numbers. M19 wrote "M19 owns 120–139" while M20-V already held 122–139.
    Run the collision check in `experiments/*/fold-*.py` before writing, **never
    eyeball it**, and if a block is taken, shift the whole block to open ground
    rather than interleaving. Record the shift in the fold and in the report.
26. **Prove that a diagnostic does not perturb the output, by hash.** Any
    statistic, probe or observer added to the merge must ship a run showing
    **byte-identical output** with it on and off, placebo included — the way
    fact 420 does. An argument that a channel is read-only is not evidence that
    it is.
27. **Before declaring a long-running process dead, state what a healthy one
    would look like at this instant.** If a working run and a failed run predict
    the same observation, the observation is not evidence and the correct action
    is to wait. Three specific traps, all of which fired here (see
    [`2026-08-external-review.md`](docs/proposals/2026-08-external-review.md) §5
    item 6): **zero bytes on disk is not zero work** — an agent that reads for
    three hours before its first write is indistinguishable from a corpse under
    a file-count probe; **a turn counter read at 473 s measures the sampling
    instant, not the run**; and **a stand-down is an intervention, not an
    observation** — telling live workers to stop causes the silence it was sent
    to diagnose. Ten agents were written off on this evidence and every one of
    them later landed a folded milestone.
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

31. **Fold from a committed revision, and record its sha in the source
    column.** Fact 548 was folded from a milestone report while it was still
    untracked; the report was then revised twice, and its own supersession note
    described the fold against *its own latest draft* rather than the draft
    actually folded — so it named the wrong clause, in good faith (fact 554).
    A report cannot describe what a fold says; only the fold can. Two defences:
    fold only from a committed sha and cite it, and when a milestone reports a
    correction, **re-read the folded row itself** before believing the report's
    account of it.
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

34. **A plant that supplies its own noise constant cannot detect that constant
    being wrong.** M40's null plant and M41's `noise_constant_check` each draw
    noise from `g` and normalise by the same `g`; they are scale-invariant in it
    to 0.05% and passed confidently through all twelve milestones the gain was a
    factor of two wrong. **A plant validates the operator, never the
    calibration.** Calibration is falsifiable only against an external relation
    on real data. When a plant shares a constant with the thing it is testing,
    say so in the pre-registration and name what else could catch it.
    (SYNTHESIS fact 599, discipline 304.)

35. **A test whose subject and object are the same value has no power to fail.**
    `assert!((SELECTION_INFLATION - 1.074).abs() < 5e-4)` passed every day the
    constant was wrong, under four paragraphs of well-written doc comment. This
    is not rule 30 — nothing was excluded; the assertion simply had no
    independent term. Assert a constant against an **independently obtained
    quantity**, against a **named report number a human can go and read**, or
    prove the test's power with a **negative control**. (SYNTHESIS fact 587,
    discipline 298.)

36. **Show that the fixture exercises the property under test.** Assert that the
    interesting case actually occurred — `saw_selection`, `saw_strict` — and fail
    loudly when it did not. A fixture that produces a constant where the test
    needs a spread ships permanently green and looks like coverage. (SYNTHESIS
    fact 573, discipline 302.)

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

### Milestone allocation ledger (rule 41 -- written at DISPATCH, not at report time)

A milestone number is an identifier. Allocate here **before** the agent starts, and
record the stem, what it was asked, and where it writes. `experiments/` counts: the
`M60` collision was three-way precisely because one claimant lived only there.

| stem | dispatched to do | writes to | state |
|---|---|---|---|
| `M60` / `M60b` / `M60c` | speckle-citation repair in `merge.rs`, then the gate's justification | `docs/research/M60b-*.md`, `docs/research/M60c-*.md` | reported |
| `M60` (collision, renamed **M63**) | measure through-focus bimodality | `experiments/M60-bimodality/`, `docs/research/M63-bimodality.md` | reported; report renamed to M63, **experiment dir deliberately keeps the M60 stem** with a forwarding note |
| `M61` | photon transfer curve at ISO 500/1000 | `docs/research/M61-ptc-high-iso-measured.md` | reported; provenance correction routed |
| `M62` | the square-root-N acceptance harness | `experiments/M62-sqrt-n/`, `docs/research/M62-sqrt-n.md`, `docs/research/M62-ruling-M64.md` | reported; **acceptance authority; CERTIFY, narrowed to CERTIFY-CONDITIONAL on M66** |
| `M64` | make the estimator the default path | `crates/**`, `docs/research/M64-estimator-default.md` | reported; **CERTIFIED by M62** |
| `M65` | `n_eff` under regularised vs raw election, at matched tolerance | `docs/research/M65-election-gate-measured.md` | reported |
| `M66` | is the gate N-dependent, given it compares against a max over N? | `docs/research/M66-gate-n-dependence.md` | reported |
| `M67` | does the merge admit the RIGHT frames? (facts 951, 966) | `docs/research/M67-focus-correctness.md` | reported; **YES -- 99.955% on a simulated stack, and the GATE not the election does it.** Turn 2 **withdrew its own asymmetry claim** (fact 1006) and designed M73 |
| `M68` | is the B plane's 0.84x a sensor conversion gain or a pre-ADC attenuation? | `docs/research/M68-b-plane-mechanism.md` | reported; **answer was NEITHER -- the binary was refused** |
| `M69` | recalibrate `FOCUS_NOISE_SD` -- the constant every gate is denominated in | `docs/research/M69-focus-noise-sd.md` | reported; **the VALUE is right (median 1.0147x, leave it alone) and the FORM is refuted (4.06x span).** Also **corrected fact 986 at source** -- M62 reproduced nothing -- and caught a false data premise in its own brief |
| `M70` | is there harvestable mid-band signal in OFF-PEAK frames? Decides the external review's #3 (multi-frame Wiener deconvolution) **core-vs-plugin**, on measurement. Anchored on fact 27's measured f/11 cutoff at 0.2762 cyc/px. Uses the corpus's 19-299 frame span as a free ~15x step-density design. **Read-only in `crates/`.** | `docs/research/M70-through-focus-spectrum.md`, `experiments/M70-through-focus-spectrum/` | **reported and folded (facts 1074-1086, disciplines 521-524).** **VERDICT: PLUGIN**, by three independent routes. Granted the review's premise (off-peak mid-band amplitude 0.879-0.970 at one step, 12/12 stacks) and **refuted the inference** -- the off-peak signal is the same spectrum scaled down (eigen-share 0.9959), and over scaled copies a matched filter *is* a weighted average. **ANSWERED FACT 1036 IN THE THESIS'S FAVOUR** (fact 1075) and **refuted the orchestrator's own sharpened mechanism** (fact 1076): it is the gate's threshold, not its domain. Found a **noise-rectification law** in its own estimator, retracted a misreading it had taken from SYNTHESIS's compressed rendering rather than the source (fact 1080), and **found `S1`'s blind spot** by auditing all 36 of its tables |
| `M71` | **the delivered flat fields.** PRNU `kappa` and whether it enters the noise model; an independent 50x-range PTC cross-check of facts 27/29; CPL transmission and uniformity; dust map. **Central confound: at m~2 the paper's own fibre texture is resolved and mimics PRNU** -- the defocus sweeps are the lever. **Read-only in `crates/`.** | `docs/research/M71-flat-fields.md`, `experiments/M71-flat-fields/` | **reported and folded (facts 1062-1073, disciplines 518-520).** **kappa = 0.3096%** MEASURED, paper confound bounded by measurement at 0.09-0.14%. **Ruled OUT of `PlaneNoise::variance`** as a coupling requirement, not a prohibition -- and it **withdrew its own original basis** mid-milestone after M68 retracted the premise it rested on. **The thesis-critical finding is fact 1064: the shipped noise model is ALREADY over-confident above S = 504 DN, reaching -12.8% at S = 8000, because the 2.16%-high profile gain and the absent PRNU term cancel at exactly one signal level.** Closed M68's open item and **cleared M61** (0.8699 against 0.8698). Ruled fact 1033's gain limb (**f = 0.650**) and declined its offset limb as pre-registered. **Turned fact 955 into an exclusive fork** (fact 1071). Killed three of its own results with their own controls, including a CPL effect smaller than its placebo, and disclosed two errors |
| `M72` | **is fact 895's green-plane correlation `rho` = +0.073 real, and does it belong in the model?** Averaging G1/G2 gives `var(mean)` = 0.5365 sigma^2, not 0.5 -- **a ~3.6% sigma error on every averaged-green path**, measured and unmodelled for weeks. Routed to M68 as a follow-up turn: it has just built and validated per-plane noise-covariance machinery and its G2/G1 null is the calibrated instrument for it. **Boundary: flat fields belong to M71; M72 uses dark frames and the corpus.** **Read-only in `crates/`.** | `docs/research/M72-green-plane-correlation.md`, `experiments/M72-green-correlation/` | reported; **YES it is real (+0.08261 vs fact 895's +0.0730), NO it is not a green-pair property** (margin +0.00043 where its gate needed +0.010), **and it is immaterial** (peaks 4.04% vs a 4.75% threshold, over-confident everywhere, within ~10 DN of black). **Its own confirming control was ruled MISLEADING by a control it wrote to break itself.** Fix `noise.rs:122`, not `green_luma_sigma` |
| `M73` | **real-capture admission correctness via the cylinder invariant.** For an axis along the image `y`, a **constant-radius cylinder** gives depth depending on `x` alone, so `k*(x,y)` is independent of `y` -- ground truth needing **no fit** on that axis. **CORRECTED by M73 (fact 1040): this row, M67's report and my relay to the owner all said 'surface of revolution', which is FALSE** -- a varying radius `r(y)` breaks the invariant. Failure signature is a residual **shaped like the text** = contrast-driven admission. Carried a transferred prediction that could refute M67's own published result, **which is why M67 designed it and did NOT run it.** | `docs/research/M73-cylinder-invariant.md`, `experiments/M73-cylinder/` | reported; **M67's prediction REPRODUCED (12.3-15.1% vs its 12%, four numbers inside the registered band) -- the first plant-to-real transfer in the project.** But **at the shipped gate this subject admits `n_eff/N` = 0.0095 / 0.0147, singleton at 81.4% / 58.7% of pixels: the estimator runs as a SELECTOR here** (fact 1036, UNROUTED). **M67's 'gate not election' framing does NOT transfer** -- +7.04/+12.09 pp against the plant's +60.26, because the real election is twice as accurate. Ink-locked bias **absent and bounded**. **Disqualified its own registered rule** with a direction-independent proof |
| `M74` | **does the FINE field carry the same form defect M69 found in the coarse one?** Facts 500/580/753 settle `FINE_FOCUS_NOISE_SD`'s **scale**; its **form** has never been asked about. The fine field is deliberately **unregularised** (`field.rs:19`), and M69's mechanism -- gradient-direction coherence across the operator's support -- has no obvious reason to stop at a change of window radius. **Load-bearing because `merge_cmd.rs:1707` divides by it to build `bimodality_sigma`, which I wrongly told it M60 consumes -- **the milestone is M63; `experiments/M60-bimodality/` is a directory named for the wrong milestone** (fact 1049)**: a drifting denominator there is the M66/`tolerance()` defect one level down. Secondary: M66's unrouted `<=` tie in the gate (0-3 px of 515,094) -- **is admitting ties a defect or correct estimator behaviour?** **Continuation in M69's agent** (`57718757`). May touch `crates/` only with pre-registration plus a re-run of M62's battery. | `docs/research/M69-focus-noise-sd.md` (extended), `experiments/M69-focus-noise-sd/` | reported; **the fine field's form PASSES -- `D = 1.371x` against the coarse field's `4.062x`, inside a `<1.5` bar registered first. The first constant in this project to survive a form check.** Mechanism is **normalisation order, not window radius** -- proved free by a non-monotone ordering (29x29 bare beats 23x23 regularised). **Published the limb that damages its own headline:** the plant is homogeneous, and within one real stack the fine field spans **1.70x-3.99x**, so the same `bimodality_sigma` z means 0.255 to 1.246 true sd by pixel location. **Counter-finding, orchestrator-verified at `through_focus.rs:724`: the consuming site is immune BY DESIGN** -- `bimodality_sigma_cut` has *no default in this crate on purpose*, names its order statistic, and mandates per-stack placebo calibration. The first hazard in this corpus designed out before a milestone found it. **Ruled the `<=` tie NOT a defect**: `merge.rs:746` admits the winner separately, so `<=` admits only non-winner exact ties, which is estimator-correct. Broke a confound against its own prediction: **`P2`'s undeclared domain is TEXTURE, not ISO** |
| `M75` | **the R-and-B-together asymmetry: two unexplained findings that may be one.** M68's `E1` found a vertical gradient **common to R and B with both greens flat** (R/G1 trend -0.066, r = -0.911), destroyed its own explanation of it, and left it **unallocated** (fact 995). M72 independently ended with *"why R is decoupled from all other planes"* unsettled. **Both are R/B-versus-green asymmetries in the same dark frames.** Question: are they one phenomenon, and does either bear on M68's still-open B-plane mechanism (`alpha_B/alpha_G2 = 0.85235`, ruled NEITHER candidate)? **Continuation in M72's agent** (`3b7b18a7`), which has the per-plane covariance machinery built and validated. **Must not touch `D:\personal\macro\flat-fields` (M71 owns it) nor anything under `crates/`.** | `docs/research/M75-rb-asymmetry.md`, `experiments/M75-rb-asymmetry/` | **reported and folded (facts 1054-1060, disciplines 514-516).** **Answered NO on three independent separators, and INVERTED M68's headline in the process**: the vertical gradient is a **green** effect, not an R-and-B one -- M68 measured a ratio and what moves in it is the denominator. It nevertheless **does** bear on M68's open B-plane question, being a row-dependent per-plane analog scale and the first direct evidence such scales are not constant across the array, which is why gate D1 failed. Honoured a pre-registered criterion that fired against its own headline, then **deleted the fit rather than pick the estimator that flattered it** -- and the model-free re-measurement found **two** gradients, split by the dual-gain switch. Fact 995 corrected in both halves |
| `M76` | **the low-`\|z\|` stratum gate: three residuals M55 disclosed against its own interest and did not close.** The acceptance spec is what certifies every candidate merge, so a hole in it sits under everything. **Q1 (the one with no data at all): does `d`'s between-repetition variance grow as `\|z\|` falls?** If it does, the gate penalises candidates for **cell noise** rather than candidate quality, and every verdict the harness has issued inherits the bias. M55: *"the observable that settles it is cheap and already exists"* -- B7's `REPS` sweep run per cell. **Q2: is the constant-`\|z\|` evasion closable in code?** A candidate reporting identical `\|z\|` everywhere gets a degenerate stratum, which is skipped -- **discipline 400 reappearing inside the gate written to enforce it** (fact 943). M55 declined to block it because a `raise` would fail its **spec rule 15**-frozen `e14`. Orchestrator's hypothesis, to be verified at source not assumed: **`e14`'s own fixture is an instance of the evasion** (all cells `z = 9.0`), so the freeze protects the evasion in its own test data. Extend-not-modify may close it without breaking the freeze. **Q3: independently re-derive P58** -- that the advertised *">= 90% of cells must pass"* clause never binds (M55 measured 0 of 2324), and extend to 4+ failures, which M55 did not. **M55 must not run this: the author never verifies their own work.** Tightening only -- M55's spec forbids relaxing anything, and forbids arguing a threshold with reference to any candidate's score. | `docs/research/M76-stratum-gate-residuals.md`, `experiments/M55-acceptance-spec/` | **reported and folded (facts 1087-1093, disciplines 525-529).** Q1 **INCONCLUSIVE** by its own registration: it declined to promote `rho = -0.8596, p = 0.0024` because the rule demanded 20 cells and the fixture yielded 18. Q2 closed **without touching the frozen primitive** (`b6_rollup` AST-identical to M55 `c37010c`, orchestrator-verified; `e14` 7/7, `e16` 13/13, `e18` 7/7 re-run). Q3 **dead**: the pooled-90% clause cannot fail, across all `2^24` placements and by derivation. **Found that B6 cannot run as specified on its own held-out set** -- the fourth ROI is outside the image on all six stacks |
| `M77` | **is the shipped gate right on real subjects, or is the estimator a selector by accident?** M73 measured `n_eff/N` = **0.0095 / 0.0147** at `DEFAULT_GATE = 4.0` on two real stacks, **singleton at 81.4% / 58.7%** of pixels, against fact 629's corpus floor of 0.0118 at the *looser* gate 2.0 (fact 1036). **The thesis is that this tool estimates where every competitor selects, and at the shipped default on a real subject it is selecting.** Two readings: the gate is too tight, or the collapse is correct because only one frame carries the pixel. **Observable, needing no ground truth:** sweep the gate and decompose the two effects that move in opposite directions -- **noise in flat ROIs** (variance side, information discarded) against **acutance in detailed ROIs** (bias side, detail protected) -- and ask whether the shipped value sits at the knee. Fact 1045's within-stack dispersion means the answer may not be a single number. **Spatial domain only: M70 owns the frequency-domain form of this question and has been told fact 1036 motivates it.** Discipline 438 binds the ROI split. **Continuation in M69/M74's agent** (`57718757`), which has the deepest `merge.rs` and `Gate` context in the project. | `docs/research/M77-gate-sweep.md` | **reported (both turns) and folded (facts 1103-1107, disciplines 540-544). VERDICT: THE GATE IS THE LEVER AND THE LEVER HAS NO SINGLE SETTING.** Fact 1036 **reproduces exactly** (`n_eff` 1.238, singleton 80.98%) and **does not generalise** -- `n_eff/N` spans **31.7x** across five stacks and singleton falls to **4.62%**, so reading (b) is false on three of them (fact 1104). Two *sibling* stacks whose spectral `n_eff` differs by **2.4%** need gates **3.31x** apart (`T*` = 38.534 / 11.642, i.e. **9.63x / 2.91x** the shipped default), which makes `DEFAULT_GATE` wrong **in kind** and sets the merge's design requirement (fact 1103). Found that **the shipped `INVARIANT 2` reads RETENTION 9.963x on ROIs its sibling invariant measures as pure noise** (fact 1105) -- an acceptance instrument inheriting the argmax defect this project exists to remove. Control **K3 failed on all five stacks**, so it registered every per-stack verdict INDETERMINATE rather than report its 3-2 split, and traced the cause to a bar transferred from a 30-frame burst (fact 1106). **Declared three of its own defects, all found by running its registered form verbatim.** |
| `M78` | **R5, blur-equalised alignment edges — the owner's fourth-ranked review item, and the last alignment repair still standing.** Its sibling **R4 is dead**: M23 killed metacalibration three ways, the decisive one being that a **zero-defocus self-pair** read `R = 0.372` where truth is 1.000 by construction, proving the shrinkage fact 45 blamed on blur asymmetry was manufactured by the harness's own **bilinear resampler** (facts 170, 172, 177). `M23-metacalibrated-edges-measured.md:478` records that **"R5 (blur-equalised edges) was not attempted"**, and open question 26 asks whether it is now the better candidate *because it plants nothing and so is immune to the mechanism that broke R4*. **Mechanism:** convolve each side of a short-baseline pair by the other side's estimated defocus increment, so both arrive at matched total blur and the asymmetry cancels by construction rather than being corrected after the fact. **The trap is pointed straight at it — a blur is a lowpass, and an unnoticed lowpass is exactly what killed R4** — so the self-pair control and an interpolator-free arm are mandatory, not optional (discipline 81). Carries **open question 25** as a separate pre-registered arm: whether sampling phase drives fact 43's span dependence, testable by shifting `coffee-bean` span-1 edges by a known integer-plus-half-pixel offset removed analytically and reading whether `1/S_48(1)` leaves **3.26**. Registered gate, inherited from M23 for comparability: **must beat 6.758 px held-out or ship nothing.** | `docs/research/M78-blur-equalised-edges.md` | **reported and folded (facts 1097-1099, disciplines 533-535). VERDICT: R5 SHIPS NOTHING**, both arms. Arm A drove `coffee-bean` conservation 3.260389 -> 1.073795 yet worsened paired held-out 7.241426 -> 7.266073 px; Arm B moved conservation to 2.493648 and held-out to 7.244330 px. **With M23's kill of R4, the short-edge repair programme is closed by two independent routes.** Its larger finding is methodological: **a conservation identity is not a proxy for accuracy** (fact 1098), which retires discipline 18's proposal to use it as the acceptance metric. **Pre-empted M23's resampler trap because the dispatch named it** (fact 1099) |
| `M78b` | **Repair the B6 held-out fixture, which SYNTHESIS fact 1087 measured as unrunnable on its own held-out set** -- M55's fourth registered ROI needs sensor row 5892 where `raw_image_visible` is `(4688, 7028)`. Commissioned to audit all four ROIs on all six stacks *before* repairing anything, to test my ARGUED fact 1088 (row/column transposition) and specifically **whether any ROI is silently valid both ways**, to repair under a rule pre-registered before decoding a held-out pixel, and to make the class impossible with a registration-time bounds check proven by a falsifying control. Barred from re-running M76's Q1: **an instrument-repairer who also reports the measurement is verifying their own work.** | `docs/research/M78b-b6-fixture-repair.md` | **reported and folded (facts 1108-1110, disciplines 545-547). VERDICT: FIXTURE REPAIRED; TRANSPOSITION CONFIRMED, AND WORSE THAN I ARGUED.** `QUAD_W`/`QUAD_H` were transposed *at fixture generation*, so all four coordinates inherited it while M55's fractional rule stayed correct -- regenerating against real geometry validates **24/24** with no judgement call. **Three of the four ROIs were silently valid both ways** (fact 1109): only one crashed, and the corpus learned of the defect solely because of it. M76's Q1 is the only exposed consumer and its INCONCLUSIVE verdict means **nothing shipped from contaminated ROIs** -- pre-registered restraint protecting the corpus from a defect not yet discovered. Control planted with Python byte-strings and **verified by read-back**, avoiding both mechanisms that defanged mine (facts 1094, 1096). **Q1's 24-cell re-run is available and unclaimed**, and must be freshly pre-registered by a milestone that is neither M76 nor M78b, naming its primary arm (fact 1090). |
| `M80` | **Repair the acceptance instrument, which carries the exact defect the project exists to remove.** M77's Addendum B (its own fact 35) measured the shipped `INVARIANT 2` reporting `RETENTION` **9.963x** and **8.819x** on flat ROIs its *sibling* invariant simultaneously measures as pure noise -- structure floor 1.0167x/0.9903x of model sigma, 97-99% of gradient variance predicted by the noise model. **Mechanism:** `corrected = sqrt(raw^2 - model^2)` subtracts the model's noise variance but **not the per-pixel argmax's max-over-N inflation**, so an acceptance statistic reports large detail retention on an ROI containing no detail -- rule 4's defect inside the instrument that certifies the merge. Commissioned to reproduce before repairing, derive the order-statistic inflation analytically **and state the residual**, repair from the mechanism rather than a fudge factor with **correct N-dependence** (corpus N = 22-299; fact 1106 is the warning), and prove it **in both directions** -- 1.0x on noise *and* detail still read on detail, since a statistic repaired into reading 1.0x everywhere would silently pass the noise test. Owns `merge_cmd.rs`; **barred from `merge.rs` and `main.rs`, which M81 holds concurrently.** | `docs/research/M80-invariant-repair.md` | live (`b0d0fb1e`) |
| `M81` | **BUILD THE ESTIMATION MERGE -- the owner's top-ranked item, and the first build to embody the thesis.** The shipped binary is still, by design, the selector defect the project exists to remove, while two verified wins sit unbuilt: **fact 84's regulariser (-35% absolute error)** and **fact 19's noise-gated mean (0.534x)**. The build was blocked because fact 1045/M65 measured the regulariser's value to depend on the gate constant; **M77 unblocked it and changed its shape** -- `DEFAULT_GATE = 4.0` is wrong **in kind**, since sibling stacks 2.4% apart in information need gates 3.31x apart and no single gate is at the knee for more than one subject (facts 1103, 1104, 1107). **Primary arm: a self-calibrating gate with no constant in it** -- estimate M70's gate-free spectral `n_eff`, solve for the gate that admits it (the composition M77 measured as `T*`), following the per-stack pattern `through_focus.rs:718-730` already mandates. **Control: the shipped constant must be beaten, measured, on all five stacks or nothing ships** -- a win on one stack is precisely the error fact 1104 caught. Must decide and record the **fold-vs-two-pass architecture** for retaining the through-focus neighbourhood, because later milestones build on it and deciding late means rewriting the merge once. Explicitly **barred** from deconvolution (ruled plugin), the depth posterior, occlusion unmixing and the robustness mask. **Warned not to accept itself with the unrepaired `INVARIANT 2`** (M80 is live on it), and reminded that in this project the author never verifies their own work. | `docs/research/M81-estimation-merge.md` | live (`3f52f279`) |
| `M79` | **Commissioned in error, redirected to something worth doing.** I dispatched an EDOF/microscopy survey on the external review's claim that the literature "was never surveyed", **without checking the corpus, where it already existed** as M19's `G-edof-deconvolution.md` (fact 1111 -- my twelfth error instance and a new variant: a third party's summary of our corpus substituted for our corpus). **Redirected to independently verify G-edof's three novelty-settling claims**, which had never been checked because the corpus verifies *builds* but not *literature verdicts* (discipline 549), and a wrongly-closed workstream leaves no failing test to reveal it. Must separate **VERIFIED-AT-PRIMARY-SOURCE** from **TAKEN-FROM-SECONDARY** paper by paper. The load-bearing question: whether Levin et al. 2009 conclude against the estimator **in general or for their configuration** -- only the former justifies the kill, and our regime (m = 1:1 to 2.8:1, effective f/33, N = 22-299) may violate their assumptions. Also asked whether M19, M20 and M70 **genuinely differ in mechanism or share a hidden premise** -- three routes resting on one premise would be a single route wearing three hats (fact 1112). | `docs/research/M79-edof-verification.md` (plus `M79-edof-microscopy-survey.md`, the duplicate my error produced) | **reported and folded (facts 1120-1122, disciplines 554-555). VERDICT: TWO OF G-EDOF'S THREE CLAIMS ARE OVERSTATED.** Claim 1 **OVERSTATED** -- the estimator identification is right but **Levin's negative is configuration-specific** (fixed total exposure, where the stack divides exposure) and **must not be counted as a fourth vote**. Claim 2 **CONFIRMED NARROWLY** -- and **G-edof missed the closest prior art entirely**, Schechner/Kiryati/Basri ICCV 1998 (DOI `10.1109/ICCV.1998.710848`), which separates *transparent* layers; **opaque sequential-stack unmixing was NOT FOUND**, so the novelty gap is real and M63 independently says there is nothing there to exploit. Claim 3 **OVERSTATED** -- plugin-first supported, permanent iteration ban not. **Answered the question the dispatch was really for:** the three routes agree by **genuinely different mechanisms** (strengthening the narrow ruling) but **share three assumptions** -- no opaque visibility change, an adequate known response, and none is the end-to-end experiment -- so the ruling is safe only when narrowed to *the core merge*. 60 individually labelled claims, primary-source separated from secondary throughout. |
| `M70` (follow-up) | **Asked whether M77's sweep qualifies its §21.6 headline.** | `docs/research/M70-through-focus-spectrum.md` §22, `ace6cc1` | **answered, not "no change", and folded (facts 1115-1118, disciplines 551-553).** **Withdrew its own §18 phrasing** -- "it is one line" was a claim about a constant, but it had measured a **window in frame index**, never a threshold; also corrected its own `s12`, where **two thirds of the window effect was content**. Then localised M77's 3.31x: the two stacks' through-focus responses **agree to 4.7% at every rung**, so **the dispersion is in the threshold's unit, not the physics** (fact 1116) -- reframing the merge's design from *abandon the constant* to **repair the unit**. Gave the local form a floor of **255 sensor px** and warned that its estimator has **no resolving power on untextured tiles**, where M77 read fact 40 (fact 1117). **Objected that its `n_eff` is a count, not a prescription** -- the identification embedded in `T*`, and in my dispatch to M81, was never measured (fact 1118). Three pre-registered guards fired in the same section. |
| `M76c` | **Rule the 74.88% unruled remainder in the flat-field noise floor** -- the largest single unexplained term in the project's crown-jewel noise model, exposed by M76b. Asked to separate scene texture from a fixed array term, told the exponent is evidence, pointed at 242 dark frames, and explicitly invited to report a null. | `docs/research/M76c-floor-remainder.md` | **reported and folded (fact 1119). VERDICT: INCONCLUSIVE, BUT BOUNDED AWAY FROM THE SENSOR.** Additional multiplicative sensor share **0.785%**, 95% CI **0-3.739%**, so the remainder is **not** predominantly a fixed array term and **must not enter `PlaneNoise::variance`** -- the null protecting the noise model from a wrong correction, which was the point of asking. **Two of its three arms were killed by its own controls** (the dark arm's registered bound was invalid; the scene-coordinate arm failed its sensitivity control), which is why the negative is credible. Fact 1064 unchanged. Its **sigma bound of 1.414%** is load-bearing elsewhere: it isolates M69's 4.06x dispersion to `FOCUS_NOISE_SD` itself rather than the photon-transfer sigma, which is what makes fact 1116's unit hypothesis coherent. |
| `M76b` | **two numeric reconciliations created by concurrency -- facts 1083 and 1086, neither closeable by the milestone that raised it.** Routed to M76 because it was uninvolved in both. | `docs/research/M76b-reconciliations.md` | **reported and folded (facts 1100-1102, disciplines 536-539).** **Fact 27's `0.2762` is CORRECT** -- M5 ran `--tile 128`, M70 the committed default of 256; both entire fingerprints reproduce, orchestrator-verified by re-running the driver each way, and all of fact 27's conclusions survive. **Fact 1086 CLOSED as *partly*:** `e_flat` is a variance in DN squared, M71's kappa explains **25.12%** aggregate (16.78-55.82% per cell), **74.88% unruled**, fact 1064 unchanged. **Refuted an inference of the orchestrator's** (fact 1101): the control it reasoned from is invariant to tile size |

**M63 is reserved** for the bimodality milestone above and must not be reissued.

**Unallocated, and deliberately so.** Three measurements are named and waiting for a
milestone that did not frame them (discipline 441):

- ~~The green-plane correlation of fact 895~~ -- **dispatched as M72.**
- ~~The B-plane mechanism's ISO sweep~~ -- **dispatched as M68.** Until it reports,
  `profile.rs` must carry the 0.84x as a **measured per-plane scale of unknown origin**,
  not a conversion gain: the two behave differently when ISO changes.
- **M55's stratum-noise question** (LOW, UNMEASURED). Must not go to M55.
- **The green-plane correlation's 3.6% sigma consequence** (fact 958), design-only,
  needs a fresh decode.

**Blocked on M62's certification, not forgotten:** `crates/strehl-core/src/merge.rs:278`
carries a **new** unresolved intra-doc link to a `#[cfg(test)]` item, taking `cargo doc`
from 3 pre-existing warnings to 4 (orchestrator-verified). It is a one-line fix and it is
**not being made while M62 is certifying that exact file** -- editing an artefact under
certification is the shared-tree hazard rule 42 exists for.

## Layout

| Path | What |
| --- | --- |
| `crates/strehl-core/` | Types, noise model, tile views, geometry |
| `crates/strehl-raw/` | RAW decode behind `rawler` |
| `crates/strehl-cli/` | The binary |
| `docs/captures-needed.md` | **Data owed by the owner.** Read before asking for captures. |
| `docs/research/` | Research corpus and decision record |

## Research corpus

| File | What | Agent |
| --- | --- | --- |
| `SYNTHESIS.md` | **Start here.** Decision record, revised after review. |
| `M39-verify-detail-metric.md` | **INDEPENDENT.** First outside verification since M2. Found M38's detail metric credits a *flat ROI* with +35% detail, inverted M38's error budget, and showed fact 19's 1.253x does not reproduce on the shipped operator (1.068x) |
| `M64-estimator-default.md` | **The shipped default is now an estimator.** `strehl stack <dir> --out x.tif` with no flags exits 0 and writes an image; `DEFAULT_GATE = 4.0`; the argmax selector survives as `ArgmaxBaseline`. Widened M62's degeneracy guard to all seven stacks, 7/7 pass, worst `coffee-bean` 0.30109 -- **not the nominated baseline stack.** Refuted the adaptive `--target-n-eff` rule on M52's own numbers. **Shipped its pre-registered 4.0 although gate 8 scored better.** Facts 947-954, disciplines 449-451 |
| `M65-election-gate-measured.md` | **Answers the question M60c framed and declined to decide.** Regularising the *election* is **not load-bearing at the shipped gate** (<=1.2335x vs a 1.332 bar) but is at gate 0.5. Measures M60c's category error directly: **56.70% of pixels change winner while the acceptance set moves 0.44%.** Voided its own headline on an unmet pre-registered criterion. Facts 961-966, disciplines 456-458 |
| `M63-bimodality.md` | **This is the M60 collision, renamed** -- the stem is the collision rule 41 was written for. **The project's cleanest kill.** Through-focus bimodality at occluding edges is real and abundant (78.3%, AUC 1.000) and is a **single-depth defocus side-lobe**, not two depths -- refuted five ways, including firing identically on silhouettes against blank card and failing to reproduce across two captures of the same scene. Kills the external review's second-ranked proposal. Facts 967-970, disciplines 459-461 |
| `M62-ruling-M64.md` | **CERTIFY.** The shipped default is an estimator: `DEFAULT` scores 5.431624 vs sqrt(30), efficiency **1.000076**, so the whole 0.83% shortfall is the gate declining 0.461 frames/px -- admission, not arithmetic. **Rules that shipping gate 4.0 is correct BECAUSE its own objective saturates at 8** -- tuning to the instrument's argmax would admit everything. States what CERTIFY does *not* cover: calibration, the gate value, and **focus-correctness, "a real open hole."** Refused to measure the shared `target/` binary as unattributable. Facts 971-977, disciplines 462-464 |
| `M66-gate-n-dependence.md` | **The gate IS N-dependent, proved not measured.** The expected max of N noisy responses is strictly increasing in N and `Gate::tolerance()` has no N term -- 18% headroom erosion over N in [19,299]. **M62's sqrt-N headline survives unqualified** (gate 8 is N-insensitive to 1e-5); the shipped gate 4 does not. Four criteria NOT MET, **one with a premise it declared false**. M64's 22.15x spread is ~72% frame count. **Post hoc and unruled: `FOCUS_NOISE_SD` runs 19-21% low on real texture** -- larger than its charter. Facts 979-985, disciplines 465-467 |
| `M69-focus-noise-sd.md` | **`FOCUS_NOISE_SD` is a zero-signal constant standing in for a texture-dependent quantity.** Its VALUE is right -- 0.9285x-1.1009x across twelve stacks, median 1.0147x -- and M69 recommends **not changing it**. Its FORM is refuted: **4.06x span** on a controlled plant, driven by gradient-*direction* coherence across the 27x27 window rather than SNR; a per-pixel form moves `n_eff` by **1.09x-1.72x**, twenty to fifty times what any rescale can do. **M66's 19-21% reproduces digit-for-digit on M66's plant and does not generalise** (three further latents: 0.8380, 1.0274, 1.0246 -- sign inconsistent); about a quarter to a half is a frozen-latent artefact, forecast to 0.7% by a control that could have failed. **The certified 5.431624 survives at worst -0.788%, asymmetrically** (saturation makes `rho>1` cheap and `rho=0.838` fatal). Reported `FINE_FOCUS_NOISE_SD = 0.090_400` as undiscussed **in the part of the corpus it searched**; **the orchestrator dropped that hedge and the resulting fact 1021 was false** -- the constant has six facts about it (437, 500, 501, 520, 580, 753) and M45 reproduces it to -0.000%. Corrected at source; what remains open is only whether its **form** carries the same texture dependence. **The quantity is NOT MEASURABLE from a focus sweep at all** -- §12's burst is now a blocking dependency, and §12b is new. |
| `M72-green-plane-correlation.md` | **rho(G1,G2) is real, is not a green-pair property, and does not belong in the model.** Replicates at **+0.08261** against fact 895's **+0.0730** by an estimator with different failure modes. **But every plane correlates with its own neighbours at +0.05 to +0.16 and the greens sit INSIDE that range** -- margin over within-green neighbours **+0.00043** against a pre-registered **+0.010**, and **-0.00074 at ISO 1600**. **Its own pre-registered control `C2` returned GREEN-SPECIFIC and M72 ruled it MISLEADING AS STATED**, caught by `F4`, written to break its own headline and committed before running. Materially: over-confident everywhere, never flips sign, **peaks 4.04% against a 4.75% threshold (a 15% margin it asks be called CLOSE)**, confined within ~10 DN of black. Mechanism localised **downstream, in the read chain**; `F3` excludes diffusion and optical crosstalk independently. **Recommendation: fix `noise.rs:122`'s independence assertion, not `green_luma_sigma`.** Incidentally answered M68's open question -- `alpha_B/alpha_green = 0.8418`, `delta_B/delta_green = 0.5966` against a single pre-ADC scale's 0.7049 and 1.0 -- **routed to M71, not adjudicated.** |
| `M73-cylinder-invariant.md` | **The first result to transfer from a simulated plant to a real capture with its magnitude intact.** M67's 12% election tightening reproduces at **12.3-15.1%** on two stacks under two references with opposite bias, all four inside a band registered before any result existed. **But the shipped gate admits `n_eff/N` = 0.0095 / 0.0147 on this subject -- at or below the corpus floor -- so the merge behaves as a SELECTOR and the admission verdict is INCONCLUSIVE for a measured reason.** **M67's framing does not transfer**: gate lift **+7.04 / +12.09 pp** against the plant's **+60.26**, because the real election is right 76.92% / 70.45% against the plant's 39.70%. At matched `n_eff/N`, hit rate **99.499% / 99.583%** against shape-matched nulls of 9.57% / 36.93%. **The ink-shaped defect is absent and BOUNDED** (>0.967 / 3.029 frames excluded at 3 sd). **Disqualified its own pre-registered `H_ax` rule** -- integer interval against continuous fit -- with a proof independent of direction, in the direction that cost it a headline. **Corrected M67's invariant: it needs a CYLINDER, not a surface of revolution.** M67's blind spot is **unclosable** here -- no silhouette in frame, now a capture requirement. |
| `M62-ruling-M64.md` (2nd ruling, `e4c1f98`) | **CERTIFY-CONDITIONAL.** Withdrew the unconditional form of its own headline after **independently reproducing M66's post-hoc 19-21% sigma_F effect on its own plant** (rho 1.2124). **"My guard has the same shape of error as the thing it polices"** -- a fixed 0.95 line against a null that drifts with N. **Caught my fold conflating an N=19 prefix with an at-own-N result.** **Retired its own scoping caution** when the evidence inverted it. Priced sigma by algebra: tolerance is linear in `FOCUS_NOISE_SD`, so a sigma rescale IS a gate rescale and its sweep is already the sensitivity curve; power arm exactly invariant. Facts 986-991, disciplines 468-471 |
| `M68-b-plane-mechanism.md` | **NEITHER candidate. `alpha_B/alpha_G2` = 0.85235 +/- 0.00316** against predictions of 1.000 and 0.705 -- **46 and 47 sigma out, 0 of 32 row bands in either**. The 0.84x acts **partway along the analog chain**; **retires the digital-scale possibility M61 left open.** **Caught M61 with the sign of its own separating observable inverted**, in committed code, before measuring. **Then withdrew its own headline recommendation when asked to confirm it** -- "worse than none" generalised a `rho`=1 result; the partial fix is actually *smaller* in error at almost every read-noise share. **What survives is a COUPLING requirement**: `gain_dn_per_e` and `read_noise_e` move together or neither, because gain-only flips conservative to over-confident exactly where the gate adjudicates. **Also volunteered that the gain factor in its own fix is M61's and unverified.** Facts 992-999, disciplines 472-478 |
| `M67-focus-correctness.md` | **The merge admits the truly-best frame at 99.955% +/- 0.023%** of interior pixels (simulated, truth known from geometry); size-and-shape-matched null 32.36%. **Load-bearing: the argmax names the correct index only 39.70% of the time and the gate catches it anyway -- focus correctness lives in the GATE, not the election**, which explains fact 961. Price `D(A)/D(E)` = 0.4895. **Registered the direction of its own bias pre-run: every accuracy number is an upper bound.** C1 failed on 3 of 10 cells and the consequence was honoured -- **exactly the cells M62's guard G fails.** **Ruled per-pixel correctness NOT MEASURABLE on the corpus** and refuted a vacuous test from its own brief. Facts 1000-1005, disciplines 479-482 |
| `OWNER-QUESTIONS.md` | **Read this before asking Chris anything.** Decisions I could not make alone, captures still outstanding, and two numbers that must NOT reach a user-facing recommendation yet. Append; do not rewrite. |
| `M20-VERIFICATION.md` | **INDEPENDENT.** M20's optics gate is a **tautology**; the 15.1% headline is one capture out of a **3.5%–65.8%** corpus range; refutes fact 88's mechanism; flags the f/5.6 advice as a two-stop extrapolation with no aberration term |
| `M31-VERIFICATION.md` | **INDEPENDENT.** 15 defects across M27–M30. Refutes fact 242 as a raw-argmax artefact (rule 4). Every published number reproduced exactly — **every defect was a choice of estimator, reference, arm or null, not an arithmetic error** |
| `M36-VERIFICATION.md` | **INDEPENDENT.** M32's focus measure was `sobel` on a *cube*, silently smoothing the frame axis: headline 142–991σ is really **84–512σ**. M33's direction is inverted (48.7% HIT) and its "replication" is complementary by construction. Fact 281's mechanism refuted — the real channel is **acceptance-set size** |
| `REVIEW.md` | Adversarial review that corrected four design errors |
| `REVIEW-plugin.md` | **Plugin-architecture critique.** Cordis verified against the PDF; four blocking interface fixes; camera/lens plugins are profiles |
| `M2-rss-resolved.md` | **Tiebreak.** Two docs disagreed 2.2x on peak RSS; resolved by measurement. Peak tracks live concurrency, and the 8 GB ratchet is at 89% by N=105 |
| `M1-decode-measured.md` | Measured decode throughput and sensor constants |
| `M2-baseline-skeleton.md` | The naive argmax baseline, and the measured defect it exposes |
| `M2-verification.md` | **Independent re-derivation of M2.** Headline confirmed and causally proven; five supporting numbers refuted |
| `M3-alignment-measured.md` | Measured alignment cost, motion model, and why chaining is dead |
| `M4-fpn-measured.md` | Dark-frame noise: sigma-vs-N, the fixed-pattern floor, read noise vs ISO |
| `M5-diffraction-measured.md` | **The bellows factor, measured from the raw CFA.** `B = (1+m/p) ∈ [2.41, 3.06]`, `p ≈ 1.0-1.4`; `p=0.5` refuted model-free. EXIF `FNumber` is **not** bellows-corrected — marked f/11 is optically f/33 |
| `M6-residual-halo-measured.md` | **Why alignment stops at 0.6-1.3 px, and how big the halo is.** The residual is **blur-induced correlation bias**, not depth-dependent magnification: in-focus tiles align at **0.144-0.172 px** (at the 0.19 px estimator floor) while far-from-focus tiles in the same pairs sit at 0.25-0.69 px, surviving within-pair (p=0.010) and within-tile. But the bias is **symmetric degradation, not directed displacement** (S6 null on all three stacks) — so **the lens plugin stays a data file** and the fix is in the aligner (weight tiles by `\|c − w\|`). Halo is **stack-dependent** (19.4 / 32.4 / 89.2 px), which is what kills a scalar `halo()`; §3.4.1 B1's "39 px" was a *displacement*, not a halo. Closes questions 6 and 10, closes §3.4.2, opens risk 11 |
| `M7-gpu-focus-measured.md` | **The fusion prize, priced.** Ring-difference focus + merge on the GPU is **4.117 ms / 22 frames**, bandwidth-bound at 84% of measured DRAM read. Fusing focus into the merge saves **1.45 ms = 0.14% of the pipeline** — *not* enough to justify constraining plugins to spliceable WGSL. Answers risk 10 / question 11; fact 21 is CPU-time-under-concurrency and cannot bound a GPU design |
| `M8-scratch-measured.md` | **Decoder scratch, and the term that was actually missing.** Scratch is **39.36 ± 0.11 MiB per concurrent decode**, file-size proportional. But **most of the planner's error was never scratch** — peak resolves into `14.4 MiB floor + live x 342.8 MiB + ⌈log₂ chunks⌉ x 110.04 MiB`, that last term being one `Selection` per level of rayon's reduce tree (= `px x 14`, 550 MiB at 18 chunks). Recommends the worker cap 20 → 16. **Also refutes SYNTHESIS §3.2.1 assertions 1 and 2 at assertion 1's own specified pair**, and finds the "379 vs 321 MB" per-worker gap was a MiB/MB unit mismatch |
| `M9-support-coupling-measured.md` | **What the merge is actually coupled to, and why nothing goes on the interface for it.** Argmax's noise excess tracks the focus operator's **centre-tap sensitivity fraction φ** (ρ = **+0.918 / +0.894**, p < 0.0001), **not** its support radius (ρ = −0.170 / −0.243, n.s.); a zero-centre-tap Sobel shows **no excess at all (0.9952x)**. For a ring difference **φ = 1/(2·(2·inner+1)²) and the outer radius cancels exactly**, so the proposed `support_px()` would have reported the one term that provably does not matter. **Rejects §3.4.1 B3** — the last Blocking verdict standing on an unmeasured claim — and reinterprets (does not retract) fact 25. Also: the flat-ROI noise objective is **monotone-then-flat with no interior optimum**, and regularising can *harm* |
| `M10-deep-alignment-measured.md` | **Deep-stack alignment: why chaining really fails, and what works instead.** Chaining does not fail from accumulated random error — **short-baseline edges under-report magnification change by ~3.2-3.5x**, coherently, so 36.4 of the chain's 40.3 px corner error is scale alone. Proved by a telescoping conservation identity (span-1 −1.6876% vs span-16 −5.8891%), then isolated: the bias needs a **real inter-frame content change** and lives **below ~0.5 px** of differential displacement (resampler-free control recovers a planted increment at 1.00; a real defocus pair at 0.56). A global least-squares solve over a sparse multiscale graph of direct edges places **105/105 frames at 6.76 plane px** against a fixed reference's **76/105**. Error is bounded by the *edges*, not the solver. Also: the scale centre is per-stack, not per-rig. **Risk 11 → partially solved; rule 6 rewritten**; facts 43-48 |
| `M12-shrinkage-measured.md` | **Can the short-baseline shrinkage be calibrated away? No.** Fitted on one stack it transfers to **0 of 18** cross-scene pairs and makes the worst case **83.4x worse**; even an oracle in-sample correction leaves a chain at twice the error the plain global solve already achieves. The magnitude is a property of the **scene**, ranging 1.03x-3.26x across five stacks — two stacks matched to 0.3% in displacement differ **3.11x** — so fact 43's "3.2-3.5x" is rescoped to `coffee-bean` alone. Also **corrects fact 49**: `112`/`113` share a per-frame focus step rather than sampling one interval at two densities, measured both by magnification and from the focus band in the pixels. Introduces a **focus index** measurable without metadata, since `FocusPosition2` has only 3 distinct values across a 79-frame sweep. **Rule 6 amended; risk 11's shrinkage question closed**; facts 50-54 |
| `M11-focus-bakeoff-measured.md` | **What to select with, and what selection costs.** A 47-operator pre-registered bake-off on two real stacks, scored on a measured Pareto front of selectivity against noise excess. **The shipped `ring(1,3)` ranks 26-27th of 36** (N = 1.3475x, ~45% of the best selectivity); the recommendation is **Tenengrad under an 11x11 box window** (N = 1.1324x) — re-tuning the ring cannot close the gap. Headline: **no operator anywhere on the front is noise-free** (0 of 36 reach N ≤ 1.02x), so operator choice alone cannot rescue a selector. Zero-centre-tap operators *are* noise-free (φ = 0.0000, Ncorr 0.989-0.997) but recover only 34-40% of a planted focus surface. **Windowing and normalisation each re-introduce a centre tap, additively** — so φ must be probed on the whole configured stage, not the kernel. Closes risk 2; facts 37-42 |
| `M13-window-depth-measured.md` | **Where the focus window sits, and why a depth discontinuity is what puts it there.** M11's 11x11 is **dominated** — `tenengrad-w8` beats it in **36 of 36** occluding-edge cells at lower noise and identical cost — and the measured argmin is **`tenengrad-w13`, a 27x27 box**, stable in all three noise seeds. The central finding: **remove the depth step and the objective stops turning over**, running to the sweep endpoint; put it back and an interior optimum appears. So M11's "still improving at 23x23" carried *no* information — a fronto-parallel plant **cannot** turn over. **M11's per-pixel metric is structurally blind to the damage in 30 of 30 cells** (18.48 DN mean penalty), which is why it chose a window less than half the right size. Cost is **flat in the radius** (2.53% spread over w1-w40) because the box is a running sum, so the widening is free. Adaptivity has real oracle headroom (5.7-46.8%) that **no realisable rule reached**. Also corrects **M11 A1's φ monotonicity** (φ peaks at w15-w17 then declines) and proves `D:\personal\macro\119MSDCF` is a **byte-identical mirror**. **Closes question 15; facts 60-69** |
| `M14-tenengrad-implemented.md` | **Shipping the operator M11 and M13 chose, and what shipping it exposed.** Replaces the ring difference in `strehl-core` with Sobel magnitude under a 27x27 running-sum box. Two results the research milestones could not produce. **(a) The benchmarked operator is the gradient MAGNITUDE, not the squared "energy"** its name implies (`squared: false`) — shipping the textbook form would have inherited M11's and M13's evidence under a name that did not earn it. **(b) The shipped CLI reproduces M13's separately-written harness to every printed digit** (1.068x, 30.114 DN, 6 winners), which is the cross-implementation check that separates "the operator is right" from "one harness is self-consistent". Index speckle falls **34.381% → 1.010%**. Also refuses M13 §6.4's φ bracket, correctly: **φ spans 47x over a 64x texture-amplitude range**, so the bracket pins an ROI. **Verification found a blind spot M14 under-reported as a note about a test: the shipped operator has EXACTLY ZERO focus discrimination on an untextured monotone edge** (fact 73) — which is why confidence must come from cross-frame spread, never magnitude. **Facts 70-73; opens question 19** |
| `M15-regulariser-window-measured.md` | **Does the window optimum survive the merge regulariser? Yes — and the orchestrator's hypothesis was refuted.** The argmin is **w13-w14, always `interior`, at every regulariser width 1-33**; shipping w13 costs **0.050 DN** at width 17 against a pre-registered 0.87 DN threshold. **Closes question 17 and discharges M13's last recommendation-moving caveat.** The mechanism is real but lands off-target: the regulariser substitutes for the window at **1.72 : 1 (r² 0.94)** on cells with no depth step and at **≈ 0 (r² 0.10)** on the cells that decide the window — a wide window buys contrast *localisation* at an occluding boundary, which a post-hoc smooth cannot supply. Three results beyond the question: the flat aggregate is a **cancellation** (`horizontal` 10/10 narrower, `vertical` and `bar` wider) and doubles as the positive control; the regulariser is worth **−35% absolute error**, the largest unbuilt win in the project; and width 3 is **worse than no regulariser at all**, reproducing fact 36 unregistered. Gate A reproduced M13's committed CSVs **byte for byte** on both stacks. Two self-corrections, both disclosed rather than dropped. **Facts 80-88; opens question 20** |
| `M16-orientation-fpn-measured.md` | **The orientation anomaly is the scene, not the machinery — and `WINDOW_RADIUS = 13` survives.** Fact 83's asymmetry transposes exactly when the *plant's textures* are rotated 90° with every piece of code held fixed (median shift difference **0.0** windows vs **8.0**), and symmetrising the texture nulls it to **+0.0**. Mechanism: horizontal edges are localised by `Gy`, vertical by `Gx`, and this corpus carries **14-22× more vertical gradient energy**. The review's proposed row/column-destripe fix moves the statistic by **0.0 windows** and is *worse* on the level statistic; the row-FPN mechanism it assumed is refuted at source — this sensor's fixed pattern is **isotropic at all 11 measured ISOs** (0.968-0.999), and the row-correlated component is **~10³ smaller** than the scene's own row structure. **Read §11 before trusting any `dmae_far`/`bleed_*`/`mis_*` number for a horizontal edge** (fact 506: `edge.rs` derives its baseline band from `roi.width` regardless of axis, emptying the far band on non-square ROIs; `E_excess` is unaffected, which is why it was the primary statistic). Facts **90-99, 506-508**; disciplines **40-44**; closes question 20. Its §13 was renumbered on fold — see the reconciliation note there. | M16 |
| `M17-dual-response-measured.md` | **Question 19 (fact 73's monotone-edge blind spot), settled — and the dual loses.** The box `max` fixes the blind spot and costs *no* noise, but costs **+18.91 DN** on M13's occluding-edge cells, **21.7x** the pre-registered bar. Candidate (c) `tenengrad-sq-w13` clears every gate and is **0.96x** the shipped cost. Answers question 100. |
| `M20-deconvolution-ceiling-measured.md` | **Does the external review's multi-frame Wiener reframe beat selection here? Measured: no — and the reason is the aperture, not the algorithm.** The estimator `L̂ = Σ H* Y / (Σ\|H\|² + σ²/S)` **is** MMSE, confirmed by three independent routes agreeing to 6 decimals, so the algebra is right. But **unguarded it LOSES to plain argmax by up to 31% RMSE even given oracle depth and an oracle prior** — the fallback guard is load-bearing, not optional — and on real data **only 15.1% of pixels** sit past the crossover, because for the *median* pixel local noise exceeds local signal structure **in its own best frame**. Hard ceiling: where every frame's OTF is zero the estimator returns exactly zero, and at marked f/8 and f/11 MTF@Nyquist **is** zero. The prize turns out to be a capture change: **blur-per-step in pixels is aperture-invariant**, so marked f/11 → f/5.6 buys **9.6×** contrast at 4-px detail for 2× the frames and no extra light. Four self-corrections, including a broken MMSE control and a guard that was algebraically identical to the thing it was guarding. **Facts 140-145; verification in flight; the optics gate may be circular — see §2** |
| `M21-occlusion-bimodality-measured.md` | **Is the through-focus curve really bimodal at occluding edges? Yes, and 85% of my first number was a tautology.** Multi-peaked curves are enriched **4.38×** at depth steps on `coffee-bean` against a scene-matched **frame-permutation placebo reading 1.01×**, stable across subsample offsets, surviving stratification in *every* intensity-gradient quintile (pooled ~2.7×, up to **14.3×** in the most textured), and intensity-edge binning alone gives **0.00×** — so it is not an edge artifact. **But it is undetectable on `109`/`119`, where the permutation null shows noise alone flags 60–98% of pixels**, so the detector only works gated on calibrated σ — the same conclusion M20 reached by a different route. Two reusable failure modes kept in the record: the shipped R=13 window **destroys the signal it looks for** (54 sensor px vs a much narrower veiled zone), and binning against an argmax field from the same volume is **circular**, since a bimodal pixel manufactures its own depth step. **Facts 150-152; binds the M18 fold seam** |
| `M22-hot-pixels-measured.md` | **How bad is this sensor? Cleaner than the review assumed.** The 242 darks arrive as 11 ISO groups, which is a free replication test: **recurrence, not a σ threshold, is the discriminator** — 3,947 pixels recur in ≥6 groups against 2e-08 expected by chance, while 108,776 single-group flags are *fewer* than chance and are simply the threshold's false positives. This deleted a tuning knob instead of tuning it. **But the defect barely matters:** in real 1.3 s frames the excess is **+3.0 DN mean, 0.0 median**, flat across three signal decades (a fixed additive offset), worth **0.39σ → 0.13σ** from shadow to upper midtone; only 3 pixels sensor-wide are both always-hot and >100 DN. **The delivered darks are also at the wrong exposure** — all 1/100 s against real stacks of 1/60 s–2.5 s — and a cross-scene test with a **shift control** finds ~839 scene-independent defects of which the dark map contains 5. My first cross-scene test used an independence baseline and reported >1M "defects" because both subjects sit centre-frame; the known-real dark map is the positive control. **Facts 160-162; adds `captures-needed.md` §6** |
| `M23-metacalibrated-edges-measured.md` | **R4 (per-edge metacalibration), and it ships NOTHING.** Dead three ways: the local-linearity premise is refuted (`R` swings 0.53 to 0.99 across delta), the response measures the plant's own **bilinear resampler** not defocus (a zero-defocus self-pair reads 0.372), and held-out is **6.758 px unchanged**. Withdraws fact 45's causal reading. |
| `M24-photometric-drift-measured.md` | **Does R9's premise hold — is there per-frame photometric drift to model? Yes, and the fix is sharper than the review asked for.** Peak-to-peak mean level varies **2.88% / 6.84% / 8.93% / 11.70%** across four stacks — and **`109MSDCF`, the stack most of this project's measurements were made on, is the quietest at 0.91%**, so a clean result there says nothing about photometric handling. The framing confound (breathing changes magnification, which moves the mean without any exposure change) is discharged both ways: `coffee-bean` genuinely changes exposure mid-capture (`4/5 s` → `5/8 s`), and a central 600 px ROI moves *at least as much* as the full frame on all three stacks tested, correlating +0.85 to +0.97 — the opposite of the framing prediction. **The useful part is that the simple explanation fails:** the measured level ratio across `coffee-bean`'s two exposure groups is **1.0443 against an EXIF-predicted 1.2800**, i.e. 16% of prediction, most likely auto-exposure compensating a drifting light. So **the per-frame gain must be FITTED, never read from metadata** — EXIF is blind to 7–9% on two stacks and overcorrects ~6× on a third. A probe, not a full milestone: no gain was fitted and no merge output was measured. **Facts 180-182** |
| `M25-simulator-measured.md` | **The calibrated simulator reproduces the project's noise-and-selection machinery and does NOT reproduce its optics or its subjects.** Gate 1a **PASS 16/16** — fact 35's phi-excess mechanism emerges from calibrated constants alone, with a zero-centre-tap placebo reading exactly zero. Gate 1b **PARTIAL 3/5**: no single defocus rate matches both fact 19's argmax ratio and its plain-mean ratio. Gate 1c **FAIL** — transplanted to a two-layer plant with known ground truth, M21's byte-identical occlusion detector reports enrichment **1.03x against a real 4.38x**, flat across a 12x defocus sweep, while its permutation placebo stays honest. **This is a verdict on the PLANT, not on the detector — do not repeat the original fold's error.** Gate 1c failed its own base-rate check (2.1x over-production) and, truth-gated, the plant's veiled pixels are multi-peaked **less** than its smooth ones (0.23x, wrong sign), so no detector could find the effect. Attributing it to the detector assumes fidelity on the axis the plant failed (discipline 297). The supported detector claim is fact 567: **1.8-3.4% precision, ~11% recall, over-flagging 3.5-5.7x against truth**. Fact 150 is untested by this milestone. **Gate 2 is the one that matters: the negative control fires on gain, on correlated noise and on no noise, and is BLIND to deleting the diffraction PSF entirely** — a change that moves green-plane power at 0.455 cyc/px by **123x**. That single result disqualifies the twin from scoring deconvolution, which is the job the external review assigned it. **It also found the worst defect in the shipped code: `g = ISO/436.8` is wrong by 2x at ISO 50**, because Sony ISO 50 is an extended pull that reads out at base-ISO gain — measured on two independent routes (M4's darks and this milestone's photon transfer). Fixed at `2a4f5c5`; it moves 23.68% of subpixels on a real stack (fact 553). **Read §5.9 before folding anything**: it is the corpus's clearest case of two errors of opposite sign cancelling into a false agreement, and of a test carve-out silencing the assertion that would have caught the bug (now rules 30-31). Seven of its own errors are documented in §5. Facts 540-554, disciplines 268-275 and 287-290, questions 111-116 and 126-127. **Fold from `4f51d0c` or later; the untracked first draft's numbers are stale.** | M25 |
| `M41-r3-kill-measured.md` | **R3 — "make the merge itself a multi-frame Wiener deconvolution" — STANDS REFUTED, and the second pass had to withdraw one of the two metrics that scored it.** Guarded focus-axis RIF costs **3.47× / 3.91×** the shipped merge's flat-ROI high-pass noise against a pre-registered 1.10× bar, so the two REFUTED clauses are **exhaustive over the detail axis** — refuted at every `f_D/f_A` from 0.50 to 5.00 (fact 479). It puts **63.97% / 81.25%** of detail pixels outside the range of every input frame, against 0.000% for the shipped merge; Forster 2004 called ~30% a defect. The scorer is not a tautology: arm C returns SPLIT REOPEN/REFUTED, and the clauses are disjoint over an 800 000-point grid. **The positive control passes** — on a plant where the OTF is exactly the one being inverted, arm D wins by **+11.17 dB** — so the optics refuse it, not the algebra (fact 464), and ~8 of those ~10 dB are the diffraction term rather than the focus axis R3 proposed. **The withdrawal:** the FRC 1/7 crossing of `0.4961` reported by every arm, both nulls and both circularity variants, is `ff[-1]` — the last ring centre returned when the curve never crosses. A right-censored bound published as a measurement, then used as **both** sides of a ratio (facts 475-476). 32 repair settings, none admissible. **It also corrects fact 417 and fact 49**, and the honest closing note is that the verdict survived by margin rather than design: at 1.2× instead of 3.5×, half the condition would have rested on a metric with no power. Facts 460-479, disciplines 276-283, questions 117-122. | M41 + M44 (second pass) |
| `M26-colour-clipping-measured.md` | **The measurable half of R13 (colour), and it caught a hole in a decision already taken.** Two results. (1) **Do not white-balance before the noise gate.** As-shot WB is a per-channel gain of **2.13–2.86× on red**, varying per stack because the body was on auto WB; the calibrated model is valid only in native raw DN, so gating after WB understates σ by a factor tending to **m** in the shadows and **√m** in the highlights — believing red up to **2.86× quieter than it is**, hardest exactly where M2 measured the argmax defect. Nothing errors; the gate just reverts toward the selector. (2) **Clipping defeats discipline 29.** Cross-frame peak contrast — chosen over focus magnitude *precisely because* magnitude fails on fact 73 — reads **1.0000, its maximum**, on pixels pinned in every frame that carry zero information, since **85.9%** of them have `f_min` exactly 0 (clipped-blob interior) against **0.0000%** of never-clipped, while `f_max` is **52× typical** (the blob's edge crosses in another frame). Magnitude fails there too, so the input must be masked rather than the metric swapped — one comparison per sample. Saturation is per-stack: **four of six stacks have none at all**, `coffee-bean` has 1.26%. The author's own headline prediction (partial clipping) was **mostly refuted** — 1.67× collapsed to **1.06–1.09×** under brightness matching. Checked-and-clean: the 16383-vs-15360 white-level split is already handled and tested in `noise.rs`. **Facts 200-203, discipline 110-111; qualifies discipline 29** |
| `M27-coverage-gap-measured.md` | **Can the pipeline tell, from the stack alone, that the bracket did not cover the subject? Yes — and the answer changed a headline design decision.** Ground truth by construction: remove frames from a real bracket and the pixels whose best frame was among them have provably lost coverage. A **hole** is detectable from **one** missing frame — peak-curvature excess **+0.45 to +1.39** over a null stable at **1.40–1.43**, vertex-offset excess −0.10 to −0.48 — using only the reduced stack. **Uniform** under-coverage, where no internal control exists at all, does **not** need the optical model as predicted: frames within 50% of peak height is **absolute** and falls **3 → 2 → 1** under decimation, with the min-estimation confound closed by holding the threshold at the full-stack minimum (identical column). Deployable recipe: pixels resolved by ≤1 sample = **0.01%** at 53 frames, **37.46%** at 27, **75.76%** at 9 — so `coffee-bean`'s 105-frame bracket is **~2–4× denser than needed** at f/8, which (DERIVED, contingent on M20's circularity check) roughly pays for the aperture change M20 wants. **The headline is the direction:** a gap makes the curve look **sharper and better centred**, refuting the author's prediction, and joining fact 73 and fact 203 as a *third* mode reading maximum confidence at zero information — which promotes discipline 120 and **disqualifies every self-normalised shape statistic as confidence**. Two further author errors recorded: the first detector was an oracle, the first control drifted. **Facts 210-213, discipline 120-121; supersedes discipline 29 in scope** |
| `M28-robustness-mask-measured.md` | **R10's robustness mask, and the premise needed correcting before the mask could be built.** Wronski's shape — noise-normalised disagreement against a running estimate — is right for a **burst**, where frames are nominally identical. **A focus stack is the opposite case: the frames are supposed to disagree.** Measured fix, one line: **reference the immediate neighbours, not the stack.** On the *clean* stack the pairwise residual grows **1.13 → 12.30** as separation goes 1 → 16 (near-linear = accumulating breathing; noise would be flat, defocus would saturate), and the radial profile is **1.82× centre-to-corner with a whole-stack reference against 0.98× with an adjacent one**. The architectural consequence inverts the prediction: **the mask can run BEFORE alignment**, so alignment can be protected by it. Sensitivity, plant-measured with a shift-zero placebo that fires **0.0%** at FPR ≤ 1%: a **4-green-pixel (≈20 µm at the subject) shift is caught 53.8%** at FPR 1% and 89% at FPR 5%. **Tile scale is not a sensitivity knob** — detection is flat within 10% across a 4× range, because the baseline tail is deterministic so signal and threshold average down together; pick the scale on compute cost. Transfers: a clean-calibrated threshold flags **1.01% / 8.33% / 17.88%** on clean / bubbles-move / scene-evolves, ordering pre-registered. Two incidental results: the **M4 noise model predicts the clean tile residual to 9.9%** with no free parameters, an independent validation at a scale it was never fitted to; and **M24 needed a *how*** — the author's own median-over-subject-crop gain read 4.28% where M24 measured 0.91%, because that median absorbs focus signal, so **fit gain as the mean over all pixels**. Four author predictions refuted, incl. a gradient normalisation that was an artefact of its own divisor. **Facts 220-225, discipline 130-131, question 45** |
| `M29-static-defects-measured.md` | **R11's other half — dust — and the free lunch the review argued for does not exist.** The claim was that an estimator averaging `n_eff` frames dilutes a sensor-fixed shadow while a selector copies it whole. Priced from measured warp geometry rather than by detecting any dust: **`D = 0.999` at `n_eff = 3`.** The mechanism is general and worth carrying — **suppression is bought by the *span* of frames averaged, not their count, and a focus merge averages ADJACENT frames precisely because they agree** (M27: `n_eff ≈ 3`; M28: disagreement grows near-linearly with separation). Adjacent-frame warp is **sub-pixel, 0.07–0.22 green px**, which independently corroborates fact 221. **Dust must therefore be handled explicitly.** It also cannot be measured from subject stacks: limit **32–50% shadow** against real dust of 1–15%, no excess over the shift null, and the floor is **scene texture — rms exponent +0.025 over a 16× frame sweep**, so more frames buy nothing. Flats reach a **0.120%** floor at n=20, **158× better**, which turns `captures-needed.md` §4 into a specification. The mechanism behind all of it: a self-ratio static map responds to depth × **local scene brightness**, `R ≈ 0.92·(g/blur(g))` — which is *why* a flat is the right instrument. **Five author errors, disclosed:** a global correlation provably an order of magnitude below its own null before it was run; a positive control scored against an oracle difference map (259.6σ there, 0.074σ against the available quantity); a window-extremum readout that moved 0.005 over a 32× depth range; standardising a common fractional defect; and choosing a reference to maximise sample count — the exact error discipline 130 was written to prevent, committed by its own author two milestones later. **Facts 230-234, discipline 140-142, question 50** |
| `M30-hdr-cobracket-measured.md` | **R17 (HDR co-bracketing), and a general constraint that settles most of the capture-design workstream.** The review's premise is right and already paid for — the estimator handles per-frame gain (M24, M28) — so the question is whether there is a dynamic-range problem worth spending frames on. **At fixed total exposure time, splitting a light budget across exposures is EXACTLY NEUTRAL in the shot-noise regime**: `m` base + `m` at +2 EV cost the same `5m` time units as `5m` base frames and reach the same variance. Measured per pixel: median ratio **1.00041 / 1.00470 / 1.00192**, residual attributable to read noise in the predicted direction. **That identity constrains R15, R16 and R17 together — how a budget is *divided* across frames does not affect noise, only the total does — so every capture decision reduces to the non-noise asymmetries, and all are now measured.** Read noise binds below **2.0–6.5 DN** above black (0.014–0.044% of full scale) and **not one pixel in three stacks** sits there; clipping **at the frames a merge gathers** is **0.075%** max and **2.3× lower** than whole-stack, because highlights are disproportionately out of focus. What is left is **aperture**, which changes the optics rather than the allocation and which M20 prices at 9.6× — so capture co-design should spend its effort there. Two smaller results: the review's direction is **backwards for highlights** (a **−2 EV** pass rescues clipping; +2 EV clips *more*, 1.89% newly clipped), and **R16's half-step proposal is disposed of for free** — once photons are indifferent it is purely a focus-coverage question, and M27 measured coverage as saturated at 53 frames. **One author error, which voided script 01's headline:** the placebo held **frame count** constant when the scarce resource is **exposure time**, so four units of light were compared against one and `√4/√2 = 1.414` was recovered to four significant figures across three stacks that should all have perturbed it. **Facts 240-243, discipline 150, question 55** |
| `M32-posterior-confidence-measured.md` | **R2's confidence limb: posterior entropy is NOT the confidence output, and the frame choice was never the uncertain part.** A posterior over frame-of-best-focus needs a temperature, and that choice *is* the choice discipline 120 is about — the noise sd from the M4 model (external) versus `std_k(f_k)` (self-normalised). **The self-normalised arm fails with a number: across a 6.1× range of focus evidence it reports 0.6480 → 0.6482** (0.03%), non-monotonically, and under a 16× SNR degradation it moves 9% while the calibrated arm moves **22 orders of magnitude**. **The calibrated arm does not fail — it is degenerate:** the through-focus peak stands at **142–991 σ** above its own curve, so a calibrated posterior is a **delta function** on real data (perplexity 1.0000, rising only to 1.206 after 16× degradation, against a no-information null of 33.97). That σ was re-estimated model-free from the curve's along-`k` roughness and agreed to **1.24×** in the conservative direction, so the conclusion survives the noise model being wrong by two orders of magnitude. **Consequence: the defect in selection is not a noise problem** — a 142 σ peak is not SNR-limited, so M2's argmax defect and M27's under-resolved pixels are **sampling and model failures**, and confidence must be built from the merged estimate's predicted σ, the acceptance-set width and the sub-frame peak offset. **This also explains M20 from the other side:** when one frame stands 10²–10³ σ above the rest the minimum-variance estimator *is* nearly a selector. Two of the milestone's own pre-registered predictions died to its own controls — the no-information fixed point is **0.874, not 1.0** (the statistic is built from a maximum), and the "information-free" population carried 119 σ of evidence because its threshold was computed on frame-averaged data. **Facts 260-264, discipline 170, question 65** |
| `M33-subframe-offset-measured.md` | **Settles `B` §4.4's UNVERIFIED marker (parabolic vs Gaussian sub-frame interpolation) and answers question 65's candidate (c).** Ground truth is the full 105-frame `coffee-bean` grid against its ×2 decimation, adequate by **3.87×** and no more. **At operational sampling 48.7% of pixels miss their focus peak and give up a median 4.64% of their response (10.74% p90, 17.34% p99)** — nothing at the median, a great deal in a large minority, which is exactly what a per-pixel confidence map is for. **The finding that generalises: three-point parabolic interpolation gives a peak HEIGHT estimate anti-correlated with what it reports** — on a synthetic Gaussian its predicted deficit falls **21×** while the truth rises **8×**, because the relative deficit depends only on the scale-free *shape* of three samples. Discipline 120's failure mode in a third guise, inside the most standard piece of sub-pixel machinery in the field. **The log-domain fit with baseline subtraction is the fix** (exact on a Gaussian; calibration 0.710 / 51.2% within 2× on real data at ×2, against the parabola's 0.457 / 37.5%), and its placebo confirms it is not universally better — on a genuine parabola the parabola fit is exact and the log fit is 3.02× wrong. **Scope that keeps it honest: the failure is specific to peak HEIGHT.** For peak POSITION the parabola is fine at operational density (4.03× over the trivial argmax, only 9.4% worse than the log fit) — position is set by first-order asymmetry, height by curvature extrapolated beyond the samples, which is purely the assumed functional form. **Facts 270-274, discipline 180-181, question 70** |
| `M34-confidence-vector-measured.md` | **Decides M18's output contract: confidence is a VECTOR, not a number.** The three real-valued channels (predicted σ, posterior `n_eff`, sub-frame deficit) flag almost disjoint pixel sets — union **14.278%** against a **15.0%** perfectly-disjoint ceiling, **95.19% of the way there** — while every pairwise overlap sits at **0.53×–1.35× of chance** and the label-shuffle null returns **0.0256** against an analytic **0.0256**. **The decisive argument is not orthogonality but ANTI-correlation:** predicted σ has a worst-5% lift of **0.89×** on the true sub-frame deficit — the pixels it calls worst have *less* true deficit than average, because photon-starved pixels have flat through-focus curves — so **no monotone scalar summary of these channels is faithful**. Controls: each channel is **70–76% self-reproducible** under an independent noise re-realisation (three orthogonal *noise* sources would have produced the same table); a random channel scores **+0.0014** against truth; C4's degenerate row is a free second null. Specificity against M33's dense grid: deficit **+0.5560**, perplexity **+0.3349**, σ **−0.0726**. **The honest "do not trust" mask is the union — 14.3% of pixels, 3× what any single channel reports.** Qualifies fact 261 (per-pixel perplexity is a delta for only 76.5%, p99 4.74, max 39.05 — the tail is where confidence lives). Three of eight pre-registered predictions falsified. **Facts 280-284, discipline 190-191, question 75** |
| `M35-fit-generality-measured.md` | **Tests M33's fit on a marked-aperture ladder (119MSDCF f/5.6, coffee-bean f/8, 112MSDCF f/11 — coffee-bean recomputed, not quoted) and audits M33's own design.** **Question 70 comes back unanswerable: M33's adequacy gate fires on two of three stacks** (headroom 2.18× and 2.10× against coffee-bean's 3.62×), so those dense grids measure themselves rather than the estimator; `captures-needed.md` §7 now requires **2.5× the normal frame count**. **The deficit ladder's log–log slope is a cheaper second adequacy diagnostic** — 1.818 when adequate, 1.09–1.13 when not, because a sub-quadratic slope means the reference already misses peaks. **What survives the failed gate is the ratio between estimators**, since a multiplicative error in a shared reference cancels: the log fit wins on all three stacks (2.05× / 1.53× / 1.79×) across a 2× aperture and 10× ISO range. **Two audit results on M33: its numbers reproduce EXACTLY from independent code (0.457 / 0.710 / 51.2%), and its design had a real confound** — it scored a raw parabola against a baseline-subtracted log fit and never ran `parabola-baseline`. The missing cell prices it at **9% baseline / 91% log domain** (3% / 97% at ×4), so **fact 272 survives and is better supported**. Four of six predictions falsified; two of them uninformative because they read off the failed stacks. **Facts 300-304, discipline 210-211, question 85** |
| `M38-merge-on-real-frames-measured.md` | **The merge meets photographs, and its acceptance metric turns out to be broken.** Invariant 1 passes: flat-ROI noise **0.890× at gate 2.0** against argmax's 1.253×, two ROIs agreeing to 0.6% at every gate, six-gate sweep in 2.9 s. **Gate 0 reproduces M2-verification's independently measured 1.075× to 0.1%**, which validates the whole pass-one chain end to end. **Invariant 2 was measuring noise, not sharpness**: mean \|∇\| falls when a merge blurs *and* when it denoises, so the uncorrected reading showed a −45% "detail collapse" that is **−4.6% once the calibrated model's noise contribution is subtracted** — ~90% of the apparent loss was the merge being charged for its own purpose, and **fact 24 carries the same confound reversed**. **Fact 24's convention was identified by enumeration** as `mean(0.5(\|dx\|+\|dy\|))` to 0.01%; the reasoned π/2 guess died on a 1.43×-anisotropic ROI, and there is **no constant conversion** between the harnesses. **The gate does not transfer**: at a fixed threshold `n_eff` spans 2.26–7.42 across five stacks, `n_eff/N` clusters at 0.068–0.079, and hitting fact 212's target of 3 needs thresholds from 1.1 to 2.9 — so the free parameter must be **the target `n_eff`, not the gate**. **Facts 320-324, discipline 230-231, question 95** |
| `M18-merge-implemented.md` | **The sufficient-statistics seam (review item 6), decided: two-pass, 60 B/px constant in frame count.** The gather is proved non-perturbing by **byte-identical SHA256**. Also the model for discipline 254: it checked its own brief against the tree and found three of four items stale. |
| `crates/strehl-core/src/merge.rs` | **The estimation merge — the project's thesis in code, and the primary build artifact.** Two-pass: pass one folds each frame's 17×17-regularised focus field into a winner map (fact 84's −35%), pass two admits every frame within the gate of the winner and averages them in native raw DN (fact 19's 0.534×, fact 23's "only averaging goes below one frame"). Both passes commutative and associative, pinned by test. **"Never noisier than one frame" was asserted here and is FALSE** — it was structural reasoning (the winner is admitted unconditionally, so `n_eff ≥ 1`, so averaging can only help), and it survived four days because `predicted_sigma` was blind in exactly the place it could be violated. At `n = 1` the merge is *selecting*, and selection measurably costs **1.074×**. Fixed in `253e56f`: `SELECTION_INFLATION` prices it, and the test is now a two-branch contract that asserts **both branches actually occur**. Facts 428-431, question 101. `FOCUS_NOISE_SD` is measured in-crate at `0.015214 ± 0.000075`, and getting that number right required fixing a test LCG whose lattice aliased against the box filters (1.30× across seeds), a chosen tolerance no honest measurement could meet, and a plane too small to escape the finite-region SD bias. **That constant belongs to the operator, not the host** — the gate tolerance is `t·√2·FOCUS_NOISE_SD`, so a plugged-in operator that inherits it silently rescales the gate (M43, facts 436-438). **The gate threshold is deliberately unmeasured and explicit at the API boundary** — fact 212's `nwide = 3` is its target, and **M38 measured that no fixed threshold hits it across stacks** (fact 324). Facts 310-314, discipline 220-221, question 90 |
| `crates/strehl-cli/src/merge_cmd.rs` | **The merge on real frames** — the additive `strehl merge` subcommand. Two decode passes (pass two recomputes rather than caching, keeping memory `O(workers)`), the whole gate sweep in **one invocation** because decode dominates and folding one frame into N accumulators is nearly free, and both passes share `Ctx::field_for` so the gate compares against a field produced by the arithmetic that elected the winner. `run()` in `stack.rs` is untouched. **`detail_metrics()` is the part to read**: the noise-corrected detail invariant, `sqrt(raw² − model²)`, and the doc block explaining why the absolute gradient could not be corrected in place. Facts 320-324 |
| `A-prior-corpus.md` | The prior attempt, filtered; includes retractions |
| `B-algorithms-sota.md` | Algorithmic state of the art per stage |
| `C-landscape.md` | Competitors, licensing, artifact taxonomy |
| `D-rust-and-hardware.md` | Crates, versions, hardware envelope |
| `E-plugin-architecture.md` | Plugin design space and Rust API. **§F5 is a measured amendment (M43) and the part to read before building any of it**: the merge gate is denominated in a constant the *focus operator* owns, `Caps` has no field for it, and **all four of §F4's property tests pass a plugin that gets it wrong** — confluence, sensitivity, residue and the calibrated fixture, because a wrong noise SD does not move the peak. §F5.3 concludes the host should **measure** the plugin at load rather than ask it, which makes the fault unrepresentable and `--gate` dimensionless. §F5.4 upgrades §F4.5 to two calibration targets. Facts 436-439, 500-503. |
| `F-camera-lens-optics.md` | Optics of the reference rig; DoF tables |
| `G-edof-deconvolution.md` | **The microscopy/EDOF literature the review said was never surveyed (M19).** Settles novelty: the multi-frame focal-stack Wiener estimator is **Levin et al. 2009, Appendix B, Eq. (52)**, and they conclude against it. "First to model the occlusion halo" is **FALSE** (28 years of prior art). Do not build iterative deconvolution. |
| `M40-VERIFICATION.md` | **The orchestrator's `SELECTION_INFLATION = 1.074` repair does not stand, and every defect was a CHOICE (rule 24 again).** The arithmetic reproduced to four decimals; the reasoning did not. **The constant multiplies a SPATIAL sd ratio into a TEMPORAL sigma** — undefined regardless of value (fact 440). It **exceeds its own ceiling**: a pure-noise plant built to maximise the winner's curse caps the operator at **1.045x** (fact 446). It is **not a constant** — the same estimator reads 1.0001x…1.2732x over six ROIs (fact 443) — and a fixed-frame arm with no selection at all reproduces the worst reading to 0.0001 (fact 444). The n>1 branch is **wrong at every n**: the decay is smooth 1.0770→1.0220, not a step (fact 448). **On a genuinely detail-free plant the correction crosses zero and lands FURTHER from truth than the defect it replaced** (−11.63 DN where truth is 0), hidden by the shipped `max(0,.)` (fact 454). And **fact 341's premise is false**: the "flat" ROI spans 3.5× in per-frame detail and its modal winner carries 1.267× the reference frame's detail unmerged (fact 455). Also found a **fourth consumer** nobody enumerated (`merge_cmd.rs:912`), which still prints the unrepaired 1.0000x and is Jensen-wrong by 2.4–5.9% (facts 452-453). **Recommendation: revert to 1.0** — shipping 1.074 is worse than shipping nothing. Keeps the two-branch *shape* (fact 458). Facts 440-459, disciplines 263-267, questions 106-110; re-rules 428-431 and re-opens 341. | M40 (independent) |
| `M42-window-ladder-measured.md` | **The window optimum belongs to the operator, and M17's operator does not want 13.** Re-ran M13/M15's ladder for `tenengrad-sq`: pooled argmin moves **w13 → w11**, and **0 of 6** independent subsets choose 13 (against **6/6 → w13** for the shipped magnitude operator). 13 survives the pre-registered 0.87 DN basin by **0.0096 DN — 1.1% of the tolerance** — a real pass, and the weakest available. Re-radiusing is **free**: `box_mean` is O(1) in radius, w11 and w13 both 3.226 ms/frame/Mpx. Falsified its own prediction 3: the blind-spot cure is **radius-invariant** (D = 0.1860 from w8 to w40) because squaring breaks TV conservation itself. **New open limitation: on a width-9 smooth ramp `tenengrad-sq` reads D = 0.6802 vs 1.0000 — fact 73's blind spot is closed on steps and only half-cured on gradients**, which is the common macro case. **Read the orchestrator addendum at the top before acting on the recommendation: the edit is a TRIPLE** — operator, radius *and* `FOCUS_NOISE_SD`, which moves **1.528×** and would silently turn `--gate 1.0` into 0.654 (facts 509-511). Facts 480-491, disciplines 258-261, questions 103-105. Answers Q1. | M17 (re-task) |
| `M45-plugin-crate-implemented.md` | **The plugin seam is built, and it closes the §F4.6 fault-5 hole by construction rather than by test.** `crates/strehl-plugin` (~3 400 lines, 33 tests): `FocusMeasure` **deliberately has no noise-SD method** and `Calibration` has **no public constructor**, so a contributed operator has nowhere to put a wrong constant — the host measures it at load. The calibrator reproduces `FOCUS_NOISE_SD` to **−0.018%** and `FINE_FOCUS_NOISE_SD` to **−0.000%**, an order of magnitude tighter than the Python reference, and reproduces all seven fact-439 `k` values to **±0.43%** — an independent second-language confirmation of M43, SML at 6.6833 vs 6.680. **It also refuted three things in §F5.3's own published sketch, one structurally:** the sketch's `calibrate()` is *unseeded*, measuring **5.56% spread** across planes, so the fix for fault 5 as designed would have violated §F4's confluence property; the margin omits the host regulariser (bias +0.31% and operator-dependent, so it does not cancel in `k`); and fact 505's 1.7 ms cost bound is **2.95× low per plane, 35× low per registration**. §F5.5's proposed byte-identical test **would have gone red**. **Read §6.2 regardless of what you are doing here** — its first positive control divided both the field *and* the tolerance by the same wrong constant, which is the identical comparison, measured 0 flips in both arms, and would have let a `rate < 1e-4` assertion pass green with zero power. Facts 520-529, disciplines 284-286, questions 123-125. **Nothing is wired into `merge.rs`** — that is one multiplication, owned by whoever holds that file. |
| `M43-plugin-calibration-seam.md` | **The pluggability requirement has a measured hole, and the existing design cannot see it.** The gate is calibrated in units of a constant owned by the *focus operator*, and workstream E has no slot for it. A contributed operator that inherits the host's constant silently rescales the gate: measured, one such mistake reverts **87.76% of pixels to pure selection** while the log still reads `gate 1.00`. Capability negotiation, confluence and the §F4.3 sensitivity test all pass it — **a missing contract, not a missing test**. §8 surveys seven textbook operators and finds `k` spanning **10.4×**, worst case **6.68** at the sum-modified-Laplacian — the canonical SFF operator, i.e. the likeliest contribution there is — which makes the load-time refusal mandatory. **§8 also corrects §2's own `k`**: it had divided a regularised SD by an unregularised one, and a two-target calibration caught it. Facts 436-439, 500-501, disciplines 256-257, question 102. |
| `M50-fpn-anisotropy-measured.md` | **M16's row-FPN refutation, verified independently from the sensor side -- and one of its supporting numbers stated too confidently.** Measured the fixed pattern by cross-half covariance (temporal noise contributes exactly zero in expectation; the estimate may go negative, so it can say "no") on full CFA planes at all 11 ISOs, placebo at 1.2% of plant. Row term is 1.8-12.8% of per-pixel FPN and the COLUMN term is larger at 4 of 11 ISOs; the proposed fix moves the anisotropy index 0.009 on a +-1 scale while destroying 99.96% of *planted* banding. Fact 93 loses its NOT-INDEPENDENTLY-VERIFIED tag and gains fact 560's qualification: isotropic to ~5%, not exactly, positive at 11/11 ISOs (M16's own numbers never once cross 1.000). Verdict unchanged -- M16's ladder needs 1774x. By-products: M4 §5 verified at 1.0043, §8.1 a third time at 0.99993, the `rawpy` use-after-free (rule 32), and a ratio statistic that returned **-494.885** for the most positive case there is. Started as a duplicate of a CLOSED question -- see discipline 294. | Orchestrator |
| [`M49-unapplied-findings.md`](docs/research/M49-unapplied-findings.md) | **Thirteen measured findings that never reached the code, and the mechanism behind all of them.** The worst: ACCEPTANCE INVARIANT 1 is computed from the raw spatial sd that fact 469 forbade, so a merge could get **6.3x** noisier and still print PASS. Also: the clip mask never reaches the focus volume (always-clipped pixels read focus contrast at its **maximum**, carrying zero information); `--target-n-eff` cannot produce an image; `profile.rs` cites a fact number that resolves to a **different fact**, which a number-validity check cannot see. The mechanisms are the point -- **a test whose subject and object are the same value has no power to fail** (that is how 1.074 passed every day), and **a consequence reaches one consumer and not its siblings** (four instances, and in every one the file that was edited was correct afterwards). Clean negative: nobody hid anything. `merge.rs:74-108` is four paragraphs explaining why the constant it declares is wrong. The corpus writes corrections into the doc comment instead of into the value. | M49 |
| [`M47-gain-blast-radius.md`](docs/research/M47-gain-blast-radius.md) | **The ISO-50 gain fix is correct; three claims in the brief that commissioned this audit are not.** The gate was **1.414x too TIGHT, not too loose** -- responses are sigma-normalised against a fixed absolute tolerance, so a too-small sigma admits FEWER frames. Proven end to end: the pre-fix published `n_eff` reproduces at corrected gate `X/sqrt(2)` on both ISO-50 stacks with the ISO-160 placebo unmoved **digit for digit**. **A plant that supplies its own noise constant cannot detect that constant being wrong** -- M40's and M41's plants are scale-invariant in `g` to 0.05% and passed cleanly through all twelve milestones it was a factor of two wrong. Most conclusions survive (fact 88's refutation at 1.33-1.64x; fact 241's 0.0000% with a 28.5x margin, re-measured across all four CFA planes); fact 324's clustering half does not, and fact 472's stack ordering inverts. User impact stated honestly: the pixels are the exact valid output of a tighter gate -- **mislabelled, not wrong** -- but every sigma printed beside them is off by sqrt(2). | M47 |
| [`M46-detail-metric-measured.md`](docs/research/M46-detail-metric-measured.md) | **SUPERSEDED -- ITS HEADLINE IS REFUTED. Read `M55-sigpow-verification.md` first.** This row previously read "an admissible detail metric exists". It does not: SYNTHESIS facts 695-712 measure `sigpow` as **non-monotone in true resolution** (it fires 344x past its own threshold in the *wrong direction* at MTF 0.0068), saturated by a **0.15%** photometric change, and dominated on real data by the half-stack split choice at **50x** the optical signal. The **0.937** separation and the **0.973** paired figure are the same reading (fact 695); the **0.4%** out-of-sample confirmation passes for every rho from 0.02 to 3.0 and falls **231x** short of the variance it requires (fact 697). Facts 610, 613, 617, 619, 620, 640, 641, 644 and 649 are all amended. **What SURVIVES, and is why the report is still worth reading:** the structural argument that every correlation metric is blind by construction to a merge that low-passes its own output (measured 0.000); that no source on this sensor is both featureless and blurrable, so the brief's demanded flat-ROI control cannot exist; the closure of question 120 (the 0.4961 censoring is common-mode FPN, white to Nyquist); and the parity-split requirement, confirmed 6/6 to six figures (fact 702). **`strehl` has NO detail instrument** -- see section 8 item 2 and fact 724. | M44 (re-task), REFUTED by M55 |
| [`M48-read-noise-measured.md`](docs/research/M48-read-noise-measured.md) | **The second wrong shipped sensor constant, fixed: `read_noise_e_high` 1.47 -> 1.2392** (relative-LS optimum over the 7 high-mode ISOs), with the negative control reproducing the brief's +12.3% error through Rust rather than Python. **It corrected the brief's mechanism**: the hot-pixel tail explains about **1/10** of the estimator gap, not the gap -- M22's whole map carries 2.2-3.6% of variance and oracle excision moves pooled RMS 1.1-1.8%. The gap is the ordinary width of the per-pixel sigma distribution. Finding 5 was attacked five ways (all-ISO fit, AIC, F-test, LOO-CV, equal-parameter confound) and **survived**: a single shared floor beats two, F=2.75, p=0.14. Two disclosures worth more than the constant: an `np.sort` axis defect whose first answer was **inverted** rather than merely noisy, left as-run per rule 15 and superseded; and a near-miss caught on the last pass, where its own recommendation leaned on a PTC *intercept* that M25 had already measured as untrustworthy, in a document it had cited twice. **`FOCUS_NOISE_SD` is NOT re-derived under the new constant** and is named as the most likely place the change has an unintended consequence.  **Section 12 answers a follow-up by refuting its premise: `FOCUS_NOISE_SD` is a property of the operator, not the sensor, and could not have been contaminated.** | M48 |
| [`M52-gate-cluster-verified.md`](docs/research/M52-gate-cluster-verified.md) | **Seven of eight gate facts stand; the eighth was stale within four hours of being written and its numbers were shipped in CLI help.** Also the night's most architecturally consequential measurement: a per-operator noise constant does **not** make the gate portable -- five correctly calibrated operators still spread 4.54x, against a placebo of 1.00000x | M52 |
| [`M55-sigpow-verification.md`](docs/research/M55-sigpow-verification.md) | **Killed the project's detail metric after three milestones had been spent on it.** `sigpow` is NON-MONOTONE in true resolution above ~0.7 px blur, a 0.15% photometric gain change saturates its decision threshold, it reads negative in 7 of 36 real cells, and on real data the half-stack split choice outweighs the optical signal by **50x**. Its separation numbers reproduce exactly and are still not measurements: `S`'s denominator is a null residual, reading **0.770-0.980** on one plant with only the repetition count varying. **It also refuted two of its own suspicions in the author's favour.** Facts 695-712. |
| [`M55-acceptance-spec.md`](docs/research/M55-acceptance-spec.md) | **A pre-registered, executable acceptance battery for a detail metric, committed BEFORE any candidate exists and not relaxable to admit one.** Thresholds are numbers with provenance, not adjectives. Calibrated against four reference metrics first: it kills all three known-bad ones and passes a passability probe, so it has demonstrated power in **both** directions per rule 39. The calibration changed the battery twice. |
| [`M57-detail-metric-from-first-principles.md`](docs/research/M57-detail-metric-from-first-principles.md) | **The fourth hunt for a detail metric, commissioned as an explicit bounded override of a pre-registration that said not to.** Candidates designed from first principles against M55's measured constraints, with kill conditions pre-registered. **Gates nothing** -- the build proceeds beside it, and if it comes back empty the answer is the unmeasured detail claim, not a fifth hunt. Proposals are numbered `P1...` per rule 28 and are NOT facts. |
| [`M48b-fpn-rho-measured.md`](docs/research/M48b-fpn-rho-measured.md) | **`rho_dark` and M46's `rho` are different quantities and no rescaling relates them** -- a dark frame has no shot noise in the denominator and no PRNU in the numerator. Answers question 142 by refusing its premise. DSNU is **0.12%** of what M46's `rho` requires, robustly across three decades of assumed signal, so 0.3094 is SCOPED rather than refuted. `rho_dark` spans **5.52x** across 11 ISOs. **Reported its own error bar as wrong by two orders of magnitude**, found by tabulating one extra column. Facts 663-678. |
| [`M54-clip-mask-measured.md`](docs/research/M54-clip-mask-measured.md) | **15360 is not a clip point on `coffee-bean`; 16383 is** -- the histogram is smooth across the declared white level and spikes three orders of magnitude at the container max. A 35% defect count was an artefact of a statistic whose domain differs from the flag's. Facts 679-694. |
| [`M58-citation-content-repaired.md`](docs/research/M58-citation-content-repaired.md) | **NAMING TRAP: written by M54, not M58.** **Refuted three of the five citation repairs it was routed to make, one of which would have introduced a 3.27x error in the opposite direction** -- at `through_focus.rs:514` both fields enter as the merge consumes them, so 5.943 is correct there and 1.815 is not. A site list is not a defect list. Also found fact 723 over-counting 4x and under-counting simultaneously, and killed question 170 by finding four correct citation forms already committed. Facts 767-778. |
| [`M58b-fold-fidelity-audit.md`](docs/research/M58b-fold-fidelity-audit.md) | **An audit of the orchestrator's own folds: 3 HIGH, 8 MODERATE, 12 LOW, 6 omissions, 1 process defect.** A row that was false on its own enumeration; a sweep whose framing structurally excluded the rows it was meant to repair; three rows carrying an amendment in one cell and the contradicted claim in another. **At least three of the twelve LOW findings were not low** (fact 781). It also refuted two of its own suspicions in the author's favour. Facts 758-766. |
| [`M55-acceptance-spec.md`](docs/research/M55-acceptance-spec.md) | **A pre-registered acceptance battery for detail metrics -- which refuted a whole class of the corpus's prior readings.** A contiguous half-stack split reads **inside an empirical roll-null on 6 of 6 real cells, detail ROIs included**, so facts 641/702's contiguous readings were ratios taken inside the null and fact 707's "something else operates on flat regions" dissolves. **Its own falsifiers fired twice and it recorded a pre-registered criterion as NOT MET rather than relabelling it.** Also: the +-0.003 decision threshold has a **75% false-alarm rate** at realistic noise (specificity 0.25, sensitivity 1.00); **a metric returning a CONSTANT passes monotonicity and homogeneity**; M46's 0.05 px reference blur is a **0.376% MTF loss**; the six held-out stacks are **three subjects** and the word *adequate* was withdrawn; and B6's coverage kill condition **was read by no code**, reproducing fact 711's disease inside the spec written to prevent it. **Two defects appeared in the instrument built to prevent them, within an hour.** `spec_v1.py` was destroyed by its own patch script (CPython truncates before validating `newline=`) and rebuilt from bytecode, verified by 35 code objects, 44 line positions and an 799 s behavioural re-run differing on 3 of 83 lines with no number changed. **Facts 861-876, disciplines 397-408, questions 195-198; answers question 165** |
| [`M59-corpus-linter.md`](docs/research/M59-corpus-linter.md) | **Built `scripts/corpus_lint.py`, and found that 458 of 639 fact rows in `SYNTHESIS.md` did not render as table rows.** Three blank lines used as batch separators inside section 4 each terminated the markdown table; everything below rendered as paragraph text. **The orchestrator's own check passed throughout, because it counted rows by regex rather than by what the renderer does.** Also found four rows across four reports silently discarding 2-6 cells from unescaped pipes in code spans -- the worst being the row carrying the Wiener estimator, the deconvolution core. **Two findings outrank the violations.** Its line-ending check fired 13 times and every one was false: it counted CRLF on disk, and `git ls-files --eol` shows the index is 1,351 LF / 0 CRLF / 0 mixed, so it was measuring the author's `core.autocrlf` setting -- permanently red on Windows, permanently green on Linux, meaningless either way. And it reports **against its own invariant** that neither half of the placement check would have caught the defect that motivated it, because `39b5ca7` wrote into the *body* of an existing item. Nine synthetic fixtures, each proving one property; every check was seen to fail. **Facts 857-860, disciplines 395-396; answers question 178** |
| [`M58c-repair-audit.md`](docs/research/M58c-repair-audit.md) | **Audited the orchestrator's REPAIRS, and refuted its summary claim that they were complete.** 2 HIGH, 6 MODERATE, 5 LOW. The two HIGH are both mine: fact 627's headline still asserted "the ISO-160 ones" after its own amendment refuted it -- **I had folded a new fact naming that defect hours earlier and left the sentence standing** -- and question 170's MOOT verdict was written into *discipline* 170, consuming its opening `**` so it stopped rendering. **Both things I flagged as uneasy came back CLEAN**: the `87.76% -> 89.02%` propagation hit exactly the two `k = 6.68` sites and left seven correctly-paired sites alone, and rule 39's `0.980` endpoint is what M55 states at three sites. **Six of the auditor's own suspicions were refuted in my favour -- discipline 305's eighth validation.** Also established that only **33 of 599 fact rows carry a sha**, and that facts 733-757 cite `M53 F1`-`F10` findings existing in no commit. **Facts 836-844, disciplines 389-390, question 192** |
| [`M48c-defect-layer-measured.md`](docs/research/M48c-defect-layer-measured.md) | **Answers "does the merge handle sensor defects?" with: it is BLIND, and turns up a 2.17x hole in the sensor model on the way.** Against a contrast-matched control the merge's defect-specific amplification is **1.00 +/- 0.08** -- it lifts a hot pixel and real detail of matched contrast by the same 1.23-1.32x, so **a defect map cannot be deferred to the estimator**. The census independently corroborates M22 to 19.8% (0.0414% vs 0.0346%), finds **99.8% singletons, largest cluster 3 px**, and a **68x odd/even sensor-row asymmetry** that looks architectural. **The bigger result is incidental:** the dark-current excess of a FIXED pixel set has two flat plateaus in electrons stepping **2.174x exactly at `second_base_iso`** -- impossible, since dark current cannot depend on the ISO dial. It is a **labelling** failure, not an arithmetic one: every DN prediction is unaffected, but `gain_divisor` and `read_noise_e_high` are **degenerate above ISO 400** and only their product is measured. The agent **refused to change the constants** on dark-frame evidence alone (its own discipline 326) and shipped a rule-30 tripwire asserting the known-wrong behaviour instead. Two disclosures: a `uint16` ISO bitmask bitwise-ANDed to bit 0, silently selecting ISO 50 -- **the conclusion survived and was not entitled to**; and a placebo reported as FAILED because the ratio of two near-zero medians is unbounded. **Facts 783-808, disciplines 372-377, questions 184-187** | M48 |
| [`M56-citation-audit.md`](docs/research/M56-citation-audit.md) | **Content-level citation audit: 11 defects among citations that a number-validity audit had passed clean. Resolving is not supporting.** **This report is itself a rule-31 violation by the orchestrator** -- eleven facts (713-723) were folded from it before it was ever committed, and recovery was attempted afterwards. Read `M58b` and facts 767-778 for the subsequent corrections; three of its findings were later refuted. Facts 713-723, fact 765. |
| [`M53-flat-ratio.md`](docs/research/M53-flat-ratio.md) | **Replaced ACCEPTANCE INVARIANT 1: the flat-ROI raw spatial sd ratio reads a planted 10x noise explosion as 1.513x.** Ships `x - box9(x)` valid-interior with a DERIVED gain `sqrt(1-1/81)`, referenced to the median over ALL frames with min-max disclosed, so fact 441's 1.60x denominator freedom is unrepresentable. **Its unplanted finding is the strongest result: the legacy statistic ranks unregularised argmax -- the defect the project exists to remove -- as the BETTER of two merges, and passes a 21% real noise increase.** Also: the milestone refuted and withdrew its own headline verification. **This report was itself a rule-31 violation** -- facts 733-757 were folded before it existed (fact 843, question 192); it was written afterwards from the fold's own citations, and three F-slots are marked UNRECOVERABLE rather than reconstructed. Facts 733-757, 843. |
| [`M53-flat-roi-statistic.md`](docs/research/M53-flat-roi-statistic.md) | **Question 183: facts 19 and 734 were never measured on the same ROI, so the founding number and today's were never comparable.** Fact 19 used `2272,1344,256,256`; fact 734 used `1356,32,512,512`. On M2's own ROI today's binary reproduces M2's denominator EXACTLY (28.201 DN) and the regularised merge crosses 1.0 like for like (1.075x -> 0.890x). **Kills the naming hypothesis** the orchestrator offered. NOT reproduced: M2's 0.981x placebo, and operator-vs-window could not be separated because `ring(1,3)` has no implementation left. Facts 733-757. |
| [`M62-sqrt-n.md`](docs/research/M62-sqrt-n.md) | **The first acceptance test with a known correct answer.** A static repeat burst is the one problem whose truth is arithmetic: every frame samples the same latent, so an estimator must reach exactly `sqrt(N)` and a selector must reach 1.0. **`strehl merge` scores 5.4778 against `sqrt(30)` = 5.4772 (+0.008%) at gate >= 8; `strehl stack` scores 0.7690 -- a 1.300x noise INCREASE -- and `merge --gate 0` (same binary, `n_eff == 1`) scores 0.9768. Separation 5.61x, against 1.039x for the flat-ROI invariant that ships today.** Demonstrated power, not argued: six selector configurations run, all fail. Ladder calibrated to <= 0.08% at `k` = 1..30. Shared-noise trap resolved by option (b) -- the frozen realisation cancels identically when truth is defined as the latent -- and the resulting prediction matched the CLI's own instrument to 0.03%. Real dark frames (Arm D) show sensor noise averaging as `sqrt(N)` to within 1% on all four planes, replicate M4's dark sigma to 0.7%, and find G1/G2 temporally correlated at rho = +0.073. **Arm A is circular w.r.t. calibration (rule 34) and cannot validate the sensor model; only the real burst can.** Arm C's photon-transfer path is written and smoke-tested, and is what closes fact 808. One pre-registration criterion tripped and is disclosed. |
| [`M61-ptc-high-iso-measured.md`](docs/research/M61-ptc-high-iso-measured.md) | **Refuted M48c's derived 2.174x dual-gain step by direct photon-transfer measurement** -- conversion gain at ISO 500/1000 agrees with `profile.rs` to 1.03 and 1.04 of the low-mode plateau, surviving every fit gate. **Vindicates M48c's refusal to change a constant on a derived number.** Also found, uncommissioned: **the B plane's conversion gain is 0.84x the greens' at every ISO and `profile.rs` does not model it.** Scopes its own ISO-1000 arm as the weak one. **Its `foam` CPL provenance was wrong and is corrected in SYNTHESIS fact 925 -- read that, not the report's table.** |
| [`M60c-speckle-citation-and-the-gate.md`](docs/research/M60c-speckle-citation-and-the-gate.md) | **Repaired fact 23's speckle citation in `merge.rs` and restated the gate's justification.** Part of the M60 stem -- see rule 41; `M60` was a three-way collision. |

Claims inherited from `C:\dev\macro` are suspect by default. Several were
retracted under scrutiny — including a headline noise finding that measured
*spatial* sigma while labelling it *temporal*, and three fabricated citations.
`A-prior-corpus.md` records which survived.

**Reusing an experiment harness?** `experiments/m11-focus-bakeoff/run-m11.ps1`
does **not** list the ROIs that appear in M11's committed CSVs. Take ROIs from
`data/noise-*.csv` and `data/planted-*.csv`, not from the script, or the numbers
will not reproduce. **The discriminator is PER STACK, not global** (fact 88): on
109MSDCF a flat ROI has `single_sigma` ~28-30 DN and a detail ROI ~630-700 DN,
but on 119MSDCF all four *correct* flat ROIs sit at **43.2-53.1 DN** — applying
109's band to 119 rejects every one of them. Separate the two populations within
a stack; never carry a threshold across stacks. More generally, **reproduce one
published number from the original data before extending anyone's experiment** —
and stratify on every column the original stratified on. Better still, re-run
the original harness unmodified first: it is deterministic, so a published
command line should reproduce that milestone's committed CSVs **byte for byte**
(M15 §0.2 did, on both stacks). If it does not, stop — nothing downstream is a
valid comparison. Byte-identity is a *consistency* check, not independent
evidence (discipline 20).

## Build

```
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Reference rig

Sony A7C II (`ILCE-7CM2`) + Sony FE 100mm F2.8 Macro GM OSS (`SEL100M28GM`).
Pixel pitch 5.12 um. RGGB. Black level 512, white level 15360, active area
7032x4688. Confirmed by measurement, not by documentation.

**v1 targets in-camera focus bracketing only** — camera fixed, focus moves, so
frames differ by magnification and occlusion never changes.

Focus rails translate the camera, producing genuine parallax and occlusion. Rail
support is **deferred**: no rail hardware is available to test against, and an
untested geometry model would violate rule 8. The `CaptureMode` enum and mode
detection stay in place because that is the one seam the rail case genuinely
needs. Never silently apply the breathing model to rail data — detect from EXIF
plus fitted residual signature, and warn. Never trust a user flag alone.
