# Plugin architecture review — what measurement did to it

**Status: design critique, read-only. Every actionable item is folded into `SYNTHESIS.md`**
(§3.4, §3.4.1, §3.4.2, §4.1, fact 25, risks 8-10, §9, §10 questions 4 and 9-11). This document
keeps the two things that do not fit there: the **independent verification of the Cordis paper**,
and the record of what was checked and how.

The trigger was a suspicion, not a finding: each measurement round had reclassified another
"camera constant" as a per-stack quantity, and nobody had asked whether the owner's explicit
camera/lens pluggability requirement was still intact. It was not.

## 0. The two headline verdicts

**Wrong:** the `Stage`/`TileView` interface as specified **cannot express project rule 2**. The
strings `gather` and `materialis` return **zero matches** across all 118 KB of
`E-plugin-architecture.md`. E's `Stage::run(ctx, inputs: &[TileView], outputs: &mut [TileViewMut])`
is a materialised-buffer-in/buffer-out interface with an axis-aligned integer ROI, no warp and no
sampler. E and the hardware workstream ran in parallel; rule 2 came out of the latter; nobody
reconciled them. §9 then credited `TileView` as *"earned by gather-at-consumption"* — crediting the
type for a capability its own specification does not contain. Fixes in `SYNTHESIS.md` §3.4.1 B1.

**Right:** E §4.2's partition by *what a plugin must contribute* — *"Most of the plugin surface ...
is data plus a GPU kernel source. That needs no ABI at all."* This is the correct and non-obvious
insight and it dissolves the ABI and GPU problems simultaneously. It is why every blocking item
found here is still cheap today.

## 1. The Cordis paper — independently verified

The owner cited `https://github.com/cordiverse/paper/blob/main/paper.pdf` as the inspiration for
the plugin model. Given that this project's research corpus contained **three fabricated citations
and a fourth that reached a scheduled work item** (`A-prior-corpus.md`), the summary was not taken
on trust. **The PDF was fetched and read directly** — 88 pages, 2,140,840 bytes, byte-identical to
what `E-plugin-architecture.md` reports.

*A Programming Paradigm for Spatiotemporal Composability*, Shi / Zhang / Cui (Peking University,
DeepSeek-AI). It identifies two orthogonal dimensions of **dynamic** composition — **temporal**
(removing a component completely reverts its effects) and **spatial** (components declare, discover
and resolve dependencies) — lifts effect systems to *revertible effects* and coeffect systems to
*reactive coeffects*, unifies both into one context type, provides a calculus with metatheory, and
implements it in Cordis/TypeScript. Case study: Koishi, 4000+ community plugins over four years.

**Spot-checks against the PDF, all passed:** title, authors, page count and byte count; §1.2.1's
VSCode 87-of-100 and 7-of-100 figures; §6.1's acquisition/emission split; §6.4 explicitly naming
Rust traits, `impl` and procedural macros; §6.5's quadratic growth in integration components;
§6.6's nominal-linking / interface-drift / key-collision framing as an **open problem**; Theorem 73
is confluence; Corollary 62 is terminal recovery; §5.3's threats to validity verbatim (*"measuring
the abstraction's overhead and its effect on developer productivity against a baseline remains
future work"*); §5.1.1's *"an obligation on the component author rather than a property the runtime
verifies"*; and the p.25 commutative-vs-ordered-key passage verbatim.

**`E-plugin-architecture.md`'s reading is accurate** — materially the highest-integrity document in
the corpus — including its correction of the owner's own summary, and its observation that the
paper contains **no benchmarks**.

### 1.1 What transfers

1. **Commutative keys vs ordered chains (§3.3.2, p.25).** *"A key whose value is a table of entries
   added and removed independently is commutative ... A key whose value is an ordered chain is not,
   since a middleware inserted before another sees a different request."* SYNTHESIS §3.4's
   *"registries commute; the pixel chain does not"* is a correct and load-bearing application.
   **This is the best idea in the paper for this project.**
2. **The committed view — reactivate on change of *provider identity*, not presence.** Gives the
   right cache-invalidation trigger directly: swapping focus measure A for B must invalidate focus
   fields even though the key stayed bound.
3. **`(requires, provides, effect-with-inverse)`.** In Rust this is a closure plus `Drop`; §6.4
   names Rust as a language that supports it well. Free.
4. **§6.1's acquisition/emission boundary.** Underused here. A GPU allocation is acquisition and is
   revertible; a write to the output file is emission and is not. Cancellation and partial-output
   policy both live on that line.

### 1.2 What does not transfer, and why

- **Everything reactive.** The paper's entire motivation is **long-lived hosts** — a VSCode-style
  extension host, agent harnesses, a bot server. §1.2.3 argues *against* process-granularity
  temporal composability because *"each restart discards all process-local accumulated state ...
  and rebuilding it takes seconds to minutes."* **`strehl` is a batch CLI that exits**, and its
  restart cost is M1's measured **1.78 s cold decode**. *The paper's own cost argument says process
  granularity is the right answer here.* Hot reload, service brokers, rolling updates, isolation
  realms, read-time interception, cross-process bridging and sandboxing all solve problems a
  process that exits does not have. §9 was right to cut them; the reason is stronger than §9 stated.
- **Fine-grained decomposition.** §6.5's premise is *"components are lightweight."* Ours are not —
  fact 21 puts one stage at ~42% of total CPU. The granularity argument assumes a cost model that
  fails here, and §6.5's quadratic growth in integration components would be inherited for nothing.
- **`notify` is O(fibers x keys) per binding change.** Configuration granularity only, never an
  inner loop.
- **§6.6 dependency typing is unsolved *in the paper*.** Nominal linking, interface drift and key
  collision are surveyed; none is completed. Shipping out-of-tree plugins inherits an open research
  problem. Now `SYNTHESIS.md` risk 9.

### 1.3 One framing that was quietly wrong

§3.4 listed as a keeper the Cordis `try_activate -> Inactive{unmet}` shape, while §9 simultaneously
cut it (*"nothing can be unmet when everything is in-tree"*). §9 was right, and the deeper point is
that the mechanism is **reactive**: it exists so a component can go inactive and later reactivate
when a provider appears at run time. In a batch run the answer is decided once, before any pixel is
touched.

What this project actually wants is **plan-time resolution reported in the output's provenance** —
which the code already implements, and better: `Provenance::Fallback` in `noise.rs`/`profile.rs`,
whose test asserts that an unknown body falls back **visibly**. That is a stronger guarantee than
Cordis's, and it is local invention. §3.4 now credits it rather than the borrowed shape.

## 2. The justification audit

`E-plugin-architecture.md` §4.12 sets the project's own test, verbatim:

> *"The strongest argument for the whole architecture is not extensibility at all — it is that
> §4.5's declared capabilities and §4.9's caching are what let 24 GB of frames be scheduled and
> re-run cheaply. Those pay for themselves on day one with zero external contributors. Extensibility
> is the second-order benefit. **If the plugin system is ever justified on extensibility alone, it
> is over-engineered.**"*

Both internal legs are gone, killed by this project's own measurements:

| E's justification | What killed it |
| --- | --- |
| §4.5 capability/tiling — *"what decides whether 24 GB can be streamed in tiles or must be resident"* | §3.2 "the problem dissolves" (u16 CFA, 60 frames in VRAM with 8x headroom) and **fact 22: measured peak RSS 1.81-1.94 GB.** There is no 24 GB. Nothing needs tiling |
| §4.9 caching — *"changing the merge weighting must not invalidate the aligned frames ... alignment is the expensive part ... worth more to a user than the entire plugin system"* | **Rule 2 forbids materialising aligned frames**, so the artifact does not exist; and **fact 15** prices all alignment at 0.78-0.96 s for 60 frames, ~6% of budget |

**The conclusion is not "cut the plugin system", and the review that reached that conclusion was
applying the test out of context.** E's criterion was written to catch machinery built for nobody.
The owner asked for this explicitly: *"the stacking techniques, algos, etc. should all be plugins
too — recomposable and **easily contributable by others**."*

So extensibility is not a *failed* justification here. It is the **only** one that was ever
load-bearing, and the ruling that follows is sharper than "keep" or "cut":

- **Cut everything that existed to serve internal engineering** — `Resources`/`negotiate`/`Access`,
  the derivation cache, two-pass ROI negotiation, tiling machinery. Priced for a problem that
  measurement dissolved.
- **Judge everything that remains solely on contributor experience**, because that is now the
  entire return.

Which is why §3.4.1 B2 — delete the `build.rs`, compose WGSL at run time — is the highest-value
item in the whole review. It is precisely a contributor-experience decision, it costs nothing at
runtime, and it was never what E recommended.

## 3. Verdicts

| # | Item | Verdict | Where it landed |
| --- | --- | --- | --- |
| B1 | `TileView`/`Stage` cannot express rule 2; scalar `halo()` cannot express a warp-dependent, radially varying source ROI (~0 at centre, 39 plane px at corner) | **Blocking** | §3.4.1 B1, §9, §10 q10 |
| B2 | *"build-time WGSL splicing"* is a mistranslation of E's *"pipeline-build time"*, which in `wgpu` is a runtime call | **Blocking** | §3.4.1 B2, risk 8 (resolved) |
| B3 | The 3-7 px winner correlation **is** `focus.rs`'s own `OUTER_RADIUS: 3` support, so the 17x17 regulariser is tuned to one measure | **Blocking** | fact 25, §3.4.1 B3, §10 q9 |
| B4 | Rule 3 is documented, not enforced — a plugin handed raw pixels can always estimate its own sigma | **Blocking** | §3.4.1 B4 |
| N1 | Camera/lens "plugins" have collapsed to data, and no document said so | **Confirmed** | §3.4.2, `AGENTS.md` header |
| N2 | `breathing_scale_prior` — F1.13 says *"is justified and should be built"*, F ranks it payoff #2 at 5 stars — but **M3 §4 removed its only job** | **Retracted** | §4.1 |
| N3 | E §4.12's own over-engineering test now fires, and no document restated the conclusion | **Recorded, and reframed** | §2 above, §9 |
| N4 | Fact 21 is a scalar-CPU number constraining a GPU contribution format; experiment 3 unrun | **Open** | risk 10, §10 q11 |
| N5 | Cordis §6.6 dependency typing is an open problem inherited by out-of-tree plugins | **Recorded** | risk 9 |
| S1 | Pupil magnification `p` — one-hour bench task, ±38% consequence, the only gear constant neither derivable from EXIF nor fittable from a stack | **Owner action** | §10 q4 |
| S2 | Do not close the lens-plugin question before §10 q6 — a field-dependent defocus PSF is the one candidate that would earn code | **Gated** | §3.4.2, §10 q6 |
| S3 | Credit `Provenance::Fallback`, not Cordis's `Inactive{unmet}` | **Applied** | §3.4, §1.3 above |

## 4. Verified independently before acting

The critique made strong claims about documents and code. Three load-bearing ones were re-checked
against the sources rather than accepted:

- **E §F2.2 really does say *"selected by name at pipeline-build time"***, and E §4.2 really does
  describe contributed kernels as *"hot-reloadable for free (re-read a file, recompose the shader,
  rebuild the pipeline)"*, and §F2.2 really does specify caching SPIR-V *"by content hash ...
  amortised to zero across runs"*. **B2 confirmed.**
- **`crates/strehl-core/src/focus.rs` really is `INNER_RADIUS: 1` / `OUTER_RADIUS: 3`**, and
  `compute(&mut self, luma: &[f32], noise: &NoiseModel)` really does take a bare whole-plane slice —
  against E §4.11 item 2, *"Never pass a raw `&[f32]` where a `TileView` descriptor would do."*
  **B3 and the foreclosure claim confirmed; the don't-foreclose list has already been violated by
  the code implementing it.**
- **E §4.12 is verbatim as quoted.** **N3 confirmed** — and then reframed, because the test was
  being applied against a requirement the owner had stated explicitly.
