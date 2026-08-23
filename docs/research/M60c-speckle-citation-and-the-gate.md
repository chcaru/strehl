# M60c — Fact 23's speckle pair, and whether the `Gate`'s conclusion survives losing it

**Scope:** `crates/strehl-core/src/merge.rs` only. This is **fact 822's routed repair**.
**Status:** both live sites repaired. The `Gate`'s conclusion **does not survive**; it is
now marked ARGUED with the missing measurement named.
**Findings numbered G10+**, continuing from M60b's G1–G9.
**Nothing here is a new corpus measurement.** Every number is read from an existing row or
report, or derived. Where I derive, I say DERIVED.

---

## 0. Rule 40 check, first

The brief told me this had been found once already and that two of four sites were repaired
by someone else. I checked before doing anything:

| site | state at HEAD when I looked | action |
|---|---|---|
| `strehl-core/src/stack.rs` `DEFAULT_SPECKLE_TOLERANCE` doc | **already caveated** | none — read as precedent |
| `strehl-cli/src/merge_cmd.rs` `Fact 23's 34.4% -> 0.868% pair` `eprintln!` | **already caveated** | none — read as precedent |
| `strehl-core/src/merge.rs` module header | **live, uncaveated** | repaired |
| `strehl-core/src/merge.rs` `Gate` doc | **live, uncaveated** | repaired |

So: not already repaired, and the two repaired ones gave me the wording to follow. Both are
other agents' files and I read them only.

---

## 1. What I verified myself, against the sources rather than the brief

**G10 — Fact 23's pair is the retired ring difference. CONFIRMED, and it is *both* halves,
not just the speckle one.**

`M2-verification.md` section 4 (`:147-165`) has exactly **four** rows: real argmax
**34.385%** (the tool reports 34.381% including borders), uniform-random null 66.174%,
observed-histogram null 53.496%, and 17×17-regularised **0.868%**. **No row mentions
Tenengrad.** `M2-verification.md:204-206` states the operator explicitly — "the
ring-difference focus measure correlates winners over 3–7 px". Tenengrad did not exist until
M14. So fact 23's `34.4% -> 0.868%` is *ring-unregularised → ring-regularised*: the delta is
**regularisation**, measured on an operator the shipped code no longer uses.

I confirm the already-repaired `stack.rs` doc's stronger claim independently: **no section-4
row publishes a regularised-Tenengrad speckle at all.** There is therefore no matched pair to
substitute, and per the brief I have not invented one.

**G11 — Why this survived four sites: two different mechanisms land in the same place.**
This is mine; it is not in M56's audit and I think it is the transferable part.

Fact 71 reads, against the retired ring on the same ROI: index speckle **34.381% → 1.010%**.
That pair is *ring-unregularised → Tenengrad-unregularised* — both **unregularised**, delta =
**operator**. Fact 23's pair is *ring-unregularised → ring-regularised* — both **ring**,
delta = **regularisation**.

So two entirely unrelated interventions both start at ~34.4% and both collapse it ~34–40×, to
0.868% and 1.010% respectively. A ring number and a Tenengrad number look interchangeable
because they agree to within 16%, and they agree by coincidence. That is a much better
explanation of a four-site propagation than carelessness, and it generalises: **numbers that
happen to agree are the ones that get swapped, so near-agreement between two measurements of
different things is a propagation hazard rather than a reassurance.**

It also has a sharp consequence for this specific argument, below.

---

## 2. The part the brief actually cared about: does the conclusion survive?

The sentence under test was:

> averaging the focus field over 289 pixels before electing a winner is what takes speckle
> from 34.4% to 0.868% (fact 23), and speckle *is* the winner's curse made visible. Electing
> on the regularised field rather than the raw one is therefore **load-bearing for the gate**,
> not just for the winner map.

It fails on three independent grounds. Any one of them is sufficient; I list all three because
they fail in different ways and only the third is a measurement.

**G12 — Wrong quantity. The cited number cannot bear this argument even with the right
operator. DERIVED.**

Speckle is a property of the winner **index map** — how spatially incoherent the argmax's
choice of frame is. The winner's curse is an upward bias in the winner's **value**, and it is
the value that sets the acceptance set, because the gate admits on `|response_k − response_win|`
against a tolerance. A spatially coherent index map is entirely consistent with a uniformly
biased winner: smoothing correlates neighbouring pixels' choices without touching the bias of
the max at any one of them. So speckle is downstream evidence that argmax is electing noise;
it is not a bound on the bias. **Even a correctly-matched regularised-Tenengrad speckle would
be evidence about a different quantity than the conclusion needs.**

**G13 — The closest operator-matched arm the corpus has points the *other* way. MEASURED
(fact 343).**

Fact 343 measures, on the shipped normalised Tenengrad, same 22 frames, same flat ROI:

| election | selection noise ratio vs one frame |
|---|---|
| **unregularised** argmax | **1.0678×** |
| **regularised** argmax (= merge gate 0, fact 320's 1.074×) | **1.0739×** |

Regularising **raises** it. Fact 343 says so in as many words — "here regularising *raises*
the ratio slightly instead of dropping it".

This is the winner's curse's measured effect on the output, on the right operator, with
regularisation as the only variable. It is not the acceptance-set size itself, so I do not
call it a refutation. But it is the nearest matched measurement in the corpus and it does not
support the claim; if regularising contained the curse, this is the arm that should have
moved down.

Note the irony the file already half-contained: the module header **already** carried fact
343's caveat for fact 23's *noise* half, and did not notice that the same fact is the
operator-matched arm of the *speckle* half's argument two hundred lines below.

**G14 — A derivation for why the effect should be small in either direction, which is why
G13's near-null is unsurprising. DERIVED.**

`Gate::threshold` is expressed in units of `FOCUS_NOISE_SD`, which is *defined* as the
standard deviation of the **regularised** response. The winner's-curse bias for a max over N
scales with the field's own noise SD (≈ σ·√(2 ln N)); the admission half-width scales with the
same σ. Their **ratio** — which is what actually admits or rejects a frame — is therefore
first-order invariant to how hard the field is smoothed. Regularising shrinks the curse and
the tolerance by the same factor.

Fact 503 makes exactly this scaling argument for a constant rescale and predicts the admission
set is "bit-for-bit unchanged". Regularisation is a spatial average rather than a constant
rescale, so the analogy is partial — it changes the field's *shape*, not only its scale, and
the signal term does not scale with σ. **I am not claiming the effect is exactly zero.** I am
claiming the noise term cancels by construction, which is a reason to expect a small effect,
and which is consistent with G13 measuring a small effect of the wrong sign.

**G15 — Verdict: outcome (3), with (2)'s repair.**

Of the brief's three acceptable outcomes, this is **(3): the conclusion does not survive**,
and the gate's justification needed restating — but the *replacement* is (2)'s shape, because
the measurement that would settle it does not exist:

> **`n_eff` under regularised versus raw election at a matched tolerance, on real frames.**

Nobody has run it. It is cheap — it is one boolean on the election path — and it is the
honest way to close this. I have not run it, because this task was scoped to documentation and
because running it would have meant deciding the answer in the same milestone that framed the
question.

What survives, and is now what the doc says: regularising before election is load-bearing for
the **winner map** and for **edge error** (fact 84, 24.79 → 15.99 DN, which *is* this
operator's number). Its value **for the gate** is unestablished. The doc now carries an
explicit instruction not to restore a stronger sentence without the missing number.

---

## 3. What I changed

`crates/strehl-core/src/merge.rs`, +58 −16, doc comments only. No code, no test, no behaviour.

- **Module header (`:15-35`).** Fact 23's speckle pair removed from the load-bearing position
  and replaced with fact 84's edge-error number, which is this operator's. Added the caveat in
  the form `stack.rs` uses — names the ring operator, cites `M2-verification.md` section 4 and
  `:205`, notes Tenengrad postdates M14, states that no section-4 row publishes a regularised
  Tenengrad speckle, names fact 71's **1.010%** as the operator-matched *unregularised* figure,
  and points at the run's own printed value as the regularised comparable. Then states G11's
  near-coincidence explicitly, so the next reader knows *why* the two numbers are confusable.
- **`Gate` doc (`:195-236`).** Heading changed from "why the regulariser is the defence" to
  "what the corpus does *not* say about the defence". The mechanism paragraph is kept — the
  curse is real. The claim is replaced by G12/G13/G14 as three numbered grounds, then
  **Status: ARGUED, not measured**, then the named missing measurement.

**Sites I checked and deliberately did not change** (all still correct):

| site | why it stands |
|---|---|
| `:39` `*Only averaging goes below one* (fact 23)` | qualitative ordering, not the operator-dependent pair — and the sentence already uses **1.0739×**, fact 343's *Tenengrad* value, so it is operator-correct as written |
| `:1409` test comment, same phrase | same |
| `:2165` "the mechanism fact 23 measured: a lone noise spike…" | describes mechanism, quotes no number |
| `:6-9` fact 19's 1.253× | **already** correctly caveated — the file explicitly says it "is not quoted as one [a baseline]", per fact 343 |
| `:40` fact 19's 0.534× plain mean | fact 19 is a different operator, but fact 343's prohibition is specifically on quoting it as *this pipeline's baseline*, which this file does not do. Flagging as adjacent, not repairing — out of scope |

---

## 4. Verification

All with real build lines, no `-q`, per rule 33 as amended.

| command | result |
|---|---|
| `cargo fmt --all -- --check` | exit 0 |
| `cargo clippy --workspace --all-targets` | `Checking` × 4 (core, raw, plugin, cli), **0 warnings**, exit 0 |
| `cargo test --workspace` | `Compiling` × 4, **220 passed, 0 failed** (40 + 136 + 35 + 8 + 0 + 1 + 0) |
| `cargo doc --no-deps -p strehl-core` | `Documenting strehl-core`, exit 0 — **the test that actually exercises a doc-only change** |

Line endings verified byte-wise after editing: **CR=0, LF=2248**. `git status` confirms
`merge.rs` is the only modified file among the ones I own.

Per discipline 366 I did not rely on exit codes: the `Checking`/`Compiling`/`Documenting`
lines and the per-suite counts above are the evidence, and I read them.

**G16 — three pre-existing rustdoc warnings, found by the doc build, not mine and not
repaired here.**

`cargo doc` is evidently not routinely run; it emits three unresolved-intra-doc-link warnings,
none in `merge.rs` and none introduced by this change (`focus.rs` is unmodified at HEAD):

- `focus.rs:99:38` and `focus.rs:227:35` → `crate::merge::ThroughFocus`. **The type lives in
  `through_focus.rs`, not `merge.rs`**, so the path is simply wrong; both files are mine.
- `noise.rs:24:10` → `NoiseModel::estimated`. **M48's file** — routing this rather than
  touching it.

I left all three: this task was scoped to `merge.rs` only, and two lines of the four-line fix
sit in someone else's file. Worth a follow-up, and worth noting that **the doc build is
currently the only check in the workspace that nothing else runs.**

---

## 5. Hand-offs

1. **For folding:** fact 822's two live sites are **closed**. The finding is that the
   conclusion did not survive (G15), not merely that the number was mislabelled.
2. **Missing measurement, named:** `n_eff` under regularised vs raw election at matched
   tolerance on real frames. Until it exists, the `Gate` doc stays ARGUED.
3. **G11 as a candidate discipline:** near-agreement between two measurements of different
   things is what makes them swappable. Fact 23's regularisation effect and fact 71's operator
   effect both run ~34.4% → ~1%, and that is why a ring number propagated to four sites as if
   it were Tenengrad's. *Check what the delta is a delta of, not just whether the endpoints
   look right.*
4. **`noise.rs:24` rustdoc link** → M48.
5. **Unchanged and untouched, as instructed:** question 180 (my `through_focus.rs:514` = 5.943
   vs M53's `merge_cmd.rs` = 1.815). I did not look at `merge_cmd.rs` except to read the
   already-repaired speckle caveat named in the brief.
