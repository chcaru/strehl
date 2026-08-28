# BUILD-SOFTGATE — the soft admission kernel is wired into the pyramid, the env channel now refuses a typo on both backends, and the depth-softening score is WITHDRAWN as confounded by width

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`F1, F2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `ec96973d` (`V-SOFTCHECK: verify the threshold
attribution at source; verdict UNCHANGED`). Working tree shared with roughly a
dozen live lanes. `crates/strehl-core/src/pyramid.rs` was **being written by
another lane throughout this milestone** and this lane did not commit it — see
§6, which is the most operationally important section in this file.

**Instruments:** `experiments/BUILD-SOFTGATE/render.ps1` (hermetic render
harness), `cmp.py` (pixel comparator), `soften.py` (depth-softening scorer,
which *imports* V-NEVERWORSE's own `spectrum()` rather than restating it).
Sources under `D:\personal\macro\` were read only; nothing was written there.

---

## 0. The commission

> Wire the soft kernel into the pyramid backend … The default must not change …
> Close the validation hole … Score the depth-softening fix, now that it can
> execute. **A null result is a perfectly good deliverable here.**

All three were done. The third is very nearly a null result and is reported as
one.

---

## 1. The premise, reproduced and then strengthened

The commission measured three cells on the pyramid backend. I measured five, on
`D:\personal\macro\coffee-bubbles -l 3 --srgb`, against binary `H` built from a
`git archive` of pristine `ec96973d` (SHA256 `15DE9909…`, 9 859 584 bytes):

| `STREHL_SOFT_GATE` | pyramid (SHIPS) | estimator `--photometric off` |
|---|---|---|
| unset | rc=0 `C9A93201…` | rc=0 `BBF38DD4…` |
| `on` | rc=0 `C9A93201…` | rc=101 panic |
| `zzznope` | rc=0 `C9A93201…` | rc=101 panic |
| **`gaussian`** | rc=0 `C9A93201…` | rc=0 **`00D8BFE3…`** |
| **`exponential`** | rc=0 `C9A93201…` | rc=0 **`F496B5A7…`** |

**F1 — MEASURED. On the shipping backend the variable was inert even when
spelled correctly.** The commission established that a *typo* was ignored. The
two bottom rows are the stronger statement: `gaussian` and `exponential` are
**valid kernel names that the code knows**, and on the backend that ships they
produced the same bytes as unset. This was not a validation gap with a working
feature behind it. The feature was unreachable.

**F2 — MEASURED. The estimator column is what makes F1 admissible.** Three
distinct hashes on an *identical command line* differing only in the environment
prove the harness can see a kernel change when one occurs. Without that column,
"one hash on all five pyramid arms" is equally consistent with a dead comparator.
Per the commission's method requirement 1, this is the planted difference, and it
is a natural one rather than a synthetic mutation.

---

## 2. What the kernel MEANS in the pyramid, which is not what it means in the estimator

This is the design question the commission asked to be answered explicitly.

The pyramid's shipped per-frame weight is `select_weight(excess, floor, p)`,
which is `r^p` for `r = excess / floor / SNR_REF`, and the merged coefficient is
`Σ w·L / Σ w`. Normalise against the band's own winner `b = argmax r`:

```
w_f / w_b = (r_f / r_b)^p = exp(-p · d_f),     d_f = ln r_b - ln r_f ≥ 0
```

`r_b^p` is a common positive factor and cancels in `num/den`.

**F3 — DERIVED, and then MEASURED (§4). The shipped pyramid selection already
IS an exponential kernel over the log-SNR deficit, at temperature `T = 1/p`.**
The sharpening ramp `MergeConfig::sharpen_per_octave` — near winner-take-all in
fine bands, blended in coarse — is therefore a *temperature schedule over scale*,
not a separate mechanism.

Three consequences drove every implementation choice:

1. **The gap axis is fixed by the identity, not chosen.** It is the log-SNR
   deficit against the band winner. The estimator measures a gap per *pixel* over
   a regularised focus field; the pyramid's equivalent is per *coefficient per
   band*. Porting the estimator's per-pixel form would have measured the wrong
   axis, which is what the commission warned against.
2. **The temperature is fixed at the shipped `1/p`.** Any other value confounds
   "different kernel shape" with "different exponent", and the exponent already
   has a knob.
3. **`SoftKernel::Exponential` is therefore a PLACEBO** — algebraically the
   shipped merge, differing only in float rounding. It is not a second treatment.
   It is the arm that separates *"the kernel changed the picture"* from *"the new
   two-pass plumbing changed the picture"*, which is the role `ROBUST_ENV`'s
   `ungated` arm plays for the estimator.

`SoftKernel::Gaussian` is the only treatment: `exp(-(p·d)²/2)` is **flatter than
shipped near `d = 0`** — frames within statistical noise of the winner are
admitted as the near-ties they are — and **sharper in the tail** — a frame that
genuinely loses is rejected harder than shipped rejects it.

**F4 — ARGUED. That is candidate-set control, which is what fact 1844 says depth
softening needs, and it is specifically not the remedy fact 1844 refuted.** Fact
1844 measured the confidence-dependent *exponent* removing 27.2 % of softening on
coffee-bubbles but **−44.6 %** on 112MSDCF, and concluded that "the premium must
be attacked directly through control of the candidate set". The Gaussian changes
*who is in the running*, not how steeply the winner is preferred. Whether that
argument survives measurement is §5, and it barely does.

### The cost, stated plainly

**F5 — DERIVED. The Gaussian is not one-pass streamable and the second decode
pass is unavoidable.** Expanding `-½p²(u_b - u_f)²` leaves a cross term
`p²·u_b·u_f` that couples the winner and the frame, so no fixed-size sufficient
statistic exists; the winner over all frames is not known until the last frame is
folded. The exponential *is* streamable, because `r_b^p` cancels — which is
exactly why it is what ships. The arm therefore pays a genuine extra decode:
MEASURED on 112MSDCF N=79, 56.3 s unset against 124.7 s gaussian. That is
acceptable **only** because the arm is off by default, and it is a real argument
against ever defaulting it without a cheaper formulation.

---

## 3. What was built

**In `crates/strehl-core/src/pyramid.rs` (NOT COMMITTED — see §6):**
`BandMerge` gains `soft: Option<SoftKernel>`, `ref_u` (per level, per
coefficient: the largest `ln r` any frame reached) and `ref_mode`, following the
existing `dmax` pattern of a buffer allocated only when a switch is on. `absorb`
max-merges `ref_u` — a maximum is associative and commutative, so it is exact
under any chunking, the same argument `lo`/`hi` already rely on. The weight loop
gains a `match self.soft` whose `None` arm is the shipped code verbatim.

**In `crates/strehl-cli/src/merge_cmd.rs` (COMMITTED):** `run_pyramid` resolves
`active_kernel()` once and, when it is `Some`, runs a reference pass before the
accumulating pass, printing a `soft gate :` banner reporting the kernel, the
reference-pass time, and the fraction of coefficients whose winner cleared its
noise floor. Plus `preflight_soft_kernel()` — §4.

**In `crates/strehl-cli/tests/byte-freeze.rs` (COMMITTED):** `STREHL_SOFT_GATE`
added to `RENDER_ENV`.

**F6 — MEASURED. `STREHL_SOFT_GATE` was missing from `RENDER_ENV`, and on this
list it is the first entry that can do something worse than move a hash: it can
abort the test.** Both rows in `byte-freezes.tsv` pass `--merge estimator`
explicitly, and on that backend the variable has always been live. An ambient
`gaussian` produces a differently-weighted fold no row records; an ambient typo
produces `panic!` at rc=101, which reads as a crashed harness rather than a dirty
shell. This is the third instance of the pattern that file's own `STREHL_FIX_CA`
and `STREHL_PHOTOMETRIC` comments predict in advance.

---

## 4. The validation hole, closed on both backends

`preflight_soft_kernel()` is called from `merge_cmd::run`, the single dispatch
shared by both backends, so one call site closes the hole for both. It follows
`align_cmd::preflight_ca_profile` exactly — ask once up front, throw the answer
away, cache nothing — and uses `anyhow`, the convention `MergeBackend::parse`
already uses for the flag channel, rather than inventing a third error style.

On the estimator this also converts the rc=101 panic into the ordinary rc=1
error, by arriving first. The `panic!` in `Estimator::new` is left in place as a
library-level invariant for direct API callers who bypass the CLI.

**F7 — MEASURED. The hole is closed, and the error now arrives before any frame
is decoded.** Against binary `S` (HEAD + this lane's change), on
`coffee-bubbles -l 3 --srgb --merge pyramid`:

| `STREHL_SOFT_GATE` | rc | time | SHA256 |
|---|---|---|---|
| unset | 0 | 4.7 s | `C9A93201…` |
| `off` | 0 | 3.4 s | `C9A93201…` |
| `zzznope` | **1** | **0.0 s** | — |
| `on` | **1** | **0.0 s** | — |
| `exponential` | 0 | 21.0 s | `D8376E35…` |
| `gaussian` | 0 | 28.1 s | `4EC3FB2B…` |

`on` is refused for the reason `kernel_from_setting` already documents: there are
two kernels and "yes" does not say which. Previously it exited 0 and rendered.
The 0.0 s is the preflight — the typo used to cost a full decode first (MEASURED:
3.4 s at `-l 3` on the estimator, and it scales with pass one).

---

## 5. Inertness, potency, placebo

**F8 — MEASURED. With the variable unset the wired binary is byte-identical to
the unwired one: 0 pixels differ of 98 898 048.** Binary `H` (pristine
`ec96973d`) against binary `S` (same tree plus this change), same subject, same
command line. `off` is identical too. The comparator was commissioned first:
self-vs-self reports IDENTICAL (it invents nothing) and a known-different pair
reports DIFFERENT at 96.286 % (it is not blind).

| comparison | pixels differing | mean DN | max DN |
|---|---|---|---|
| **INERTNESS** H unset vs S unset | **0** (0.000 %) | 0 | 0 |
| **INERTNESS** S unset vs S `off` | **0** (0.000 %) | 0 | 0 |
| **PLACEBO** S unset vs `exponential` | 28 754 (0.029 %) | 0.001 | 1091 |
| **TREATMENT** S unset vs `gaussian` | 95 224 579 (**96.286 %**) | 10.874 | 3956 |

**F9 — MEASURED. The placebo confirms the identity of F3 and clears the
plumbing.** `exponential` computes `exp(-p·d)` where shipped computes `r^p`;
these are the same number by F3, and the residue is float rounding — 0.029 % of
pixels against the treatment's 96.286 %, a factor of 3300 in affected count and
10 000 in mean magnitude. The second pass is therefore not what moves the
picture. It is not *nothing*: `maxDN=1091` on a handful of coefficients that
rounded across a visible threshold, which is why this is reported as a measured
floor rather than as zero.

**F10 — MEASURED. The kernel is potent on the shipping backend.** 96.286 % of
pixels move, mean 10.87 DN. The component that shipped switched off and
unreachable now executes on the default path and does something large.

---

## 6. The freeze that moved, and why it is not mine

`cargo test --release -p strehl-cli --test byte-freeze` **FAILS** on
`coffee-bean-20-gate2-sidecar`: expected `52517FF8…`, actual `E600A506…`, bytes
unchanged at 49 450 019. The commission's instruction was to stop and report
rather than re-baseline. **I have not touched `byte-freezes.tsv`.**

**F11 — MEASURED. The freeze was already moved at `ec96973d`, before this lane
changed anything.** I ran the same test in a second `git archive` of pristine
`ec96973d` with no modifications at all. It fails identically, producing the
**same** `actual` hash `E600A506…` bit-for-bit. The companion row
`coffee-bean-20-gate2-unaligned` HOLDS in both trees.

That control does double duty: because both trees produce the *identical* actual
hash, it is also a second independent inertness proof for F8 — on the **estimator**
backend, on a **different subject** (coffee-bean, 20 frames, sidecar alignment)
than the pyramid test used.

**O1 — RESOLVED, WITH A MECHANISM THAT PREDICTS THIS LANE'S OBSERVATION.** The
owner traced the cause rather than picking between two lanes' contradictory
reports, and the trace makes a testable prediction about *this* file's control.

Two lanes disagreed honestly because they measured different trees:
BUILD-OUTPUT ran the suite at `c7bb6282` (**08-27 01:04**) and saw both rows
hold; the `eps_r` re-fit is `393d7ca3` (**08-27 23:59**), ~23 h later.

**F11c — MEASURED. The mechanism predicts this lane's red control, and the
prediction holds.** `git merge-base --is-ancestor 393d7ca3 ec96973d` returns
**0** — the re-fit *is* an ancestor of this lane's pristine baseline
(`ec96973d`, 08-28 00:55). So the `git archive` tree §6 calls "pristine" already
carried the CA re-fit, and **must** be red on `-sidecar`. It was. That is a
mechanism predicting an independent measurement, which is worth more than either
alone.

`eps_r` is consumed by `OpticalProfile::compose`, whose **shipping** call sites
are exactly two, both in `align_cmd.rs` (1929, 2095) — **the lateral-CA
correction exists only on the alignment path.** Hence the rows behave as they
must:

| row | `env_align` | `compose` runs | outcome |
|---|---|---|---|
| `…-sidecar` | unset (alignment ON) | yes | **RED — the re-fit reaches it** |
| `…-unaligned` | `0` (alignment OFF) | no | **HOLDS** |

The registry is working exactly as designed: it caught a real change and its
paired control localised the cause to one code path.

**Three lanes now agree bit-for-bit** on all three hashes, having reached them by
different routes: expects `52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206`,
produces `E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2`,
`-unaligned` holds at `88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620`.
Matching `E600A506…` exactly also confirms this lane measured a tree **with** the
CA fix in it; a third distinct hash would have been a finding worth stopping for,
and there was none.

**F11b — MEASURED. The specificity control is GREEN under this lane's change.**
`coffee-bean-20-gate2-unaligned` holds at `88712017…` in **both** the pristine
tree and the tree carrying this lane's full change — including the unlanded
`pyramid.rs` hunk, which is strictly more than what was committed. That is the
row that would be this lane's fault if it moved, and the soft kernel lives in the
**merge**, not in alignment, so neither row should move and neither did. The one
`RENDER_ENV` addition cannot move a hash either: it makes the harness *clear*
`STREHL_SOFT_GATE`, and cleared equals unset equals the shipped selection.

**D1 — DISCIPLINE. Every arm of a comparison must come from one build, and this
lane hit that independently before it was told.** Binary `A`, built from the
shared working tree, renders `742A6331…` where pristine `ec96973d` renders
`C9A93201…` on an identical command line. It was discarded and every number in
this file is against `git archive HEAD` (§6). BUILD-CROP proved the general form
on a stronger case: a **coefficient-independent** CA-OFF arm, which must
reproduce bit-exactly, differed on 33 003 417 px at max 23 210 DN when
re-rendered across the night's churn. Ordering and ratios survive a shared tree;
**absolutes do not.** A pinned pre-change binary is not bookkeeping, it is the
only thing that makes "byte-identical to today" a measurement rather than a
guess.

### The collision — the operationally important part

**F12 — MEASURED. `crates/strehl-core/src/pyramid.rs` was under active
concurrent write by another lane for this entire milestone, and I did not commit
it.** Observed growing from 51+/0− to **519+/18−** across the session, with the
mtime advancing repeatedly, including *during* one of my builds. The other lane
is adding `MergeConfig::soft_significance`, `NU_SMOOTH`, `SIGMA_REL`,
`significance_floor(gate)` and a 4-argument `select_weight` — **inside the exact
weight loop this lane needed** — and its in-tree test asserts
`MergeConfig::default().soft_significance` is `true`, i.e. it is changing a
shipped default.

Two consequences:

- **My first baseline was contaminated and I discarded it.** Binary `A`, built
  from the shared working tree, renders `742A6331…` where pristine `ec96973d`
  renders `C9A93201…`. The shared tree's uncommitted state *already* moves
  pyramid default bytes. Every number in this file is against `git archive HEAD`
  for that reason. This is AGENTS.md rule 33's hazard arriving in a form the rule
  does not name: not a stale artifact, a stale *source*.
- **The `pyramid.rs` hunk is delivered as a validated patch, not landed.**
  `experiments/BUILD-SOFTGATE/pyramid-softgate.patch` (242 lines) applies to
  `ec96973d`. Everything in §5 was built and measured from it. Landing it into a
  file that has diverged by 519 lines would have required a hand-merge of another
  lane's in-flight work, which rule 42's reasoning forbids as surely as
  `git add -A` does.

I messaged both candidate owner lanes with the collision and received no reply.
**This should be checked against rules 40/41 as a possible double-dispatch:** the
other lane's `soft_significance` may be the same candidate-set fix this lane was
dispatched to unblock. I have not assumed either way.

---

## 7. Scoring depth softening — the near-null result

Subject `112MSDCF` at N=39 and N=79: the subject *and the depth pair* facts 1843
and 1844 both used, chosen so the number is directly comparable to the candidate
fact 1844 priced. Statistic: `n_0.30-0.35`, radially-averaged power at
0.30–0.35 cyc/px normalised by a 0.02–0.05 low band, **imported from
`experiments/V-NEVERWORSE/vn_ninv.py`** rather than restated, so this lane
measures with the instrument that produced the facts.

Commissioned before use: a planted blur takes the statistic to **0.0009×** and a
planted sharpening to **2.41×**. Both PASS.

| arm | N=39 | N=79 | Δ (79−39) | softening removed |
|---|---|---|---|---|
| unset (shipping) | 0.001029 | 0.000765 | −0.000264 | — |
| exponential (placebo) | 0.001029 | 0.000765 | −0.000264 | 0.0 % |
| **gaussian** | 0.001027 | 0.000771 | **−0.000256** | **+3.0 %** |

**F13 — MEASURED. Depth softening reproduces on this subject: every arm is
negative.** The deeper stack is softer, consistent with fact 1843.

**F14 — WITHDRAWN AS A CONTROLLED SCORE. The 3.0 % is measured but
uninterpretable, and fact 1918 is why.** The raw numbers stand and are
reproducible from the harness: Gaussian removes **3.0 %** of the depth softening
on 112MSDCF 39→79, placebo removes **0.0 %**. What does *not* stand is the
inference that the kernel is therefore 3.0 % better.

Lane V-DILUTE measured that `Gate::tolerance()` is shared across kernels, so a
hard-versus-soft comparison **at equal threshold is not a controlled comparison**:
on `109MSDCF` the same calibrated T admits mean n_eff **4.674** under the hard
gate against **19.295 of 22** under the Gaussian, with 79.2 % of the plane at
n_eff ≥ 20. Holding the threshold fixed varies kernel *shape* and effective
*width* together.

That fact is measured on the estimator's `Gate`, and this lane's wiring is on the
pyramid's `select_weight`, so the specific code path does not transfer. **The
mechanism transfers exactly, and §2's own derivation predicts it.** Swapping
`exp(−p·d)` for `exp(−½p²d²)` makes the kernel *flatter near d = 0* — that is
precisely the "admits statistical ties" property F4 argues is the whole point —
and a flatter kernel near the winner admits more frames. **Admitting more frames
trivially reduces noise and trivially increases blur**, which is the dilution
mechanism this project already knows about. This lane **never measured n_eff in
any arm**, so it cannot separate the two.

**The placebo does not rescue this, and it is important to say why.** The
exponential placebo is algebraically the shipped weight (F4), so it has the *same*
n_eff as shipping. It therefore controls for harness artefacts and for the wiring
itself — which is what F9 and F10 use it for, and there it is sound — but it
provides **no width control at all**, because the only arm whose width moved is
the one arm it is not matched to.

**What the next person must do to score this properly:** calibrate the Gaussian's
temperature so its **mean n_eff matches the shipped kernel's on the same
subject**, then compare at matched width. Scoring at equal `p` cannot answer the
question no matter how many subjects it is run on. This lane did not do that
calibration — it is a new experiment and the session was winding down — so per
instruction it reports **no soft-versus-hard score**, rather than a clean-looking
number that would have to be withdrawn later.

**F15 — MEASURED, AND IT SURVIVES THE F14 WITHDRAWAL, WEAKLY.** Fact 1844
measured the confidence-dependent exponent at **−44.6 %** on this exact subject
and depth pair — it made the deeper case *worse*. This kernel is **+3.0 %** on
the same measurement. The **sign** is the part that survives, because a width
confound of the F14 kind plausibly explains a small positive number but does not
explain away a **sign reversal** of that size. So the defensible claim is the
weak one: candidate-set control does not reproduce the backwards result that
disqualified exponent control. It is not evidence that it *works*.

**Read this as a null result, because that is now what it is.** The honest
summary: the mechanism argued in F4 survives contact with measurement in
*direction*, fails it in *magnitude*, and **is not yet controlled for width at
all**.

---

## 8. What would falsify this file

- **F8 (inertness)** dies if anyone renders any pyramid subject with the patch
  applied, the variable unset, and gets a hash differing from the unpatched
  binary. One counter-example kills it.
- **F3/F9 (the kernel identity)** dies if `exponential` is shown to move a render
  by materially more than float rounding — say >1 % of pixels — on any subject.
  It would mean the gap axis or the temperature is wrong, and F14 would then be
  measuring the plumbing.
- **F14** dies if the 3.0 % does not reproduce on a second subject or a second
  depth pair. **It has been measured exactly once, on one subject, at one depth
  pair, at one temperature.** This is the weakest claim in the file.
- **F11** dies if pristine `ec96973d` is shown to pass the freeze on another
  machine — which would make the move mine after all, or make it environmental.

## 9. What this lane did not verify

- **No second subject and no second depth pair for F14.** The 299-frame subjects
  were not scored; the commission's own warning that the premium grows with N
  means the 3.0 % could be larger or smaller there, and I do not know which.
- **The flat-region control for §7 failed and is not reported as evidence.** The
  automatic lowest-variance tile selected a region of variance 9.5 M — not flat.
  Rule 9's control is therefore **absent**, and F14 cannot fully exclude that the
  3.0 % is a gain or noise artefact rather than detail. The low-band
  normalisation is designed to remove common gain, which is an argument, not a
  measurement.
- **No visual verdict** (rule 48) was made on any depth-softened render.
- **The unlanded `pyramid.rs` patch has never been compiled inside the shared
  working tree**, only in the private `git archive` tree. It will need a
  hand-merge against the other lane's work and must be re-measured after it.
- I did not audit any other `STREHL_*` variable; that is V-ENVSURF's lane.

---

## 10. Landing checklist for the unlanded `pyramid.rs` hunk

**D2 — DISCIPLINE. Treat doc comments in this crate as unverified claims, and
grep the call sites before believing one.** `optics.rs:317` read "Nothing in this
crate calls `compose` yet" while two live call sites existed, and cost BUILD-CROP
an entire investigation into a wiring bug that did not exist (fixed at
`910e6bc0`). The scar is now in the source at `optics.rs:326-327`, which records
the false sentence and its date so the next reader sees the failure and not only
the fix. In this crate **a comment about reachability is a claim; the grep is the
evidence.**

**F16 — MEASURED. Call-site census of every symbol this lane's reachability
claims depend on**, counted crate-wide over `crates/**/*.rs`, excluding comment
lines. This is the evidence for those claims, and it is cheap to re-run:

| symbol | occurrences | where |
|---|---|---|
| `active_kernel` | **3** | def `merge.rs:681`; call `merge.rs:1455` (`Estimator::new`); call `merge_cmd.rs:2905` (**this lane's preflight**) |
| `preflight_soft_kernel` | **2** | def `merge_cmd.rs:2904`; **one** call `merge_cmd.rs:2917` (`merge_cmd::run`) |
| `enable_soft` | **0** | — |
| `SOFT_GATE_ENV` | 2 | def `merge.rs:530`; use `merge.rs:682` |

Read the three numbers that matter:

- **`active_kernel` went from one call site to two.** The premise of this
  milestone was that it had exactly one, inside `Estimator::new` — which the
  owner independently confirmed by the same grep. It now also runs on the
  dispatch shared by both backends. That is deliverable 2, and the count is the
  proof rather than the claim.
- **`preflight_soft_kernel` has exactly one call site**, which is the design: one
  site on `merge_cmd::run` refuses an unknown name on *both* backends. Two sites
  would mean the dispatch was missed and each arm patched separately.
- **`enable_soft` reads 0, and that number is load-bearing.** It is the grep
  named in that function's own SCOPE paragraph. While it reads 0 the pyramid
  backend *validates* the kernel and does not *apply* it, and the paragraph is
  current. **When it reads 1, the paragraph is stale and must go in that commit.**

A refinement worth recording because it is the same trap in miniature: counting
`compose` naively gives more than two. The **shipping** call sites are
`align_cmd.rs:1929` and `align_cmd.rs:2095` — which is what makes the CA re-fit
alignment-only and O1 above resolvable — but a raw grep also returns one in
`crates/strehl-cli/examples/build-demosaic-truth.rs`, an **example binary that
ships nothing**, plus the definition and twelve in `optics.rs`'s own tests. The
"exactly two" is a claim about shipping call sites and is correct as such; a
census that does not say which kind it counted invites the next misreading.

**The corollary is that this lane's own change creates two future instances, and
they must be fixed IN THE COMMIT THAT LANDS THE PATCH, not after:**

1. `crates/strehl-core/src/softgate.rs`, module header: *"Opt-in and not
   wired."* **True today, FALSE the moment the patch lands.**
2. `crates/strehl-core/src/merge.rs` ~1435, on `Estimator::new`: *"it is the
   only reason the soft kernel is reachable from `strehl stack` at all."*
   **True today, FALSE the moment the patch lands** — `run_pyramid` becomes the
   second route.

Neither was corrected in this milestone, deliberately: with the hunk unlanded,
editing them to say "wired" would have manufactured exactly the defect D2
describes. They are correct as they stand and become wrong on landing.

3. `merge_cmd::preflight_soft_kernel`'s doc carries an explicit SCOPE paragraph
   stating that the pyramid backend *validates* the kernel but does not *apply*
   it, naming the grep that falsifies it. Delete that paragraph when
   `enable_soft` stops reading **0** in the F16 census.

5. **`selection_inflation` keys on a count that stops being integral under a soft
   kernel, and landing the patch makes that live.** V-DILUTE measured it:
   `fold_inner` skips only at weight ≤ 0 and increments `n` afterwards, so `n`
   counts every frame that survives f32 underflow rather than every frame
   meaningfully admitted. The n_eff ≤ 1 population — *the population the
   correction exists to serve* — collapses from **3.936 % to 0.023 %**. The guard
   still runs and still returns success on a domain emptied underneath it, which
   is the failure mode this project keeps finding: a check that passes because its
   input vanished. **Do not fix it while landing the soft kernel** — it is
   mitigated twice over today, since `SELECTION_INFLATION` is 1.0 and both
   branches return 1.0 — but do not be surprised by it, and do not read its
   success as evidence.

**D3 — DISCIPLINE. Do not flip another lane's gate on the strength of a claim
about your own change; check whether your change actually made its premise
false.** V-DILUTE's gate **G2 asserts that `STREHL_SOFT_GATE` changes nothing on
the pyramid**, and this lane was asked to flip its polarity on the grounds that
the wiring made that false. **It did not, and G2 was left alone.** The reason is
F16: `enable_soft` greps to **0**, so the committed change validates the kernel
without applying it. Concretely:

| input | pyramid before | pyramid now | G2's assertion |
|---|---|---|---|
| `gaussian`, `exponential`, `off` | renders `C9A93201…` | renders `C9A93201…` | **still TRUE** |
| `zzznope` | rc=0, renders | **rc=1 in 0.0 s** | false, for this input only |

Flipping G2 wholesale would have asserted that the soft gate *changes pyramid
output*, which is **false for every valid kernel name** — planting a green-looking
lie in a commissioned harness owned by another lane. G2 is not in any file this
lane owns (`grep '\bG2\b'` over `experiments/BUILD-SOFTGATE/` and
`docs/research/BUILD-SOFTGATE.md` returns **nothing**). **When the `pyramid.rs`
hunk lands, G2's premise genuinely becomes false and it should be flipped then**
— gated on `enable_soft` reading 1, not on this report.
4. Re-measure everything in §5 after the hand-merge against the other lane's
   work. The patch was built and measured against `ec96973d` only, and that lane
   is changing a default in the same weight loop.

---

## 11. Re-certification of banking under the scoped instrument (fact 1962)

This lane previously certified its numbers "12 of 12 banked" using an unscoped
`git grep` hit count. **That certification is withdrawn.** It was measured blind:
invented numbers score the same order of magnitude as published ones, so a hit
count proves nothing. Re-run under
`experiments/ORCH-drift-check/verify_banked.ps1`, which scopes to one named
committed file and requires digit boundaries. **Controls read clean, 3 of 3
NOT-BANKED, on both runs below.**

| target file | BANKED | NOT-BANKED |
|---|---|---|
| `experiments/BUILD-SOFTGATE/results.tsv` | 11 of 12 | `742A6331` |
| `docs/research/BUILD-SOFTGATE.md` | 10 of 12 | `28754`, `98898048` |

**F17 — MEASURED. Two of the three misses are instrument false negatives caused
by this project's own house style, and other lanes will hit them.** The report
writes grouped digits, so `28 754` and `98 898 048` are stored with U+0020
between groups — verified by dumping the code points, not assumed. A
digit-bounded token search for `28754` cannot match `28 754`. The values are
present and correct; the instrument cannot see them. **Any lane certifying
against a prose report in `docs/research/` will get false NOT-BANKED for every
number above 9 999.** The third miss is not a defect: `742A6331` is genuinely
absent from `results.tsv` and present in the report, which is correct, because it
is a discarded contaminated hash and not a measured arm.

So the union across both committed files is 12 of 12 as tokens. **That union is
not the interesting number, and it is not what this section concludes.**

**F18 — MEASURED. EVIDENCE GONE: four of this lane's six SHA256 values exist
only as 8-character prefixes, and the full digests are unrecoverable.** Scanning
both committed files for 64-character hex tokens returns **three**, and all three
are byte-freeze registry hashes that belong to the registry and were
cross-confirmed with BUILD-CROP:

| digest | full 64 chars banked | status |
|---|---|---|
| `52517FF8AE…`, `88712017FE…`, `E600A506F6…` | **yes** | freeze rows, not this lane's renders |
| `C9A93201…` baseline | **no** | **EVIDENCE GONE** |
| `D8376E35…` exponential | **no** | **EVIDENCE GONE** |
| `4EC3FB2B…` gaussian | **no** | **EVIDENCE GONE** |
| `742A6331…` contaminated binary A | **no** | **EVIDENCE GONE** |

The full digests existed only in deleted scratch and in terminal output that no
longer exists. They are **not reconstructible**: scratch is gone, re-rendering is
forbidden here, and per fact 1886 a re-render on today's tree would not reproduce
them anyway. They are recorded as EVIDENCE GONE rather than reconstructed from
memory, because memory is not measurement.

**What survives this, and it is the part that mattered.** The load-bearing claim
of this lane is **inertness** — that the default did not move — and that claim was
never carried by a hash. It is a pixel count: **0 differing pixels of 98 898 048**,
banked in both files. A pixel-difference count is stronger evidence than a digest
comparison, because it survives the tree drift that makes absolutes meaningless.
The potency and placebo results are likewise pixel counts. **The withdrawn
depth-softening score is unaffected: it was already withdrawn in section 7 for a
different and more serious reason.**

**D4 — DISCIPLINE. Bank full digests or bank none.** An 8-character prefix is not
a verifiable hash: it cannot be checked against a re-render with any confidence,
and under a digit-boundary matcher a hex prefix is not even reliably
distinguishable from a longer digest, because the boundary is `[0-9]` and the
next character of a hash is often a letter. Truncating a digest for readability
in prose is fine **only if the full value is banked verbatim somewhere else in
the same commit.** This lane did not do that and cannot now.
