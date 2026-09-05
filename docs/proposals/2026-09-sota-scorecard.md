# strehl — pre-registered SOTA scorecard

**Status: SPEC / PRE-REGISTRATION v1.11 (2026-09-06).** The v1.0 metric, bar, and
control protocol was written before implementation lanes reported outcomes.
Subsequent revisions quarantine leaked evidence, classify captures before use, or
withdraw/tighten an instrument defeated by independent commissioning; each change is
recorded below. **Two axes have now been read: M8 FAIL and M12 FAIL.** The
competitive position remains **UNKNOWN**, because neither read axis carries a
comparator arm.

**Revision 1.11 — M12 read; an unratified reverse dependency on M11 removed:**
lane M139 completed the registered `N=33/105/299` x `1/2/4/8/16` matrix on a
guarded host (`0c089f96`). `M12-D` **PASSES** on all 15 fixed-worker cells and is
the first registered sub-property in this program to pass anything. `M12-S`,
absolute memory, and N-mod-4 all **FAIL**; only `peak_N299/peak_N33` is unread, at
`UNMEASURED_SAMPLING_COVERAGE`. Separately, lane M178 adjudicated the clause
requiring M12-S's 16-worker output to *"simultaneously pass M11"*. That clause
entered at `986c4653` (2026-09-02, *"Tighten scorecard anti-cheat constraints"*),
was never present in the governing proposal — whose M12 bars are *"memory <=6 GiB
warm; bytes invariant to worker count (D9a); the staircase gone"*
(`2026-08-sota-path.md:1981-1982`) — and was never claimed as proposal-authored by
the commit that introduced it. It is therefore an **unratified addition** and is
removed. **This removal lowers the scoreboard rather than raising it**: it converts
M12-S from a licence-withheld unknown into a measured FAIL. The legitimate
*forward* guard is untouched and still binds at §3.3: M11's claimed
production-speed output must be byte-identical across the worker ladder. What is
withdrawn is only the *reverse* dependency, which withheld a measured M12 result
behind an unpurchased licence without protecting anything.

**Revision 1.10 — razor ruling and request-register closure, with no bar or verdict
movement:** the razor remains barred from every positive M1/detail use, including an
aperture-ordering statistic that fits no edge locus. Its fixed subject geometry is
filtered differently by each arm and therefore does not cancel from an arbitrary
score. More decisively, M164's independent two-world construction proves that even
the exact expected aperture order and relative Airy attenuation can survive common
post-render sharpening; M166's audit also rejects cancellation in the actual
request-19 arms. The broad-boundary exception is M3-specific, not a general
no-registration exception. Razor captures may still reject a candidate in development,
but cannot tune, admit, qualify, or score one. A read-only filesystem and EXIF census
also closes the request register: all 32 ARW-bearing directories are now explicitly
classified. The protected three-arm fabric-weave holdout remains sealed; this revision
does not authorize a render or score.

**Revision 1.9 — Amendment 6 scope correction, with no bar or verdict movement:**
the output-only detail/noise limitation now retains its load-bearing qualification,
*“without an assumption or observation outside those outputs”*; the scorecard no
longer permits the three failed instruments to read as one theorem; capture is
identified as a precondition of the currently specified instrument route rather than an
alternative to it; and every `M1`-qualification reference is explicitly registry
shorthand for the current practical route, not a claim that M1 is the unique
mathematical anchor. A validated external model, prior, reference, or narrowly scoped
certified-target protocol may supply identifying information, but inherits its own
scope and still requires independent commissioning. M2 remains `UNMEASURED`. M8
remains `FAIL` on M8-R at `1.030569%` against `0.0000%`. No score or comparator
output is imported.

**Revision 1.8 — M166 bar definitions applied without manufacturing evidence:** M3
now binds its population, representation, per-capture and pooled reductions, literal
maximum, and M1-qualified comparator envelope. The retained M4 component now binds
its 250-tile denominator and same-output transfer veto. M9 records an exact downstream
certificate contract but remains **DEFINITION BLOCKED** on independent M1 acuity
truth. M11 now binds full-process QPC timing, six alternating-order scored sweeps, the
per-capture fastest-qualified envelope, actual reboot receipts, and the owner's
last-shutter epoch. M11 is well-defined but remains unmeasured: comparator
qualification is absent, and absolute timing is quarantined under `docs/STATUS.md`
§2.9.55 until a quiet-host reproduction. M10 is not repaired here; M163 repaired its
uncertainty instrument, but M166 found the remaining bar ill-defined and a separate
specification is pending. No score or comparator output is imported.

**Revision 1.7 — phase-0 decision-gate census registered:** all nine closed
implementation gates now have a verdict, number, independent-unit count, provenance,
and explicit scorecard effect. The two systems PASS verdicts are admitted only for
their narrow build/no-build questions; neither is an M11 product-path score. The
M1–M12 scoreboard remains 0 measured / 12 unmeasured.

**Revision 1.6 — underpowered S25 sharpening result superseded:** the earlier
24-seed `0.995819x` USM reading is replaced by the 64-site `1.028294x` result
against the unchanged 1% bar. This strengthens, but does not otherwise alter, M1's
withdrawal. It also preserves the independently successful PCHIP tone-witness
construction for future instruments.

**Revision 1.5 — M12 terms separated; existing evidence ruled out of protocol:**
fixed-worker reproducibility is now named **determinism**, while equality across
worker counts is named **scaling invariance**. Existing source admissions and a
reported unaligned N=20 1/4/8-worker sweep are strong diagnostic evidence that the
former holds and the latter fails, but they are not the registered N=33/105/299
native-product matrix. M12 therefore remains `UNMEASURED`; no host run was performed
for this revision.

**Revision 1.4 — defeated detail instrument withdrawn; M8 tightened before use:**
M1 now has no active statistic or bar because both registered outputs failed
independent commissioning. This revision also records which axes are scientifically
measurable now and splits M8 into per-frame resampler- and final-output hull
certificates. It registers no result and consumes no holdout.

**Revision 1.3 — fresh slide classified before outcomes:** the six
`high-res-calibration-slide-cpl` stacks arrived with input metadata only. They form one
657-frame physical-subject/session unit, assigned deliberately to development for the
flat-path geometry/resampling investigation. All six report IBIS on, so none is
admissible as an independent-repeat FRC arm. No render, metric, or visual verdict was
used for this assignment.

**Revision 1.2 — holdout quarantine:** the v1.1 baseline at `bc8f315a` reached no
metric because the geometry gate refused every arm. Separately, W1 rendered and swept
the calibration-grid-1 sw4 capture and disclosed outcomes before it was halted. The
entire same-subject calibration-grid session is therefore burned as future holdout
evidence; see §2.3 and quarantine commit `0c503d84`. No scorecard value changes from
`UNMEASURED`.

**Revision 1.1, still before any score render:** adds joint anti-cheat constraints,
caps every licensed detail claim at `0.25 cyc/px`, and makes decode/storage control
explicit in the timing protocol. It imports no phase-1 acceptance bar and no measured
quality result.

This document owns the definition and protocol, not a result. The first render of any
scored capture **under this protocol** seals v1.10; pre-existing unrelated masters are
not score outputs. A later change to an instrument, bar, eligibility rule, comparator
setting, capture, or aggregation rule requires a numbered revision and a fresh
holdout capture. Existing score outputs may then be used only for development.

## 0. What “SOTA” means here

The governing proposal does define it:

> “**SOTA = a pre-registered scorecard, versus named comparators, on axes with
> commissioned instruments.**”

That sentence and its requirement that every instrument first fail a relevant plant
and pass an untuned null are in `2026-08-sota-path.md` §1, lines 164–167. Its
end-state is conjunctive: detail at or beyond the best shipping comparator, strictly
lower noise, zero invented structure, bounded occlusion veil, calibrated per-pixel
acuity / effective sample count / physical depth, and competitive CPU speed
(`2026-08-sota-path.md` §1, lines 189–197). **Therefore, for strehl, SOTA means that
the shipping default satisfies every clause of that sentence on the common-merge
track against the licensed comparator set, while also emitting independently
calibrated trust and depth products. The owner's publication claim is satisfiable
only on that common-merge track.** Product-native results are separately publishable
end-to-end product evidence, but they cannot establish a competitive detail, noise,
clipping, or colour win and cannot satisfy, rescue, or alter any publication gate.
Competitive reports must distinguish the tracks and may not splice a value, setting,
or verdict from one into the other. SOTA is not an average, a weighted score, or
“wins most axes.”

> **AMENDMENT — publication scope corrected to the owner's sentence, and Helicon
> restored to "when obtainable".** This paragraph previously read *"passes every primary bar
> below against licensed Zerene Stacker and Helicon Focus ... and meeting the
> registered resource bars."* That was wrong in two independent ways, both of which
> made this document harder to satisfy than the plan it derives from.
>
> **(i) Twelve axes are not the owner's requirement.** An independent audit of all
> `58` gate-bearing blocks in this document against the full plan (M158,
> `docs/research/M158-scorecard-drift.md`, finding 13) established that the plan's
> printable end-state sentence names licensing instruments mapping to **seven** axes:
> **M1** (`D1: FRC + slant-edge`), **M2** (*"existing flat-ROI instrument"*), **M8**
> (*"hull census, stamped per file"*), **M3** (*"halo instrument at full reach"*),
> **M9** and **M10** (*"D2/D8/A5/C5"*), and **M11** (*"existing harness"*). I verified
> this directly against the sentence rather than accepting the audit's summary.
> **M4, M5, M6, M7 and M12 are named by no clause of it**, yet this document made all
> five fatal to publication. Their full-axis bars are retained below as **mandatory
> disclosures** and are marked `SCORECARD ADDITION`; **they are not independent
> prerequisites for the owner's claim**. The narrower M4 flat-power-plus-transfer-veto and M12
> cross-worker byte-identity components retained in §0.2 are anti-cheat protections
> for named axes, not reinstatement of the full M4 or M12 bars.
>
> **(ii) Helicon, when obtainable, was never mandatory.** The plan pins comparators as *"licensed Zerene
> (PMax **and** DMap ...), the fork rebuilt at its best-known build ..., Helicon if
> obtainable"*, and its purchase instruction names only Zerene, at *"Prosumer ($189)
> or Professional ($289)"*. Treating Helicon as required despite "when obtainable"
> made comparator blocker `(d)` fatal on eight axes for a product the owner never
> mandated. **The required comparator set is licensed Zerene Stacker PMax, licensed
> Zerene Stacker DMap, and a fresh rebuild of the fork's best-known retained source
> revision, commit-pinned before scoring, on the common-input TIFFs, with its
> executable hash frozen before rendering.** Helicon,
> when obtainable, is an additional comparator; its absence is recorded rather than
> fatal. The fork's omission from this document's comparator list was itself a drift
> (M158 finding 9), but M162 later established that the archived fork output cannot
> fill the required common-merge arm. It consumed `105` Lightroom-developed TIFFs,
> has no producing source revision or executable bound to it, and is not reproducible;
> the retained May 17 executable postdates the render by six days and is not its
> producer (`docs/research/M162-noise-regression.md`, "Correction to the premise"
> clause). That byte-pinned artifact is **HISTORICAL /
> `PRODUCT_NATIVE_END_TO_END` DIAGNOSTIC ONLY**, not a v1.10 scored arm. The first
> retained fork commit, `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, makes a fresh
> rebuild plausibly constructible but does not establish that it builds. Until a
> qualifying rebuild exists, every fork result cell is `UNMEASURED` under blocker
> `(d)`.
>
> **Superseded on the rebuild question, 2026-09-07 (lane M175).** The sentence
> above is retained as written because this amendment is a dated record. The
> rebuild prerequisite is now **closed**: M175 rebuilt commit
> `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6` twice on clean hosts to a
> byte-identical executable, SHA-256
> `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`, froze that
> hash and the settings before rendering, and passed §1.3 on the native-size
> eight-copy common-input tone sentinel — slope `1.0000000000000002`, intercept
> `-6.6597626500634704e-18`, maximum residual `2.220446049250313e-16`, strictly
> monotonic with no interior clipping. **Fork result cells nevertheless remain
> `UNMEASURED`**, now for a different reason: no scored common-input campaign
> output exists yet. **Blocker `(d)` itself is unmoved at run level while
> licensed Zerene PMax and DMap are absent**, because `:472-477` requires every
> named arm. The same distinction applies wherever this document says the
> rebuild or development transfer is absent.
>
> **What this amendment does not do.** It lowers no bar, retracts no `FAIL`, and makes
> no axis passable that was failing on its merits — M8 still reads `FAIL`, on M8-R at
> `1.030569%`. It removes prerequisites this document invented. Nothing else.

The proposal supplies several exact systems bars and the exact `0.0000%` hull bar.
It leaves the veil, acuity, colour, coverage, and several other acceptance numbers as
literal `[bar]` placeholders. Numbers below marked **SCORECARD ADDITION** are this
document’s proposed completions, not claims that the governing proposal already made.

### 0.1 Decision rule

1. The publication gates are exactly `M1`, `M2`, `M3`, `M8`, `M9`, `M10`, and
   `M11`, and every gate is evaluated only on the common-merge track. Every one is
   hard; no win compensates for a loss. `M4`, `M5`, `M6`, `M7`, and `M12` are
   mandatory disclosures, not independent publication gates: every one must still be
   measured on its registered track, published in the results table, and any miss
   stated prominently and without softening.
2. A verdict requires measurements for all twelve axes. When no owner gate, including
   its retained anti-cheat component, has failed, an uncommissioned checker, an
   invalid required-comparator arm, an under-powered required capture, or any other
   missing required measurement makes the run `UNMEASURED`; it is not a pass or a
   loss. An axis whose operative predicate itself is unresolved is
   `DEFINITION BLOCKED`, not merely `UNMEASURED`. A measured owner-gate failure
   retains `FAIL` precedence under §8. Helicon, when obtainable, must follow the same
   protocol, but its absence is recorded and is never a reason for `UNMEASURED`.
3. A comparative quality gate uses the **best qualifying comparator envelope**.
   The required set is exactly licensed Zerene Stacker PMax, licensed Zerene
   Stacker DMap, and a fresh fork rebuild from the best-known retained source
   revision, pinned by commit before scoring, with the built executable's hash frozen
   before rendering. Helicon Methods A, B, and C are added when obtainable. Every
   included mode uses its frozen setting with user post-processing disabled. “Best”
   is chosen in the comparator-favouring direction for each metric. The archived
   fork output is not an admissible common-merge arm.
4. Once a replacement M1 is admitted, a comparator mode may define a noise, artifact,
   speed, or memory envelope only if it passes the input/output transfer audit and
   retains at least `98%` of the highest replacement-M1 information score achieved by
   any registered mode on that capture. This stops a deliberately blurred fast/quiet
   mode from becoming the quality comparator. In v1.10 no mode can yet be
   quality-qualified for a claim that contains scene detail. A separately
   commissioned M2 protocol on input-certified featureless or deliberately defocused
   ground is exempt because its stated scope contains no photographic-detail claim;
   no such M2 instrument is licensed today.

   > **SCORECARD ADDITION — UNRATIFIED. This rule is authored here and is not
   > traceable to the owner's plan.** An independent audit verified that neither
   > this coupling nor the `98%` threshold appears anywhere in
   > `docs/proposals/2026-08-sota-path.md`; the nearest source requires only
   > comparators *"at matched output"* (`:1975-1978`), and Amendment 1 explicitly
   > preserves the noise, veil and invented-structure instruments as live
   > (`:2208-2210`). See `docs/research/M133-blocker-audit.md:1177,1190,1204,1209,1598`.
   >
   > **It is load-bearing.** This rule propagates blocker `(a)` beyond the axes
   > that intrinsically need a detail instrument. A mechanical re-derivation of
   > all sixteen blocker subsets (`experiments/M140-readiness/readiness.json`)
   > finds `(a)` is **intrinsic** only to M1, M5, M6 and M9, and **propagated by
   > this rule** to M2, M3, M4 and M11.
   >
   > **CORRECTION -- the price this block originally quoted was false.** It read
   > `2` axes becoming `6`, and `4` becoming `8`, under the headline *"Same
   > money, same shooting, four more axes."* **That claim is withdrawn.** An
   > independent audit (M146, `docs/research/M146-unlock-audit.md`, commit
   > `68ea3b95`) tested all four propagated axes against the archive and returned
   > `NEEDS_NEW_CAPTURE` or `BLOCKED_FOR_ANOTHER_REASON` for every one. The
   > propagation above is real but it is **not exclusive**: those axes reach the
   > detail instrument through clauses that are not rule 4. A later independent
   > audit found that the comparator-envelope clause and M11 computation also
   > required every quality axis. This reconciliation narrows both clauses to the
   > applicable owner-required gates and the retained §0.2 anti-cheat components.
   > Full M4, M5, M6, M7, and M12 results remain mandatory disclosures, but they do
   > not become owner gates through comparator qualification. **Cite these named
   > clauses, not line numbers**; repeated edits have already demonstrated that a
   > quotation-presence check can stay green while a line pointer rots.
   >
   > | cleared | rule 4 as written | rule 4 narrowed or removed |
   > |---|---|---|
   > | `b+d` — comparator bought | **2 axes** | **2 axes** — *no change* |
   > | `b+c+d` — comparator + capture | **4 axes** | **4 axes** — *no change* |
   >
   > **Narrowing rule 4 unlocks nothing today**, and with only `(b)` cleared all
   > scenarios leave exactly M8 and M12 scoreable. The rule remains `UNRATIFIED`
   > and it still changes what a passing claim *means*, so blocker `(a)`
   > assignments must not be presented as owner-mandated until the owner
   > ratifies, narrows or rejects it -- but no purchase or capture decision
   > should be made expecting to gain axes from it. The owner-facing version is
   > `docs/OWNER-ACTIONS.md` Ask 3.
5. Each capture must pass independently, and the pooled one-sided 95% confidence bar
   must also pass. Pooling may not rescue a failed capture.
6. All confidence intervals resample independent physical sites, not pixels:
   10,000 fixed-seed (`20260902`) hierarchical bootstrap draws by capture, then
   non-overlapping site. Rates use a Wilson one-sided 95% bound.
7. Frequency does not license itself. A pass/fail decision or public numerical detail
   claim above `0.25 cyc/native px` is admissible only when the scored subject has
   input-verified real contrast in that band and a pre-registered, independently
   commissioned instrument distinguishes real scene information from aliasing,
   interpolation, sharpening, and noise. Commissioning must include a planted
   **improvement** that the instrument rewards in the claimed direction, an untuned
   null it does not spuriously reward, and a planted degradation it penalizes. The
   instrument must state its physical optical/sampling ceiling and refuse above it.
   Existing FRC, slanted-edge, and single-image certificate readings remain
   `UNLICENSED_GT_0.25` unless separately admitted under this rule. No licensed
   high-frequency instrument exists in v1.10, so every current reading above
   `0.25 cyc/native px` remains `UNLICENSED_GT_0.25`. Absence of such an instrument
   makes only that band `UNMEASURED`; it does not permanently forbid a future C1 or
   C12 instrument from earning credit there.

This is not a relaxation in present effect: no licensed high-frequency instrument
exists, so no current above-`0.25 cyc/native px` reading changes status. It replaces
a permanent prohibition with hard, named admission conditions because a blanket ban
would also forbid strehl from claiming detail that a future commissioned instrument
can demonstrate it genuinely resolves.

**Amendment 6 — scope of the limitation and of `M1` references.** The operative
limitation is that rendered outputs do not by themselves identify whether reduced
high-frequency variation is removed noise or artifact, or removed scene signal,
**without an assumption or observation outside those outputs**. That does not prove
every conceivable no-reference metric impossible. An independently anchored
signal/transfer reference, a certified featureless-target protocol with an expressly
narrow claim, or a validated generative prior or constraint may supply the missing
identifying information; each route inherits the scope and failure modes of its
assumptions and must still survive independent commissioning.

The three instrument deaths remain distinct. D8 common-filter invariance is an
algebraic result; the band-power flat-null failure is an empirical defeat; only M2's
two-output ambiguity is the identifiability construction. Their common conclusion is
limited: no statistic can universally certify latent signal provenance when the same
observed pixels admit opposite ground-truth labels.

Throughout this scorecard, `M1-qualified`, `M1 truth`, and equivalent phrases are
registry shorthand for the **currently specified and physically actionable route**
to an independently anchored detail/transfer judgement. M1 is not the unique
mathematical anchor. A sufficiently
powered independent same-resolution reference could in principle normalize relative
transfer, but no such archive-qualified route is admitted today. This changes the
justification, not the schedule, bar, or current blocker cascade. Capture likewise
does not replace or “shoot around” an instrument: it supplies identifying information
and is a precondition of the currently specified instrument route.

### 0.2 Joint anti-cheat constraints

The seven owner-axis bars remain hard gates. The full M4, M5, M6, M7, and M12
axis bars are mandatory disclosures, not independent gates. The natural tradeoffs
below are scored and published as **joint tuples from the same output bytes and
settings**. No program may submit one render for one member and another render for
its opposite. The per-axis comparator envelope remains an additional conservative
bar; Pareto plots use each actual program/mode as one point and never splice modes
into a fictional point.

| Joint constraint | Cheat and opposed movement | Binding rule |
| --- | --- | --- |
| M2 flat/defocused-ground noise + retained M4 flat power/transfer + M8 hull; M1 detail when available | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | Publish every available value `(detail, eta, Q_flat, g, r, M8-R, M8-O)` from the same output bytes and settings. Each full axis retains its own bar and verdict; the tuple has no aggregate axis verdict. M1's absence blocks M1 and the full SOTA sentence, not a future independently commissioned M2 or the existing M8 result. A full-axis M4 or M8 failure must be published beside M2 but does not convert M2 to `FAIL` or `UNMEASURED`; an M2 pass licenses only its stated flat/defocused-ground noise claim and never excuses either failure or licenses detail. For the owner's overall gate, the same output must pass the retained M4 component: every capture and the pooled population have median `Q_flat<=1.00`, and every eligible site/channel passes `0.995<=g<=1.005` and `r<=0.005`. A miss fails that retained anti-cheat component within the M1/M2/M8 gate without turning full M4 into a gate. |
| M3 boundary integrity + local source coherence/width | Blur can hide a halo or veil while widening the edge and reducing agreement with the independently sharp source. | The same boundary render must pass M3's width and local `rho_edge>=0.90` bars; that local coherence is an M3 anti-blur component, not the full M5 axis. The build must also pass the independently commissioned M1 gate. |
| M6 clipping + §1.3 transfer + M5 highlight coherence | Darkening/tone compression avoids clipping; smoothing hides clipped texture. | Measure and publish the ramp, clipping, and highlight-coherence tuple from the same output. M5 and M6 remain mandatory disclosures; their misses produce `DISCLOSURE MISS`, not `FAIL`, when all seven owner gates pass, including their retained anti-cheat components. |
| M9 false certification + M9 coverage | Universal confidence overclaims; universal refusal obtains perfect precision by saying nothing. | M9 remains `DEFINITION_BLOCKED_M1_TRUTH`; no verdict exists until independent M1 acuity truth is admitted. Thereafter publish `(false_certification, true_band_coverage)` from one frozen map; both point and Wilson bars must pass, along with the interval, variance-decile, and exact-`n_eff` requirements. |
| M11 runtime + retained M12 cross-worker byte identity | Serial execution can buy determinism by abandoning the speed claim, while worker-dependent output can make the fast arm a different product. | The common-merge 16-worker output must meet M11. On the same common-merge input at fixed width, the complete TIFF file SHA-256 and canonical decoded-pixel SHA-256 must each be identical across 1, 2, 4, 8, and 16 workers. That cross-worker ladder is the only M12-derived publication-gate component; M12's product-native fixed-worker repeat, memory, N-scaling, and N-mod-4 bars remain mandatory disclosures. |

The retained M4 and M12 components protect the owner's own sentence from being
satisfied by a cheat; they are not extra independent goals. Dropping the flat-power or transfer
tell would allow a nominally hull-safe output to satisfy “zero invented structure”
while flat power balloons or the output destroys real in-band signal. Dropping
cross-worker byte identity would allow the timed
16-worker arm to be a different product from the slower arms. Conversely, retaining
the full M4 or M12 axes as prerequisites would contradict the seven-axis scope. The
narrow components above are therefore the only requirements carried into the owner
gates; every other M4 and M12 bar remains a mandatory disclosure.

This opposed-pair framing is not universal. M7 colour has an external target, M10
depth has physical/hidden truth, and M8 has an exact independently reconstructed
invariant; inventing an “opposite” for them would be weaker than their conventional
controls. Joint constraints supplement, rather than replace, each metric's planted
defect and untuned null.

## 1. Measurement contract

### 1.1 Freeze before outputs

Before any stacker runs, commit these files under `experiments/SCORECARD/`:

- `INPUT-MANIFEST.json`: source ARW path, size, timestamp, SHA-256, EXIF dump,
  decoder binary hash, and every linear-development setting;
- `SITE-MANIFEST.json`: input-derived tile, edge, patch, and exclusion coordinates;
- `RUN-MANIFEST.json`: hardware, OS, power plan, program hashes, licences, versions,
  complete settings, worker count, cache state, and output contract;
- synthetic plants and their hidden truth in separate files. The checker receives
  truth only after the renderer has finished.

Site selection may inspect the common inputs but never a stacker output. The site
manifest is then hashed and immutable.

### 1.2 Two frozen input contracts

Competitive evidence has two separately reported tracks. They answer different
questions, and neither may borrow a value, setting, or verdict from the other.

**Common-merge track — sole publication track.** Decode each ARW once with one
independently versioned LibRaw-based converter whose executable hash is frozen before
rendering. Apply sensor black/white levels and one frozen deterministic-pattern map
estimated from independent matching dark/flat captures; if no matching map exists,
M1 is `UNMEASURED`, while M9 remains `DEFINITION_BLOCKED_M1_TRUTH` with an additional
missing calibration input. Apply the recorded camera white balance and one camera matrix
once. Demosaic once. Write **uncompressed** 16-bit **linear ProPhoto RGB, D50** TIFFs
at the native active-image dimensions. Ignore every XMP sidecar. Disable
auto-brightening, exposure compensation, tone curves, contrast, clarity, texture,
sharpening, denoising, chromatic-aberration correction, lens correction, local
contrast, gamut compression, and output resize. Strip development tags from the
derivative, embed only the frozen linear ICC, provenance, and source hash, and hash
both the pixel payload and whole TIFF.

Licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, the fresh commit-pinned
best-known-source fork rebuild, and strehl must receive the exact same TIFF bytes on
this track. The fork's built-executable hash must be frozen before rendering. Helicon
Methods A, B, and C, when obtainable, must receive those bytes too. A strehl TIFF
adapter or a bit-for-bit hash identity at strehl's internal pre-merge linear-frame
boundary is required. Until one exists, the dependent publication gates remain
`UNMEASURED`; feeding TIFFs only to the comparators is forbidden.

The byte-pinned archived fork output is **HISTORICAL /
`PRODUCT_NATIVE_END_TO_END` DIAGNOSTIC ONLY** and cannot populate this track. It was
rendered from `105` Lightroom-developed TIFFs, has no producing source revision or
executable bound to it, and is not reproducible; the retained May 17 executable
postdates the render by six days and is not its producer. It also does not satisfy
the registered product-native contract below because neither its input lineage nor
its producing binary was frozen to that protocol.

**Product-native track — product evidence only.** Freeze one source-ARW manifest
before any output is viewed. Strehl receives those original ARWs through its shipping
native path. Each registered comparator receives the earliest linear input its frozen
native stack path supports, derived once from the same ARWs. No arm receives
per-subject development, retouching, post-sharpening, denoising, tone adjustment, or
output resizing. Freeze and publish every source hash, derivative hash, converter
hash, program version, setting, output-transfer result, and output hash.

The common-merge track isolates behaviour after a shared demosaic and is the **only**
track that can satisfy §0.1's publication gates or the owner's SOTA sentence. A
product-native result must be labelled `PRODUCT_NATIVE_END_TO_END`, reported honestly
and in full against every applicable unchanged bar, and may support only an explicitly
labelled end-to-end product statement. It cannot establish a competitive detail,
noise, clipping, or colour win and cannot satisfy, rescue, veto, or otherwise alter
any publication gate. Its deliberately different input representations must never be
described as byte-identical.

Every metric result must name its track. A common-merge result cannot veto or
substitute for a product-native result, and a product-native result cannot veto or
substitute for a common-merge result. No report may splice values, settings, or
verdicts across tracks into one fictional arm.

### 1.3 Output transfer and the tone sentinel

Each program must emit a native-size 16-bit linear TIFF. No output may be histogram
matched, auto-exposed, white-balanced, sharpened, denoised, resized, or tone-mapped
after stacking. Numerical metrics run in linear light before any display conversion.
Visual crops, when supplied, use one external colour transform, are cut 1:1 at
`<=400 px`, and are never resampled, per `AGENTS.md` rule 48 (lines 801–835).

The common input set includes eight identical copies of a 33-step neutral linear ramp
from `0.02` to `0.98`. For every channel, fit `y = ax + b` on steps 2–32. An arm is
invalid unless all of these hold:

- `0.995 <= a <= 1.005`;
- `|b| <= 0.001`;
- maximum absolute affine residual `<= 0.002`;
- RMS affine residual `<= 0.0005`;
- no interior step clips and ordering is strictly monotone.

The input audit additionally fails if any file or sidecar contains a non-zero
`Contrast2012`, `Sharpness`, `Clarity`, `Texture`, `LuminanceSmoothing`, tone-curve,
or equivalent development instruction. In the common-merge track, all programs
consume one hashed linear TIFF, so a one-arm `Contrast2012=+100` instruction changes
the shared input hash or fails the ramp. In the product-native track, the source ARWs,
comparator derivative, converter, and every development setting are frozen and
published separately; this section still forbids output-side tone or sharpening
asymmetry. Product-native evidence is explicitly end to end, does not claim pre-merge
sample identity, and cannot satisfy a publication gate.

### 1.4 Comparator settings

For licensed shipping products, use the newest generally available stable release on
the `RUN-MANIFEST.json` freeze date. The required fork arm must be a fresh rebuild
from the best-known retained source revision, pinned by commit before scoring. Freeze
every included comparator's version, binary hash, licence where applicable, and
screenshots/export of every relevant setting before the first scored output; do not
choose among releases, builds, or settings after viewing results.

- **Zerene Stacker:** licensed current shipping build; automatic PMax and automatic
  DMap; no retouching; output contrast/brightness/sharpening at neutral/off.
- **Fork — required common-merge rebuild:** select the best-known retained source
  revision and pin its commit before scoring, then freeze and record its source-tree
  hash, toolchain and dependency lock, compiler flags, final executable SHA-256, and
  complete settings manifest **before rendering**. The retained history begins at
  `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`; that proves a source pin exists, not
  that it builds. Select one build and one fixed setting preset before any scored
  output; no per-subject tuning or post-result rebuild is allowed.
- **Archived fork output — historical / product-native only:** the byte-pinned
  artifact used `105` Lightroom-developed TIFFs, has no producing binary or source
  revision bound to the render, and is not reproducible. The retained May 17
  executable postdates the render by six days and is not its producer. It is a
  diagnostic, not a common-merge or current product-native scorecard arm; unrelated
  repository histories also prohibit a cross-project bisect.
- **Helicon Focus, when obtainable:** licensed current shipping build; Methods A, B,
  and C at factory defaults; no retouching; built-in post-sharpening, denoising, and
  auto-adjustment neutral/off.
- **strehl:** the shipping default at the scored commit; no per-subject environment
  overrides or experimental quality flags.

If a named control is unavailable in a particular version, record the exact UI and
exclude that mode. If any required arm — Zerene PMax, Zerene DMap, or the fresh
commit-pinned best-known-source fork rebuild — cannot produce a linear output that
passes §1.3, the named-comparator requirement is unmet and the dependent comparative
axes remain `UNMEASURED`; the run-level verdict follows §8. Until the fork is rebuilt
from its pinned best-known retained source revision, its executable hash is frozen
before rendering, and it consumes the exact common-input TIFF bytes, the fork arm is
explicitly `UNMEASURED` under blocker `(d)`.

> **SCORECARD ADDITION — UNRATIFIED. The universal conjunction in the preceding
> paragraph is authored here and is not traceable to the owner's plan.** An
> independent audit (lane M169, commit `7ae6dac3`,
> `docs/research/M169-comparator-requirement-audit.md`) re-derived the plan's
> comparator requirement from source. The plan pins the same three *names*, but
> assigns them **by claim** rather than as an atomic portfolio: PMax and DMap to
> the detail clause, DMap separately as *"A5's true comparator"*, and the fork
> beside the honest speed quote (`2026-08-sota-path.md:1535-1539`). The plan's own
> axis table (`:172-181`) gives each axis a claim-specific blocker — noise reads
> *"Nothing — quotable now"* (`:174`) and speed/memory reads *"Hold the line (D5;
> D9 buys back the worker-cap tax first)"* (`:181`) — while only fine detail names
> *"a licensed comparator"* (`:178`). **No plan sentence makes failure of one arm
> fatal to an axis that does not name it.** This is the second unratified addition
> found in this document; rule 3's conjunction and rule 4's `98%` M1 gate were
> authored here by different routes.
>
> **This annotation flags the clause. It does not suspend it.** The clause remains
> in force, and no axis has been or will be scored under a relaxed reading before
> the owner rules. The orchestrator declines to loosen a gate that is presently
> constraining its own scoreboard: a pre-registered scorecard edited whenever it is
> inconvenient is worth nothing, and the ratification belongs to the plan's author.
> The decision is recorded in `docs/OWNER-ACTIONS.md`. Note that under the plan
> `(d)` remains a genuine owner purchase regardless of how this is ratified: *"An
> open-source stacker is a useful foreign arm and repairs a real provenance defect,
> but it clears **no** blocker."* (`2026-08-sota-path.md:2302-2309`).
Helicon, when obtainable, must pass the same transfer rule; when it is unobtainable,
record that absence and continue. If an obtainable Helicon arm is invalid, record and
exclude it rather than changing the required-comparator verdict. No expert hand
retouch is admitted because it has no reproducible operating point.

For higher-is-better metrics, the comparator envelope is the maximum qualifying value
over all registered modes. For lower-is-better metrics it is the minimum. For speed it
is the fastest mode that passes `M1`, `M2`, `M3`, and `M8` plus the retained M4
flat-power and transfer-veto anti-cheat component at identical output conditions.
`M9` and `M10` are
strehl output obligations, not comparator capabilities. This is intentionally
conservative toward strehl without making a disclosure axis an independent gate.

### 1.5 Geometry and exclusions

- Outputs must retain native scale. Resize is a hard invalidation.
- Crops are fixed from the common-input overlap before outputs exist. Retained field of
  view must be `>=99.0%` of that overlap.
- Translation may be removed analytically as a Fourier phase ramp. Frequency metrics
  may not resample an output.
- A similarity fit from input-derived landmarks must have scale disagreement
  `<=0.10%`, rotation disagreement `<=0.02 deg`, and non-translation residual
  `<=0.10 output px RMS`; otherwise that capture/arm is `UNMEASURED`.
- At least `80%` of pre-registered sites and at least the metric-specific minimum must
  survive identically in every arm. Differential site attrition over `2 percentage
  points` invalidates the comparison.

### 1.6 Commissioning before scoring

`AGENTS.md` requires a flat control beside every sharpness metric (rule 9, lines
185–190), the fooling direction beside every metric (rule 18, lines 257–266), an input
that can make each gate fail (rule 20, lines 267–284), and an independently obtained
term rather than subject/object identity (rule 35, lines 457–462). Accordingly:

1. Each checker must fail its metric-specific positive plant at the registered
   sensitivity and pass an untuned null.
2. The checker may consume common inputs, external calibration data, and final
   outputs. It may not import strehl’s focus map, weights, contributor mask, noise
   constants, depth estimate, or certificate to construct its own answer.
3. The “all red” omnibus plant applies pre-sensor blur, added shot/read noise, a 6%
   edge halo and veil, a 32-px selector patchwork, a three-frame focus gap, 1%
   highlight clipping, a channel hue rotation, 6-sigma out-of-hull samples, an
   overconfident certificate, permuted depth, a 60-second timed delay, and a 7-GiB
   allocation. Every applicable gate must fail.
4. A failed commissioning result voids the metric. It may not be repaired against the
   scored captures under v1.10.

## 2. Frozen capture set

### 2.1 Read-only inventory

The full trees were enumerated with `Get-ChildItem -Force` on 2026-09-02 and were
never written:

- `D:\personal\macro`: `10,067` files, `9,852` ARWs, `429.352 GiB`;
- `D:\personal\macro\requests`: `3,261` files, `3,251` ARWs, `115.321 GiB`.

Those are the historical pre-slide totals. A v1.10 request-only re-audit enumerated
`3,918` files, `3,908` ARWs, `139.682 GiB`, and exactly `32` ARW-bearing directories
under `D:\personal\macro\requests`. ExifTool `13.58` read the headers of all `3,908`
ARWs; the path/size/mtime tree fingerprint was identical before and after. The
machine-readable census is
`experiments/M160-razor-ruling/request-audit.json`.

All input derivatives, manifests, and outputs must be written beneath
`experiments/SCORECARD/`, never to either capture tree.

### 2.2 Scored and control captures

**Literal rule:** only a row whose evidence class begins `HOLDOUT` is holdout. No
other wording implies holdout status.

| Capture | Verified ARWs / metadata | Evidence class | Registered role |
| --- | ---: | --- | --- |
| `requests\30-calibration-grid\calibration-grid-1-sw1-cpl` | 91; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former dense checker reference. Same subject/session as leaked sw4; cannot score M1/M5/M9. |
| `requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | W1 swept `k` and observed outcomes; quarantine `0c503d84`. |
| `requests\30-calibration-grid\calibration-grid-2-sw4-cpl` | 46; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former scored repeat B; collateral same-subject/session burn. |
| `requests\30-calibration-grid\calibration-grid-1-sw10-cpl` | 23; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former sparse-step arm A; collateral same-subject/session burn. |
| `requests\30-calibration-grid\calibration-grid-2-sw10-cpl` | 27; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former sparse-step arm B; collateral same-subject/session burn. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et6s-sw4-cpl` | 65; ISO 100, 6 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` resampling diagnostic; longest-exposure SNR rung. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et2.5s-sw4-cpl` | 61; ISO 100, 2.5 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` diagnostic; middle SNR rung. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl` | 60; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` diagnostic; exposure-matched control for the tilted block. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw4-cpl` | 182; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Dense controlled-tilt M5/M10 commissioning and geometry diagnostic. Never an FRC repeat or checker reference for a score. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw10-cpl` | 92; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Sparse-step controlled-tilt M5 commissioning. Distinct geometry, not a repeat of the all-axis stack and never an FRC arm. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\very-tilted-all-axis-sw10-cpl` | 197; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Sparse-step all-axis M5/M10 commissioning. Distinct geometry, not a repeat of tilted-sw10 and never an FRC arm. |
| `requests\7-aperture-pairs\fabric-weave-f5.6-sw5-cpl` | 210; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Natural oriented high-frequency and colour-seam stress. |
| `requests\7-aperture-pairs\fabric-weave-f8-sw5-cpl` | 150; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Aperture robustness. |
| `requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl` | 109; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Aperture robustness / diffraction control. |
| `requests\7-aperture-pairs\fabric-weave-f14-sw5-cpl` | 83; ISO 100, 1.3 s | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | M129 aperture-spectrum outcome already read; development evidence only and never an M1 scored arm. |
| `requests\7-aperture-pairs\fabric-weave-f18-sw5-cpl` | 71; ISO 100, 1.3 s | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | M129 aperture-spectrum outcome already read; development evidence only and never an M1 scored arm. |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl` | 120 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Outcome already read by M-PHASE0-CURV (`:167`, `+0.316961 [+0.078558,+0.543411]`, DETECTED-SMALL). Was M5 depth coverage and conditional M10 slope; M10 now needs a fresh metrology-backed unit. |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f8-sw7-cpl` | 85 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Outcome already read by M-PHASE0-CURV (`:168`, `+0.047308 [-0.265968,+0.261226]`, UNRESOLVED). |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f11-sw7-cpl` | 65 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Outcome already read by M-PHASE0-CURV (`:169`) *and* M-PHASE0-LCA (`:125,181`, the "primary ruler"). |
| `requests\12-bee-iso-var-no-bracket-32-repeat-diff-light` | 576 total | **HOLDOUT — QUALITY** | Independent repeated exposures for M1/M2/M9. Bright ISO 100 is `DSC00328.ARW`–`DSC00359.ARW`; second-light ISO 100 is `DSC00584.ARW`–`DSC00615.ARW`, 32 each, 1.6 s, f/5.6. |
| `requests\10-paper-iso-var` | 110 total | **CONTROL — NOT HOLDOUT** | Flat/noise transfer control. ISO 100, 1/8 s is `DSC00245.ARW`–`DSC00249.ARW`. The actual EXIF census includes ISO 250 although the README list omits it. |
| `requests\6-11-extended-dark-frames` | 506 | **CONTROL — NOT HOLDOUT** | Independent temporal-noise and fixed-pattern floor; never an image-quality subject. |
| `requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f5.6-cpl` | 67; ISO 100, 3.2 s, f/5.6 | **CONTROL — NOT HOLDOUT** | Frozen M3 broad-boundary control and M128 development material. It may reject a detail candidate but can never supply positive M1 evidence. |
| `requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f8-cpl` | 50; ISO 100, 3.2 s, f/8 | **CONTROL — NOT HOLDOUT** | M128-consumed aperture/edge development. Negative-only for detail; never positive M1 evidence. |
| `requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f11-cpl` | 40; ISO 100, 3.2 s, f/11 | **CONTROL — NOT HOLDOUT** | M128-consumed aperture/edge development. Negative-only for detail; never positive M1 evidence. |
| `requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f5.6-cpl` | 279; ISO 100, 2.5 s, f/5.6 | **CONTROL — NOT HOLDOUT** | Razor aperture-ordering/detail use refused; broad-boundary development or negative-only candidate challenge only. |
| `requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f8-cpl` | 210; ISO 100, 2.5 s, f/8 | **CONTROL — NOT HOLDOUT** | Razor aperture-ordering/detail use refused; broad-boundary development or negative-only candidate challenge only. |
| `requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f11-cpl` | 143; ISO 100, 2.5 s, f/11 | **CONTROL — NOT HOLDOUT** | Razor aperture-ordering/detail use refused; broad-boundary development or negative-only candidate challenge only. |
| `requests\misc-diagnostic\razor-flat-vertical-slightly-tilted-sw1-cpl` | 51; ISO 100, 10 s, f/11 | **DEVELOPMENT — NOT HOLDOUT** | M128 focus-step systematic control. The razor prohibition applies; never positive M1 evidence. |
| `duck-tape-side-layers-cpl` | 197 | **HOLDOUT — QUALITY** | Thin fibres crossing textured ground; occlusion/ghost stress. |
| `chia-seeds-cpl` | 130 | **HOLDOUT — QUALITY** | Deep-crevice broad-veil specimen. |
| `flower-bud-with-background-fern-cpl` | 299 | **HOLDOUT — QUALITY** | Dense multi-layer occlusion and coverage stress. |
| `coffee-bubbles` | 19 | **DEVELOPMENT — NOT HOLDOUT** | High-ISO patchwork/mottle commissioning subject. |
| `medication-pill-cpl` | 146 | **HOLDOUT — QUALITY** | Low-contrast powder/focus-election stress. |
| `foam` | 100 | **HOLDOUT — QUALITY** | Specular, coloured, near-rail highlight stress. |
| `requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso100-sw4-cpl` | 30 | **HOLDOUT — QUALITY** | Reflective neutral metal, fine scratches, clipping/colour-seam stress. |
| `requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso200-sw4-cpl` | 27; ISO 200, 13 s, f/5.6 | **CONTROL — NOT HOLDOUT** | ISO/noise and frame-count sensitivity control; never substitutes for the protected ISO-100 score arm. |
| `requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso400-sw4-cpl` | 27; ISO 400, 13 s, f/5.6 | **CONTROL — NOT HOLDOUT** | ISO/noise and frame-count sensitivity control; never substitutes for the protected ISO-100 score arm. |
| `maldon-sea-salt-cpl` | 255 | **HOLDOUT — QUALITY** | Translucent facets and recoverable highlights. |
| `highly-angled-ruler-mm-cpl` | 299 | **HOLDOUT — QUALITY** | Neutral edges and lateral-colour stress. |
| `bee-1-cpl` | 299, `DSC00001.ARW`–`DSC00299.ARW` | **HOLDOUT — PERFORMANCE** | 33 MP wall-clock and memory master. First 100 frames are the live-latency arm. |
| `coffee-bean` | 105 ARWs, `DSC00016.ARW`–`DSC00120.ARW` | **FIXED HISTORICAL BENCHMARK — NOT HOLDOUT** | Comparator continuity and medium-N speed; never used to recover the retracted detail claim. |
| `113MSDCF` | 63 ARWs, `DSC00001.ARW`–`DSC00063.ARW` | **HISTORICAL CONTROL — NOT HOLDOUT** | `Contrast2012` regression sentinel only; not a primary acuity subject. |

**Ruling — the razor prohibition binds every positive M1/detail use.** It is not
limited to statistics that fit a line, estimate `f_c`, or self-register the edge.
It therefore bars the proposed three-aperture ordering statistic from using any razor
capture to tune, admit, qualify, or score itself. A razor result may only reject a
candidate in development. The existing broad-boundary exception is specific to M3:
there the edge is an artifact boundary, not a straightness-dependent resolution truth.

The common-subject argument does not clear the bar. For arm `N`, the observation is
`I_N = S * h_N + epsilon_N`; the fixed subject `S` remains inside the arm-specific
convolution and therefore does not cancel from an arbitrary scalar `q(I_N)`. The
ragged locus can be attenuated and reweighted differently by the three optical,
sampling, and stack operators. Without a pre-registered proof that `q` is monotone
under those actual operators for every allowed fixed locus, a subject-induced
ordering or inversion cannot be excluded.

M166's read-only audit of all `789` request-19 headers and retained M128 evidence
rejects cancellation on this capture directly (`4dc266e7`). Common-coordinate locus
RMS is `1.77638/1.64144/1.91766 green px` at f/5.6/f/8/f/11, decomposing into
`1.63194 px` shared and `0.70697 px` aperture-specific components; the independent
two-green-plane registration component also spreads by `33%`. The arms cover unequal
focus spans, and their frame/photon budgets are aligned with the desired order.
ExifTool already folds the 2× teleconverter into the reported focal length and
f-number, so doubling those f-numbers again does not establish that all three complete
imaging operators are diffraction-ordered.

The ruling does not depend on that unresolved possibility. M164's independent
counterexample at `77fbc946` grants the strongest premise — true diffraction transfer
strictly decreases from f/5.6 to f/8 to f/11 — and constructs two worlds with
identical rendered triplets: `Y_i = K H_i X = H_i K X`. One world contains common
post-render sharpening; the other contains a sharper latent scene. Both recover the
correct aperture order, common USM raises every score by `1.409469446×`, the relative
score vector matches the predicted Airy attenuation to `1.11e-15`, and the arrays
match exactly. Aperture order is therefore a necessary screen and useful model check,
not a truth reference that identifies resolved-detail provenance.

M128 independently supplies the capture-specific warning: straight-line recovery
passes at `0.02` and fails at `0.03 green px RMS`, while this razor measures
`1.23 green px RMS` (`54×` over), and per-column registration biases `f_c` by
`+91.05%` even at zero wander. Its required straight-edge truth target remains a
lithographic chrome-on-glass edge, not a razor.

This is also a precedent rule: “the defect is common across arms” never overrides a
capture's claim-specific ineligibility. A future monotonicity proof would require a
new pre-results scorecard amendment; it cannot be inferred from a favourable order.
The three registered fabric-weave holdouts remain sealed, and this ruling does not
authorize their render, measurement, or score.

**Request-register closure.** The v1.10 audit found ten previously unregistered
ARW-bearing directories: five additional `19-razor-edge` arms, fabric f/14 and f/18,
battery ISO 200 and 400, and the vertical sw1 razor. All ten now have explicit rows
above. The current request tree contains `32/32` registered ARW-bearing directories;
no scorecard request path is absent on disk.

### 2.3 Holdout units and burn log

The holdout unit is **subject plus uninterrupted capture session**, not a directory or
step width. Rendering, tuning, or reading an outcome on any member burns every member
of that unit. A `HOLDOUT` capture may be decoded to build the frozen common input and
input-only site manifest, but no output, metric, visual verdict, parameter sweep, or
code-acceptance decision may be seen before the registered score run.

All five `30-calibration-grid` stacks are one unit. Its README says subject, light,
aperture, ISO, and composition were constant and only step width changed. EXIF places
the five stacks contiguously on 2026-09-01 from 20:57:42 through 21:09:06. There is no
other calibration-grid capture group in `D:\personal\macro`.

W1 swept `k=0.00:0.05:8.00` (161 values) on
`calibration-grid-1-sw4-cpl` and read real-stack sentinel outcomes before halt:
detail `1.063350`, flat power `1.329831`. Commit `0c503d84` quarantines that pilot.
Therefore sw1, both sw4 stacks, and both sw10 stacks are all burned. The later W1
targets `flat-on-ruler-cpl`, `coffee-bubbles`, and `113MSDCF` do not extend the burn:
none is labelled holdout here.

The fresh high-resolution slide is conservatively one **657-frame unit** spanning
20:13:04–21:01:58. The 16 min 45 s gap is a target reconfiguration inside the same
evening's capture session, not independent evidence: the physical slide, camera,
lens/teleconverter, ISO, and aperture remain the same. Exposure, step width,
directory, and flat/tilted geometry do not split a subject into six holdouts.
Touching any member would therefore burn all six.

All six carry `ImageStabilization: On`. Registration-based M5 development is allowed,
but repeat-pair FRC/M9 truth use is forbidden. The entire unit is deliberately spent
on development: constant depth makes the flat block the cleaner identity/resampling
test for the known `cover=scale` geometry defect, its exposure changes make an SNR
ladder rather than matched repeats, and reserving the tilted views while tuning on the
same slide would create target leakage.

**Axis consequence:** these captures advance M5 coverage-instrument development and
M10 planarity/order commissioning, but they close no holdout gap. M1 keeps only its
same-focus bee sentinel; M5 retains ruler/natural holdouts but still lacks its
replacement controlled-slide holdout; M9 retains bee repeats but lacks independent
depth-stack truth.

**Even after an M1 replacement exists, M1, M5, and M9 cannot pass v1.10** until a
fresh untouched subject/session supplies,
at identical subject geometry, exposure, ISO, aperture, and focal length with
**IBIS off**:

1. one dense checker-only reference pass;
2. two independent sw4 scored passes; and
3. two independent sw10 sparse-step passes.

A single repeated pair at only one step width does not close both registered arms.

### 2.4 Missing or insufficient truth captures

No enumerated capture is a traceable colour target spanning the focus sweep. `foam`,
fabric, metal, and neutral paper can reveal seams or casts but cannot supply true
CIELAB values. M7 is therefore registered now but cannot be scored until a tilted
ColorChecker Classic or Digital SG, grey card, illuminant measurement, and darks are
captured. Natural-object agreement is not colour fidelity.

The tilted ruler is **burned, not holdout**: M-PHASE0-CURV read outcomes from all
three apertures (`:167-169`) and M-PHASE0-LCA from the f/11 stack (`:125,181`),
before this scorecard labelled them holdout. Separately, its README records the
angle only as “approximately 10.26 deg”, derived from an about-`10 cm` run against
an about-`1.81 cm` rise, with no instrument, least count, endpoint definition,
repeatability, camera-relative frame or uncertainty recorded. **M10 therefore
requires a fresh metrology-backed ruler unit on both counts** — the old unit cannot
score because it is burned, and its angle would not qualify even if it were clean.
M154 derives the admissible band around the nominal as `-0.245/+0.257 deg`
(`[10.014357337, 10.516726712] deg`): an angle known to `+/-1 deg` yields
`11.022604%` slope error and one rounded to the nearest degree yields `5.231674%`,
against a `2.5%` truth allocation. Degree-level knowledge is therefore not enough.
Image-derived focus may not be used to certify the angle it is being tested against.

The high-resolution slide currently has no committed target-pitch certificate or
external flat/tilted pose measurement. Its development unit may commission M10
planarity and ordering, but it cannot contribute to M10's physical-depth bars. A
future holdout requires those input-only truths to be frozen before any output is
viewed.

## 3. Scorecard at a glance

Publication roles are fixed before any score is read. `M1`, `M2`, `M3`, `M8`, `M9`,
`M10`, and `M11` are **OWNER GATES**. `M4`, `M5`, `M6`, `M7`, and `M12` are
**MANDATORY DISCLOSURES**: their complete values and misses must be published, but
their full-axis bars do not independently decide the owner's claim. Only the
same-output M4 flat-power-plus-transfer component and the M12
1/2/4/8/16-worker byte-identity component cross into owner gates under §0.2. Every
owner gate and both retained components are evaluated on the common-merge track.
M4–M7 disclosures use that same track; full M12 remains a product-native disclosure.
Any additional product-native metric result is reported separately and cannot alter a
publication verdict.

| ID | Metric | Success bar |
| --- | --- | --- |
| M1 | Sharpening-safe resolved information | **NO ADMISSIBLE BAR — WITHDRAWN.** `f_licensed` is blind; native `S_25` fails sharpening and tone, while tone-hardened derivatives reverse the optical controls. |
| M2 | Flat/defocused-ground noise | Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |
| M3 | Occlusion halo and broad veil | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`.** On every capture and pooled: median `h_e,v_e<=0.01`, p99 `h_e,v_e<=0.05`, literal `max(a_e)<=0.05`, affected rate `<=0.01`, median width `[0.95,1.05]`, and median `rho_edge>=0.90`; pooled affected-rate Wilson UCB95 `<=0.02`; `p99(a_e)` no worse than the M1-qualified comparator envelope in every scope. |
| M4 | Non-edge artifact rate | **RETAINED COMPONENT DEFINED; `UNMEASURED_CAPTURE_INADEQUATE`.** Every capture and pooled median `Q_i<=1.00`; every eligible site/channel has `0.995<=g<=1.005` and `r<=0.005`. Full disclosure remains: sites with `Q_flat>1.25`, ghost ratio above `0.10`, or an M3 boundary-limit failure total `<=1%`, Wilson UCB95 `<=2%`, no worse than best comparator. |
| M5 | Depth-of-field coverage / stack failure | `>=99%` of eligible tiles pass `rho_best>=0.90` and focus margin `>=0.05`; Wilson lower bound `>=98%`; longest failed run `<=1%` of sweep. |
| M6 | Recoverable highlight/shadow retention | Recoverable high-rail and low-rail clipping each `<=0.10%`; highlight-detail retention `>=0.90`; no worse than best comparator. |
| M7 | Colour fidelity | Median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum `<=3.0`; on the frozen M145 input-only seam population, nearest-rank boundary-seam p99 `<=1.0` and no connected contour segment has three consecutive sites `>1.0`; an empty or sub-minimum population is `UNMEASURED_CAPTURE_INADEQUATE`; ICC/300-DPI conformance `100%`; no worse than best comparator. |
| M8 | Invented values / source-hull certificate | M8-R per-frame resampler-hull violations and prospective M8-O v1.5 representable-domain final-output violations: each exactly `0.0000%`. The impossible v1.4 M8-O construction is superseded. |
| M9 | Acuity / `n_eff` certificate calibration | **DEFINITION BLOCKED on independent M1 acuity truth.** The registered downstream contract requires false-certification point rate and Wilson UCB95 `<=0.01`, true coverage and Wilson LCB95 `>=0.90`, nominal coverage `[0.93,0.97]`, exact `n_eff` identity with `n_eff>=1.0`, and pooled plus at least 9/10 decile variance ratios in `[0.90,1.10]`; none is presently usable as a bar. |
| M10 | Physical depth product | **DEFINED; UNMEASURED — MISSING PRODUCT, CHECKER, AND SCORED TRUTH.** M190 adopts M163's five uncertainty vetoes and M166's value populations/reductions, leaves the flat-null rule unchanged, and preregisters the quota digest order, origin divisor, product/manifest wire contract with total fail-closed outcomes, and the hidden synthetic renderer, one-draw seed commitment, target populations, and affine certificate. Bars are valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`; flat-null span `<=0.5` step; layer confusion `<=1%`; boundary bias `<=0.5` step and p95 `<=1.0` step; uncertainty coverage `[0.93,0.97]`, at least 9/10 decile variance ratios in `[0.90,1.10]`, and reported half-width median `<=0.5`/p95 `<=1.0` step. No compatible candidate product, commissioned integrated checker, or scored physical/synthetic truth package exists, so no M10 verdict exists. |
| M11 | Wall-clock throughput | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; absolute timing QUARANTINED. COMMON-MERGE GATE:** `R_c>=2.00` on each of C33/C105/C299 and `R_pool>=2.00` against the fastest qualifying per-capture envelope, with retained cross-worker file and pixel identity. **PRODUCT-NATIVE REPORT:** at each N, candidate/default baseline `<=2.00`, CPU-16 `<=0.15 s/frame`, hybrid `<=0.06 s/frame`; every cold pair `<=warm+20.0 s`; all six live replays `<=10.0 s` after shutter close of frame 100. |
| M12 | Memory, determinism, and scaling invariance | Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical; N-mod-4 per-frame spread `<=2%`. |

M8, the M11 comparator/CPU/hybrid/cold/live targets, the M12 6-GiB bar, and byte
invariance come directly from the proposal
(`2026-08-sota-path.md` lines 1582–1584 and 1957–1985). The remaining numerical
completions — including freezing D5's “roughly 2x” as `<=2.00` — are
**SCORECARD ADDITIONS** because the proposal is silent, approximate, or contains
`[bar]`.

### 3.1 Measurement readiness as of v1.10

This table separates scientific blockers from the baseline's single pre-metric
refusal. Codes are the owner's requested categories: **(a)** missing admissible
detail instrument, **(b)** unresolved native-scale/`cover=scale` geometry,
**(c)** missing or under-powered capture, **(d)** unavailable common-input output
from licensed Zerene PMax, licensed Zerene DMap, or a fresh commit-pinned
best-known-source fork rebuild whose executable hash was frozen before rendering,
and **(e)** scientifically measurable now. The archived fork output cannot clear
`(d)`. Helicon, when obtainable, is recorded separately and never supplies blocker
`(d)`. An **(e)** does not mean a result has been run.

| Axis | Class | What can and cannot be measured now |
|---|---|---|
| M1 | **(a)(b)(c)(d)** | No active detail statistic or bar exists; scored matched repeats and comparator arms are also absent. |
| M2 | **INSTRUMENT VOID; (b)(c)(d)** | The licensed flat/defocused-ground noise instrument does not exist. DELIVER-V6's product-native diagnostic fractional box9 residual is `1.515208x` the historical archived fork output's median across twelve frozen sites, with `0 of 12` below one; that output is not an admissible common-merge comparator. A blur challenge scores `0.571215x`, proving that the existing flat-ROI statistic rewards blur. M2 remains `UNMEASURED`, not passing. |
| M3 | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; (a)(b)(d)** | The population and statistic are fixed, but no admitted M1 qualification or required common-input comparator set exists; the profile-package builder and input-only warp evidence are also absent. |
| M4 | **RETAINED COMPONENT DEFINED; `UNMEASURED_CAPTURE_INADEQUATE`; full M4 (a)(b)(d)** | The retained flat-power/transfer bar is exact, but required eligible flat tiles, a separate development flat, materialized Dirichlet matrices/plants, and base/planted renders are absent. The full disclosure's edge/comparator remainder is still blocked. |
| M5 | **(a)(b)(c)(d)** | No scored dense/sparse repeat unit exists, and failure coverage needs a licensed detail test. |
| M6 | **(a)(b)(c)(d)** | The rail census is executable, but the registered capture set has fewer than 10,000 recoverable samples and the full axis includes detail retention and comparators. |
| M7 | **(b)(c)(d)** | No traceable colour target exists. |
| M8 | **(e) for M8-R; M8-O v1.5 `UNMEASURED`** | **M8 remains `FAIL`: M8-R is `1.030569%` against the achievable `0.0000%` bar.** M8-R is the only produced-and-read score against an achievable bar. The historical M8-O v1.4 `1.326144%` figure is superseded because its bar was impossible as written; the corrected v1.5 checker at `e5489d64` has not been recommissioned, so no v1.5 M8-O score exists. |
| M9 | **DEFINITION BLOCKED — `DEFINITION_BLOCKED_M1_TRUTH`; (a)(c)** | No independent candidate-specific acuity-truth producer is admitted through the current M1 registry route; the balanced manifest, repeat captures/truth, calibration, and certificate product are also absent. M1 is the only currently specified and physically actionable route with an evidenced path today, not a unique mathematical anchor. The downstream contract is not presently scoreable. |
| M10 | **DEFINED; UNMEASURED; (b)(c)** | M190 closes the four remaining definition gaps before any candidate output: quota SHA-256 is byte-lexicographic/big-endian with a total tie-break; origin `N` is the full-capture count of candidate-valid truth targets; the depth/sigma/valid package has a strict JSON/TIFF/hash contract and total fail-closed outcome map; and the hidden synthetic renderer, PRF, one-draw scored-seed commitment, exact populations, and affine-certificate proof are frozen. Remaining blockers are implementation/evidence: a compatible native-grid product and commissioned integrated checker, fresh ruler and independent focus-axis/repeat truth, and either output-blind certification of the existing flat battery or a fresh flat. The scored synthetic arm is defined and precommitted but has not been rendered against a frozen candidate. No M10 verdict exists. Not `(e)`: `:834` defines `(e)` as scientifically measurable now, which M10 is not. |
| M11 | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; absolute timing QUARANTINED** | M1/M2 qualification, required common-input comparator outputs, the fresh hash-bound fork, frozen modes, timing harness, trace, reboot receipts, and quiet-host release are absent. STATUS §2.9.55's `93.2%` mean host CPU makes current absolute wall time inadmissible. |
| M12 | **MEASURED; `M12-D` PASS, `M12-S` FAIL, M12 overall FAIL** | Hashes and process-tree RSS need no detail, comparator or holdout, and the registered `N=33/105/299` x `1/2/4/8/16` matrix was completed on a guarded host by lane M139 (`0c089f96`). Peak Job Object memory `35.65745162963867 GiB` against the `6 GiB` bar; five distinct TIFF and five distinct pixel hashes across workers at every N; N-mod-4 spread `0.07618677189815302` against `2%`. Only `peak_N299/peak_N33` is unread, at `UNMEASURED_SAMPLING_COVERAGE` (minimum coverage `0.7957678743186919` against `0.90`); it cannot rescue two exact bar failures. Adjudicated licence-free by M178: the reverse dependency making M12-S wait on all of M11 was an unratified scorecard addition, now removed. |

Thus defining M3, retained M4, and M11 does not make them adjudicable, and M9 remains
definition-blocked. M8 is the only complete quality axis ready now. M12 is
scientifically unblocked, but its complete registered run is deliberately deferred to
a quiet host. M6's clipping preflight and several other submetrics may be run as
diagnostics; they are not complete axis verdicts.

### 3.2 Closed program decision gates

These gates decide whether a proposed implementation branch is licensed. They are
registered because otherwise their results will be mistaken for missing work, but
they are **not** M1–M12 output scores. “PASS” below means the narrow phase-0 question
was answered; “KILL/STOP/NOT ROBUST/CLOSED/REFUTED” licenses a no-build decision at
the stated scope. No row may silently populate §6.

| Lane / gate | Registered verdict and number | Independent units / power | Frozen and result commits | Scorecard effect |
|---|---|---|---|---|
| IOPERF / D11 decode | **PASS — retain rawler.** Allocated-output rate `381.0 MB/s` at one thread and `1,413.4 MB/s` at 32; paired compressed-input rates `193.9` and `719.3 MB/s`; saturation by 16 threads. A 200-ms plant added 188–289 ms. | Three A7C II ARWs (first/middle/last) per iteration; seven Divan samples; forward/reverse sweeps at 1/2/4/8/16/32 threads. | `40e41a63` / `d337daa8` | Admitted for D11's decoder build gate only. It is not M11 end-to-end native-product throughput. |
| IOPERF / D15 storage | **PASS — do not build IOCP.** Cold no-buffering `6.338 GB/s`, immediate buffered warm `20.615 GB/s`, `3.25x`; replication `6.342/19.671`, `3.10x`; independent third cold `6.334 GB/s`. Storage was 11.41% of projected decode time against a 20% materiality bar. | 60 ARWs, exactly 2,252,959,744 compressed bytes; QD8; two accepted runs plus one independent read-only replication. | `40e41a63` / `d337daa8` | Admitted for D15's storage-materiality gate only. It is not M11 cold-minus-warm product latency. |
| DPAR2 / C4c curved track | **KILL** the stated `0.3–0.6 px/depth-step` mechanism. MDA80 `<=0.010 px/step` at radius 1000, bootstrap 95% `[0.010,0.010]`; proposed minimum cleared by 30x. Null `rho=+0.1352`, `p=0.4896`. | 15,599 accepted residual observations, three stacks, 96 preserved-noise torus phases; first nonzero rung detected 96/96. | `e27e3dd8` / `7a1a3128` | Admissible conditional KILL of C4c, not a universal claim that every lens lacks every smaller or differently shaped term. No axis score. |
| XSPEC / C10 | **NOT ROBUST.** `R=0.70852`, CI `[0.66732,0.76315]`, below point/lower bars `2.0/1.5`; held-out grid-48 floor `71.43%` of 49 against 80%. | Bee: 654 records / 132 tiles, below the frozen 160-tile minimum. Text: 1,000 / 200. | `efdc6829` / `4f1f28ec` | Admissible refusal to build. It does not establish that C10 is absent or incapable. No axis score. |
| VEIL2 / A2 | **STOP — DO NOT BUILD.** Primary `theta=-0.081241`, CI `[-0.235876,+0.051078]`; four potency/provenance gates failed; re-scope audit `0/7`. | Effective `n=36` spatial clusters. The 20,000 bootstrap draws are Monte Carlo resamples, not independent observations. | `e4e3939f`, `bcc77de9` | Admissible refusal only. It does not prove zero veil or settle M3. |
| LCA / C2 | **STOP.** Reproduced axial focus forfeits: R `4.22–7.54%`, B `3.51–7.13%`, but tone-normalised evidence was valid on only 1/4 stacks; both registered gamma arms were invalid. | 1,002 RAW frames across four stacks; frozen four-stack tone gate required 4/4. | `08cf9401` / `a3b87d36` | Axial CA exists; a field-valid corrective build is not licensed. This is not M7 colour fidelity. |
| CAND1 / detail instrument | **KILL candidate 1.** USM/base `1.095732x`, one-sided UCB95 `1.129895`, against frozen `<=1.01`. | 480 independent macro-tile clusters, eight trials each (3,840 trials) across five acquisition blocks. | `613eaf1`, `efa25bd2`, `2d3d247d` | Admissible instrument KILL. M1 still has no statistic or bar. |
| COVER / default path | **SUPERSEDED 2026-09-05 — original verdict retained.** *Original:* **CLOSED — keep Scale.** Crop ring up to `+2.6106%`; minimum evidenced safe inset 256 px; retained area `64.6047%` against 80%. Scale changes 98.1463% of identity-arm samples. **Superseding result (M130 `crop-early`, commit `248178b9`):** the `64.6047%` was produced by late-crop boundary poisoning, not by the crop geometry itself. Evaluating warps in full-plane coordinates and extracting the covered rectangle *before* luma, variance, gate floor, pyramid, weighting, accumulation, confidence and collapse reduces the evidenced safe inset from 256 px to 8 px and raises retained area to **`96.22496088092659%`** — `FAIL -> PASS` on the same 80% gate, a `1.489442x` improvement. Default output is byte-for-byte unchanged. | Four development captures decoded; `109MSDCF` supplied the admitted inset profile, while the ruler specificity arm refused a general safe inset. Superseding arm: 121 unit tests, 4-row byte freeze, retention re-derived independently from plane geometry. | `66e79043`; superseded by `248178b9` | The original ruling that Crop is not licensed as the default was correct **on the evidence then available**. Blocker `(b)`, the scorecard native-scale geometry gate, is now **CLEARED**. `DEFAULT_COVER_MODE` remains `Scale`; this row licenses the geometry, not a default change. |
| Phase 1 / W1 | **WITHDRAWN 2026-09-05 — original verdict retained.** *Original:* **REFUTED — DO NOT IMPLEMENT.** `NO_COMMON_K`: 16/42 predicates pass at some `k`, 26/42 at none, and no band-4–6 predicate passes anywhere in `[0,8]`. **Withdrawal (M138, commit `cac33527`):** the gate was **unsatisfiable by construction**. `experiments/PHASE1-DESIGN/measure.py:129-130` defines the legacy comparator's exponent as `min(2.0 * 1.4 ** (R.BANDS - 1 - band), 8.0)` = `[8.0, 8.0, 7.6832, 5.488, 3.92, 2.8, 2.0]` — **band-shaped by construction** — while the gate required a band-*constant* candidate to reproduce it per band within `±5%`, and evaluated that requirement *before* any quality bar. Bands 4–6 returned `0 of 18` width survivors, so the Pareto frontier the phase existed to render **was never rendered**. Legacy `n_eff` spans `2.88x–37.95x` within one capture and ROI. | 42 frozen capture/band predicates over the 161-value width grid on three development captures. | `f5658e5d`; withdrawn by `cac33527` | **Phase 1 returns to `untested`, not validated** — *"unvalidated, not rescued"*. The width match is a comparator-equivalence requirement, not an output-quality requirement. Real standardisation defects remain and must be repaired before re-run: pooled-only coverage gating, no positive-`q` commissioning, band-0-only Poisson control, approximate variance propagation, no selected-winner/stack-size calibration. A corrected gate is being specified and preregistered before any number exists. |

**Strict systems-gate ruling.** D11 and D15 are admitted as phase-0 PASS
verdicts because their governing proposal asks for those exact component estimands,
not a full product render. D11's three-file set is narrow, but the frozen gate had no
cross-file minimum, sampled the bracket's beginning/middle/end, consumed and checked
every decode, and clears its bars by 1.91x per core and 1.41x aggregate. Its result is
scoped to this A7C II codec/workload and cannot generalise to another camera or fill
M11.

D15's no-buffering arm bypasses the Windows page cache and remains at device rate
after the buffered warm placebo becomes 3.1–3.3x faster. SSD controller
firmware/DRAM cannot be disabled, but it is part of the host-visible device path D15
asked to price; this is not a NAND-only claim. The result is scoped to this 980 PRO,
QD8 workload. Neither systems PASS supplies M11's registration, merge, colour,
write, comparator, or end-to-end cold/warm terms.

**Power ruling.** XSPEC and VEIL2 are admissible **refusals**, not admissible
negative capability claims. XSPEC missed its own 160-tile minimum and therefore says
“C10 was not shown to work,” not “C10 was shown not to work.” VEIL2's effective
sample is 36 clusters, not 20,000 observations; its 0/7 audit stops the build but
does not prove the underlying effect is zero. Under-power is safe only because these
verdicts decline authorization rather than assert absence.

**Resulting scoreboard:** **two owner gates have an admitted `FAIL` (M8 and M12),
one is `DEFINITION BLOCKED` (M9), and the other nine axes are `UNMEASURED`; no
axis passes.** M1 carries the greatest publication consequence because the owner's full
SOTA sentence includes detail and M1 has neither an instrument nor a bar. It is not
by itself a prerequisite for a future independently commissioned M2
flat/defocused-ground verdict. M8-R is the only produced-and-read score against an
achievable bar; its failure cannot be rescued by an absent M1.

## 4. Metric cards

### Shared conventions for the M166-repaired bars

The M3, retained M4, M9, and M11 definitions below adopt
`docs/research/M166-bar-definition-repairs.md` at commit `e4c69154`. For those four
definitions:

1. `PASS` and `FAIL` describe a candidate only after every required
   input/reference/comparator exists and passes its own admission checks. A missing
   required capture, truth producer, comparator, manifest, or commissioning artifact
   is `UNMEASURED_<reason>`, never a candidate pass or fail.
2. Missing, cropped, malformed, non-finite, rail-clipped where clipping is forbidden,
   or hash-mismatched **candidate** data are charged as the candidate-worst value
   stated by the metric. They are never deleted from a frozen population. Malformed
   frozen evidence invalidates the campaign instead.
3. All thresholds apply to unrounded IEEE-754 binary64 values and are inclusive.
   Reports may print decimals but must also retain hexadecimal binary64 values or
   exact integer numerator/denominator pairs. Non-finite values never compare as
   passing.
4. A nearest-rank quantile of `N>0` values is sorted ascending and takes the one-based
   element at `ceil(qN)`; there is no interpolation. An empty population is
   `UNMEASURED_EMPTY_POPULATION`.
5. Stable order is ascending UTF-8 byte order of the frozen `site_id`, `cell_id`,
   product ID, and mode ID as applicable. This is also the tie-break order.
6. One-sided 95% Wilson limits use `z=1.6448536269514722`. The upper limit is
   `((p+z²/(2n)) + z*sqrt(p(1-p)/n+z²/(4n²))) / (1+z²/n)`; the lower limit changes
   the `+` before the square-root term to `-`.
7. Every result binds the scorecard hash, input and output byte hashes, checker hash,
   complete settings hash, product and mode IDs, population manifest hash,
   representation, and every excluded/invalid row with reason.

### M1 — WITHDRAWN: no admissible detail instrument

**What it must measure and why.** A focus stacker must preserve independently
repeatable scene information across the depth sweep, not merely raise edge contrast.
Raw band power, MTF50, acutance, SFR and other presentation statistics can all rise
after an information-free sharpening pass.

**Why the v1.3 M1 instrument is withdrawn.** Independent commissioning established
both failure modes that this pre-registration was intended to expose:

- `f_licensed` remained pinned at `0.15 cyc/px` for the base, physical blur, genuine
  improvement and unsharp-mask arms. It is sharpening-invariant only because it is
  blind.
- The earlier 24-seed native `S_25` run read USM/base `0.995819x`
  (`-0.418%`) and therefore appeared to pass the frozen 1% commissioning bar.
  The identical arms on the expanded 64-site control read `1.028294x`
  (`+2.829%`), **RED against the unchanged 1% bar**. The bar did not move; the
  sample grew. The flattering 24-seed result was underpowered and is superseded
  (`docs/research/M-PHASE0-SLANTEDGE.md` lines 269 and 276–278).
- Native `S_25` also moved `4.8400x` under gamma-3 tone and `18818.9045x` under
  a logistic tone curve. Its noise range was `0.004972x`–`10.381863x`, and its
  0.5/1/5/12-degree response was `1.42205/1.18548/1/0.65802`. Derivatives that
  hardened tone reversed the optical controls: blur `1.268326x` and genuine
  improvement `0.923468x` (ibid., lines 269–274).

Accordingly, **the `S_25` requirement is withdrawn plainly, not weakened**, and the
old `f_licensed`/`S_25` formulae are not claim-bearing scorecard outputs. Three
independent slanted-edge implementations are also presentation diagnostics only:
they report roughly a 9.9% “resolution” gain after post-render unsharp masking.

**Current sharpening-safe inventory.** Among the candidates tested in this repository
under the current output-only observation contract, no admissible detail statistic is
sharpening-safe: none that still responds correctly to physical blur and genuine
improvement survives sharpening. Q25 rewards the same
information-free USM by `5.560744x`; all three slanted-edge implementations report
roughly 9.9% improvement; and native `S_25` now reads `1.028294x`, outside its
unchanged 1% bar. Hardened `S_25` derivatives that suppress USM are not
counterexamples because they cease to be resolution statistics: blur scores sharper
and genuine improvement scores worse.
This complete candidate sweep requires a future instrument to have a structural
reason sharpening cannot improve it; a small empirical battery alone is not evidence.
Here “structural” includes an independently anchored reference, validated external
model or prior, certified target with an expressly limited claim, or another
observation outside the compared outputs. The inventory above is a result about the
candidates actually tested in this repository, not a theorem that every conceivable
no-reference metric must fail.

**Reusable positive from the failed lane.** An external 33-step PCHIP linearisation
moved affine, gamma, and logistic tone arms by at most `0.0141%` without disturbing
the USM result. Tone invariance therefore does not require an ordinal statistic.
Future candidates may reuse this independent tone witness, but it does not excuse
their own sharpening, optical-direction, noise, angle, and null controls
(ibid., lines 286–289).

**Effect on M1 replacement.** None of M1's status, missing captures, or absence of a
numeric bar changes. The superseding result strengthens the admission requirement:
a replacement needs structural sharpening protection plus the full commissioned
battery; it does not resurrect or select a statistic.

**Input needed by the currently specified replacement route.** These captures are part of
the instrument's construction, not an alternative to the instrument or a way to
“shoot around” it:

- one dense checker-only reference;
- two independent sw4 passes at identical geometry and exposure, IBIS off;
- two independent sw10 passes at identical geometry and exposure, IBIS off;
- matched dark/flat captures and a non-periodic independent-reference sentinel.

The burned grid and the development-only high-resolution slide may commission a new
instrument but may never provide its scored value.

**Exact computation.** None is admitted in v1.10. A replacement must be
pre-registered before its fresh holdout is rendered, must declare and commission its
licensed frequency range, and must be implemented and audited independently of the
pipeline producing the render. Any claimed band above `0.25 cyc/native px` must also
satisfy decision rule 7's independent scene-content, alias-disambiguation,
optical/sampling-ceiling, planted-improvement, untuned-null, and
planted-degradation requirements.

**Success.** There is deliberately no active numeric success bar. M1 remains
**UNMEASURED**, and no detail or full SOTA claim is licensed until a replacement
statistic and numeric bar survive commissioning. M1's absence does not by itself
block a future independently commissioned M2 flat/defocused-ground verdict.

**Known defeat.** Sharpening can fake edge/detail transfer; monotone tone can fake
spectral ratios; averaging can improve noise by destroying detail; shared fixed
pattern or deterministic hallucination can make repeat renders agree; a periodic
checker can carry its own answer.

**Required controls for any replacement.** It must distinguish untuned null,
pre-sensor blur and genuine optical improvement in the correct directions; refuse
post-render unsharp-mask, gamma, logistic-tone, noise and edge-angle challenges; fail
a common-mode A/B plant absent from the independent reference; and report a flat ROI
as no detail evidence. Its sharpening battery must use at least 64 independent sites
and retain its frozen bar as sample size grows; a structural invariance argument is
still required, or an independently justified external assumption or observation
must supply equivalent protection with its scope stated explicitly, because
empirical non-rejection is not a guarantee. Those challenge outcomes and numerical
admission bars must be frozen in a later revision before score data are read.

### M2 — flat/defocused-ground noise

**Instrument status: INSTRUMENT VOID; current axis verdict `UNMEASURED`.** The
existing flat-ROI statistic is commissioned only as an output-residual measurement,
not as a stand-alone comparative noise instrument: a blur challenge improves it to
`0.571215x`. On twelve frozen coffee-paper sites, the product-native DELIVER-V6
diagnostic instead measures an adverse median `1.515208x` the historical archived
fork output's fractional box9 residual, with `0 of 12` sites below one. That archived
output is not an admissible common-merge comparator. Both observations must be
published, but neither is a licensed M2 verdict, and the rename does not make M2
measurable or passing.

**Amendment 6 scope.** The `0.571215x` blur result is an empirical defeat of
the existing flat-residual statistic. Separately, M2's output-only ambiguity is an
identifiability construction: the same rendered pair can represent removed
noise/artifact or removed scene signal, and the pair alone cannot choose between
those worlds **without an assumption or observation outside those outputs**. This is
not D8's separate common-filter algebra and not the band-power statistic's empirical
flat-null failure. It also does not rule out every no-reference metric. M164's
external-reference `Q_EIN` candidate has author-generated synthetic evidence only;
it has not passed the independent battery or physical commissioning and is not an
admitted M2 instrument. The current verdict therefore remains `UNMEASURED`.

**What it measures and why.** Focus stacking should average independent sensor noise
without trading it for blur, selected grain, or low-frequency patchwork.

**Input.** The two 32-frame ISO-100 bee repeat blocks, the ISO-100 paper block, and
the dark/FPN captures. For each 32-frame block, frames 1–16 are stacked and frames
17–32 form an external mean reference, then the roles reverse. Flat ROIs are selected
on the other illumination block and frozen before output. At least 32 non-overlapping
ROIs total and 16 per light must qualify.

**Exact computation.**

1. Candidate 128x128 ROIs must be in the lowest quartile of input-only
   `0.02–0.08 cyc/px` structure and contain no clipped samples.
2. For each cross-fit output `O` and held-out 16-frame mean `R`, compute the
   `0.15–0.35 cyc/px` residual and
   `sigma_res = 1.4826 * MAD(BP(O-R))`.
3. Estimate per-frame temporal `sigma_1` from pairwise frame differences, never from
   spatial texture. The ideal difference of two independent 16-frame means is
   `sigma_ideal = sigma_1 * sqrt(2/16)`.
4. `eta = sigma_res / sigma_ideal`. On a natural-detail target, the comparator ratio
   uses paired ROIs and only modes within `98%` of a future replacement-M1 information
   envelope; no mode qualifies by that route in v1.10. An M1-independent replacement
   may instead use a pre-registered, input-certified featureless or deliberately
   defocused target whose scope makes no photographic-detail claim. No such
   instrument or qualifying common-merge comparator output exists today.

The `0.15–0.35 cyc/px` quantity here is a noise residual, not a detail or acuity
reading; it does not license any spatial-resolution claim above `0.25 cyc/px`.

**Success.** The proposal says “strictly lower noise” but supplies no practical
margin (`2026-08-sota-path.md` lines 192–195). **SCORECARD ADDITION:**
`eta <=1.10` and `UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`.

**Known defeat.** Blur, denoising, black crush, lower gain, or selecting an unusually
flat ROI can lower the statistic without improving the stack.

**Control.** Input-only cross-light ROI selection prevents output cherry-picking;
§1.3 fixes gain and tone. A Gaussian-output-blur plant must improve raw noise while
failing the edge-width/gain guard, so the report exposes the known route by which
blur can buy a lower residual. Added independent noise of `0.25 sigma_1` must increase
`eta` by at least `0.20`; the untouched temporal mean must fall in
`0.90 <= eta <=1.10`. The existing flat-ROI instrument fails the blur-specificity
control at `0.571215x`, so `eta` and the adverse product-native DELIVER-V6
`1.515208x` residual remain diagnostic and M2 remains `UNMEASURED` until a
replacement instrument is independently commissioned. M2 receives its own verdict
and licenses only its stated flat/defocused-ground noise claim, never a detail claim.

### M3 — occlusion halo and broad veil

**Definition status.** The statistic is defined by M166, but its comparator limb is
not adjudicable. M3 remains `UNMEASURED_COMPARATOR_QUALIFICATION` until M1 admits the
required comparator outputs and the profile-package builder/input-only warp evidence
exists. Definition does not manufacture qualification.

**What it measures and why.** Focus stacking combines different depth layers at one
boundary. It can create overshoot/undershoot rims, ghost edges, or a broad pedestal
from the out-of-focus foreground. The proposal explicitly requires a bounded veil but
leaves `[bar]` blank (`2026-08-sota-path.md` lines 192–197).

**Frozen population and representation.** Adopt these existing artifacts by content
hash:

- M152 census manifest
  `experiments/M152-site-census/out/census-manifest.json`, SHA-256
  `35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d`;
- M161 checker definition
  `experiments/M161-m3-ratification/m3-checker-definition-v2.json`, SHA-256
  `578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca`;
- M161 scorer `m3_checker_v2.py`, SHA-256
  `05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda`.

The frozen population is exactly 500 sites: duck tape 133, chia 133, flower/fern
132, and horizontal-razor control 102. No output-dependent selection or replacement
is allowed.

Decode every common input and product output as unsigned 16-bit linear ProPhoto RGB
D50. Normalize each code by `65535` and form the binary64 scalar

`Y = 0.2880402*R + 0.7118741*G + 0.0000857*B`.

Before scoring, each adapter supplies one hash-bound common-coordinate to
output-coordinate similarity transform per product/capture. It is derived from
input-only landmarks, never from scored output. Its independently held-out landmark
residual must meet all M161 limits: absolute scale disagreement `<=0.1%`, absolute
rotation disagreement `<=0.02 degrees`, and non-translation residual RMS
`<=0.1 output px`. Failure is `UNMEASURED_WARP_INADEQUATE`, not a deleted site.

At each frozen site, use the manifest centre and renormalize its stored dark-to-bright
normal once in binary64 by `n=n_raw/hypot(nx,ny)`. For signed native-pixel offsets
`s=-400,-399,...,400`, bilinearly sample each source `Y` image at `centre+s*n`;
sample output at the transformed coordinate. Pixel centres have integer coordinates,
bilinear interpolation uses the four enclosing centres, and an exact integer
coordinate has its integer pixel value. Any required sample outside the image charges
that output site invalid. The 128-by-128 `rho_edge` patches are axis-aligned and use
coordinates `centre+(j-63.5,i-63.5)` for `i,j=0,...,127`, sampled by the same rule.

The M152 discovery source named by `source_file` is both `normalization_source` and
`far_reference_source`. `sharp_source` is the source having the smallest finite
10–90 width under the M161 definition; ties take the earliest source-frame ordinal.
All source frames form the pointwise source hull. These source-only choices are
shared bit-for-bit by the candidate and every comparator.

**Exact computation and bars.** For each site, use the M161 v2 formulas:

- `h_e` is the maximum output excess outside the all-source pointwise hull on
  `2<=|s|<=32`, divided by the discovery source's narrow step measured from
  `[-64,-48]` and `[48,64]`;
- `v_e` is the greater of the negative-side and positive-side arithmetic mean
  absolute residual from the discovery source on `16<=|s|<=200`, divided by that
  source's broad step measured from `[-400,-320]` and `[320,400]`;
- `a_e=max(h_e,v_e)`;
- width is output 10–90 width divided by the sharp-source 10–90 width on `[-32,32]`;
- `rho_edge` is M161's complex cross-spectrum coherence on the 128-pixel patch in
  `[0.15,0.25] cyc/native px`.

> **Prior M3 tightening provenance — unchanged.** The earlier whole-band
> `v_e = mean(|O(s)-R_far(s)|)` averaged the two sides together. M152 commissioned
> that literal reduction against a required one-sided plant occupying offsets `+33`
> to `+232` — a `6%` veil — and the unaffected side diluted it to `0.027243`, so no
> site crossed the `5%` affected threshold and the affected count stayed zero. The
> per-side maximum detects `100%` of those sites, reading approximately `0.0545`.
> Because the old whole-band mean is `(v_e_neg+v_e_pos)/2` and
> `max(a,b)>=(a+b)/2`, the retained maximum cannot make an output easier to pass.
> M152 returned `NOT_ADMITTED_COMMISSIONING_FAILED` with
> `failed: one_sided_far_veil_detected_at_least_95pct`
> (`docs/research/M152-site-census.md`, "Commissioning failure"). No scored M3
> result exists, so nothing was re-graded.

A malformed output site is `(h_e,v_e,width,rho)=(+inf,+inf,+inf,0)`. A site is
affected iff `a_e>0.05`.

The candidate must satisfy every bar both on each of the four capture populations and
on the pooled 500 sites:

- nearest-rank median `h_e<=0.01`;
- nearest-rank median `v_e<=0.01`;
- nearest-rank p99 `h_e<=0.05`;
- nearest-rank p99 `v_e<=0.05`;
- `max(a_e)<=0.05`;
- affected point rate `<=0.01`;
- nearest-rank median width ratio in `[0.95,1.05]`;
- nearest-rank median `rho_edge>=0.90`.

The one-sided 95% Wilson upper bound on affected rate is computed only on the pooled
500 sites and must be `<=0.02`; applying that confidence bar to the 102-site razor
control would make even `0/102` exceed 2%. Per-capture point bars remain mandatory.

For the comparator clause, form `p99(a_e)` on identical frozen sites with no
deletion. For each capture and for the pooled population independently, the reference
is the lowest value among every available mode that has passed admitted M1
qualification on those same output bytes. This per-scope envelope is deliberately no
easier than choosing one favourable global mode. Ties use product ID then mode ID.
Required modes are licensed Zerene PMax, licensed Zerene DMap, and the fresh
best-known-source fork rebuild; each obtainable Helicon A/B/C mode also enters.
Strehl's value must be `<=` that reference in every scope. If any required comparator
product is absent, or no mode has admitted M1 qualification, M3 is
`UNMEASURED_COMPARATOR_QUALIFICATION`.

**Loose-direction closure.** A constant output has no finite 10–90 crossing and zero
coherence, so it fails. A blur large enough to collapse edge transfer is rejected by
the `1.05` width ceiling; coherence alone is not credited as transfer magnitude. A
one-sided veil cannot be diluted by the opposite side, and one or a few severe sites
cannot hide below p99 because the literal maximum is mandatory. No favourable capture
or comparator can compensate for another because every capture and the pooled
population pass independently.

**Commissioning control.** The score is excess over the source interval/reference,
not absolute optical halo. A 6% planted rim and 6% 200-px veil must be detected on at
least 95% of sites; untouched raw frames must have false-positive rate `<=1%`. Any
checker that convicts the raw null is not admitted.

### M4 — non-edge artifact rate

**Publication role: MANDATORY DISCLOSURE.** Full M4 must be measured and published.
Only the flat-power-plus-transfer component below, computed from the same output bytes
and settings as the M1/M2/M8 claim, is retained as that named claim's anti-cheat
component. The full-axis failed-site, ghost-ratio, and comparator bars remain
mandatory disclosures and do not independently gate the owner's verdict.

**What it measures and why.** Spatially varying frame election can manufacture
20–60 px patchwork on flat ground, while bad registration can create double contours.
Neither is adequately represented by a single “halo” number.

**Definition and current state of the retained component.** The retained component is
now exact, but it is `UNMEASURED_CAPTURE_INADEQUATE`. It waits on at least 29
additional eligible medication flat tiles, at least 83 eligible foam tiles, a
separate development flat of at least 100 tiles, materialized Dirichlet matrices and
transfer plants, and base/planted common-input renders. None may be replaced by an
empty denominator or waived limb.

**Exact flat-power limb.** Adopt M152's population and randomization freeze
`experiments/M152-site-census/m4-freeze.json`, SHA-256
`a92b49bd2dc0a661b3319f96e54c7514994292f17f5a0ac0bab0d12cf7cb8d5c`.
The canonical window, mask, Parseval weighting, and band-RMS implementation is
`experiments/M152-site-census/census_common.py`, SHA-256
`3e36a18d8c7b675f224f4fbe694ef2d16297e3e038df18e61cdb4dead219a680`.
The scored population is exactly 250 output-blind 128-by-128 native-pixel flat tiles:
medication pill 84, bee background 83, and foam 83, with no cross-capture
substitution. Site order is M152's frozen order. The unplanted/base output is the
exact same output byte stream and settings used by the retained M4 component in the
joint M1/M2/M8 quality bundle.

For every source common TIFF and candidate output, use decoded linear ProPhoto green
channel `G/65535`. For each tile:

1. subtract its arithmetic mean;
2. multiply by a separable 128-point Hann window normalized to mean-square one;
3. take an orthonormal real 2-D FFT;
4. sum squared magnitude, with exact real-FFT Parseval weights, over radial frequency
   `1/60<=f<=1/20 cyc/native px`;
5. divide that energy by `128*128` and take the square root.

`B99_i` is the nearest-rank p99 of that band RMS over:

- 1,000 blends of all source frames with
  `numpy.random.Generator(PCG64(15240420260904))` and independent
  `Dirichlet(1,...,1)` weights in generated order;
- every one-hot source frame; and
- the uniform source mean.

Instantiate the generator once. In fixed capture order medication, bee, foam, draw
one `1000 by N_frames` matrix per capture; every site in that capture uses the same
matrix. Before any candidate output is opened, materialize those matrices as
little-endian binary64 arrays and bind their SHA-256 values in the campaign manifest.
Those arrays, rather than a later library's reimplementation of `Dirichlet`, are the
normative random input.

The ISO floor is interpreted in the same normalized linear units and is exactly:

- ISO 50 or 100: `1.26102285354196e-5`;
- ISO 1000: `3.72061790502189e-5`.

For tile `i`,

`Q_i = band_rms(candidate_G_i) / max(B99_i, noise_floor(ISO_i))`.

A missing/invalid output tile has `Q_i=+inf`. The retained `median Q_flat` is the
nearest-rank median of these `Q_i` values. Each of the three captures'
nearest-rank median and the pooled 250-site nearest-rank median must be `<=1.00`; any
invalid tile is also an immediate candidate failure.

**Mandatory paired transfer veto.** Flat power alone is not admissible. After the
candidate binary, settings, common-input manifests, and flat sites are hash-frozen,
derive two phases per site from SHA-256:

`phase(site,j) = 2*pi*uint64_be(SHA256("M4-TRANSFER-V1|"+site_id+"|"+j)[0:8])/2^64`.

For local tile coordinates `x,y=0,...,127`, form the exact signed integer-code plant

`P_i(x,y)=round_ties_even(256*cos(2*pi*(4x+3y)/128+phase(i,0)) + 256*cos(2*pi*(-3x+4y)/128+phase(i,1)))`.

Both carriers have radial frequency `5/128 cyc/native px`, within the scored 20–60 px
band. A flat site is eligible only if adding `P_i` to R, G, and B of every source
common TIFF cannot leave `[0,65535]`; this margin check is input-only and occurs
before outputs. Add the same `P_i` to every frame and all three channels at all
selected non-overlapping sites, producing one hash-bound planted twin stack per
capture. Render the base and planted stacks with identical candidate binary and
settings. Materialize and hash the integer plants before rendering; their stored
bytes, not a platform's later `cos` implementation, are normative.

For each site and each RGB channel, let `P` be the decoded planted-minus-base input
tile and `D` the planted-minus-base output tile, both divided by 65535 and with their
tile means removed. Compute

`g=<D,P>/<P,P>` and `r=||D-gP||_2/||P||_2`.

Every site and channel must have `0.995<=g<=1.005` and `r<=0.005`. `<P,P>=0`, any
non-finite value, changed output geometry, or a missing twin is a candidate failure.
The phases stay concealed until all candidate and comparator hashes/settings are
frozen.

A constructive clean implementation exists: at each flat tile choose any registered
convex source blend whose measured band RMS is at or below its `B99` and use weights
summing exactly to one. Its base has `Q<=1`; because the plant is identical in every
source, the same linear blend gives `D=P`, hence `g=1` and `r=0`.

**Loose-direction closure.** A constant output still obtains `Q=0`, but its
planted-minus-base output is zero, so `g=0` and the retained component fails. A blur
that materially attenuates or distorts the 25.6-pixel carriers fails gain or residual.
Because the plant is applied to the actual scored flat stacks at the actual scored
sites, this is not a separate easy synthetic scene. The transfer veto can only
reject; it cannot rescue `Q_flat>1`.

**Full-axis disclosure remainder, unchanged.** In addition to the retained component,
full M4 retains coffee-bubbles as a flat commissioning target and measures structured
edge sites from fabric, duck tape, and flower/fern; the burned grid may commission but
cannot score. At least 500 full-axis sites overall and 50 per scored capture must
qualify. A full-axis flat tile qualifies only if every input frame's
`1/60–1/20 cyc/native px` power is below the independently measured temporal-noise
99th percentile. On an edge,
`g_ghost` is the largest secondary same-sign normal-gradient peak 2–20 px from the
main peak divided by the main peak. A full-axis site fails if `Q_flat>1.25`,
`g_ghost>0.10`, or it fails M3's 5% boundary limit. Its failed-site point rate must be
`<=1%`, Wilson UCB95 `<=2%`, and no greater than the best comparator's. These
full-axis bars remain mandatory disclosures, not owner gates.

**Commissioning control.** The checker sees inputs and final pixels, never weights. A
planted 32-px spatial selector must make at least 95% of planted flat tiles exceed
`Q=1.25`; a fixed-weight mean must produce no more than 1% failures. Shifting output
by one tile must destroy edge correspondence without changing its spatial spectrum.

### M5 — depth-of-field coverage and stack failures

**Publication role: MANDATORY DISCLOSURE.** Full M5 must be measured and published;
its miss is reported as `DISCLOSURE MISS` when every owner gate passes.

**What it measures and why.** A stack may be sharp where it succeeds yet leave focus
holes, choose the wrong depth, lose a thin layer, or crop away difficult regions.

**Input.** The three new tilted-slide stacks are development-only commissioning
captures; they do not replace the burned grid's holdout arm. Remaining holdouts are
all three tilted-ruler apertures, flower/fern, duck tape, and medication-pill. The
burned grid is also development-only. Sites are 128x128 input-fixed tiles. At least
500 eligible tiles overall and 50 per capture must qualify. M5 remains
`UNMEASURED` until a fresh controlled-slide holdout replaces the burned arm.

**Exact computation.**

1. Determine each tile’s best source frame from the input-only `0.05–0.12 cyc/px`
   band or, on the ruler/grid, from physical target contrast. Evaluate
   `0.15–0.25 cyc/px`.
   A tile is eligible only when its best/far source-signal ratio is `>=2.0` with
   bootstrap lower bound `>=1.5`.
2. For output `O_k` and each source-frame spectrum `I_j,k`, compute
   `rho_j = |sum(O_k conj(I_j,k))| /
   sqrt(sum(|O_k|^2) sum(|I_j,k|^2))` in the evaluation band. Let `rho_best` use the
   independently elected frame. Let `rho_far` be the maximum over frames at least
   three focus steps away.
3. A tile passes when `rho_best>=0.90` and
   `rho_best-rho_far>=0.05`.
4. Coverage is passing eligible tiles divided by all input-eligible tiles. A connected
   run is measured along the known focus-sweep direction.

**Success.** **SCORECARD ADDITION:** coverage point estimate `>=99%`, Wilson LCB95
`>=98%`, longest failed run `<=1%` of the sweep dimension, retained FOV `>=99%`, and
strehl coverage no lower than the best comparator.

**Known defeat.** A single sharp plane can look excellent in selected tiles; cropping
can remove failures; a common blur can preserve correlation while making the
presentation soft; an eligibility map derived from the output can omit the hard
sites.

**Control.** The denominator and best frame come only from common inputs and are
frozen. Coherence is gain-invariant. A future replacement M1 must catch softening.
Removing the smallest contiguous run of at least three frames that covers at least
10% of the eligible target depth must reduce measured coverage by at least 5
percentage points and place the longest failure in that slab. A complete-stack null
may move coverage by at most 1 point. M1's future replacement remains the separate
resolution gate.

### M6 — recoverable highlight and shadow retention

**Publication role: MANDATORY DISCLOSURE.** Full M6 must be measured and published;
its miss is reported as `DISCLOSURE MISS` when every owner gate passes.

**What it measures and why.** A focus stacker sees different blur discs and sometimes
different valid exposures at each pixel. It should recover an unsaturated contributor
instead of clipping a highlight or crushing a shadow.

**Input.** Foam, Maldon salt, ISO-100 battery, highly angled ruler, and qualifying
bright sites from the grid/fabric captures. Each scored capture needs at least 20
non-overlapping highlight/shadow tiles and 10,000 recoverable pixels.

**Exact computation.**

1. A high-rail pixel is recoverable when at least one common input is `>=0.98` and at
   least one aligned input lies in `[0.20,0.95]`. A low-rail pixel is recoverable when
   at least one input is `<=0.02` and another lies in `[0.05,0.80]`.
2. `clip_high` is the fraction of recoverable high pixels with output
   `>=65534/65535`; `clip_low` is the mirrored fraction `<=1/65535`.
3. On recoverable-highlight tiles, compute M5’s `rho_best` against the independently
   selected unsaturated source; report the median as highlight-detail retention.

**Success.** **SCORECARD ADDITION:** `clip_high<=0.001`,
`clip_low<=0.001`, highlight-detail retention `>=0.90`, and none of the three values
is worse than the best comparator.

**Known defeat.** Darkening or compressing the output avoids clipping; excluding the
brightest pixels changes the denominator; smoothing hides clipped texture.

**Control.** Recoverability is input-defined. The tone ramp requires unit gain, while
mid-grey gain must remain within `0.5%` and the 99th-percentile linear luminance within
`1%` of the common reference. A plant clipping exactly 1% of recoverable pixels must
be recovered within `0.1 percentage point`; a darkened arm must fail §1.3.

### M7 — colour fidelity

**Publication role: MANDATORY DISCLOSURE.** Full M7 must be measured and published;
its miss is reported as `DISCLOSURE MISS` when every owner gate passes.

**What it measures and why.** Frame-dependent white balance, per-channel focus
selection, clipping, and chromatic registration can make seams or move real colours
even when luminance detail is good. D7 requires colour/print polish but supplies no
colourimetric score or bar (`2026-08-sota-path.md` lines 1682–1689).

**Input.** A missing, required tilted ColorChecker capture under a measured illuminant,
with published patch values, grey card, darks, and enough focus travel to place patches
on different elected frames. At least 24 valid patches, including all neutral patches
and at least 12 chromatic patches, must survive. Fabric, foam, battery, and ruler
remain seam diagnostics only and cannot substitute for the target.

**The seam arm needs its own stimulus.** A flat or untextured ColorChecker capture
cannot be presumed to exercise focus transitions at all, so it cannot populate the
boundary-seam term in step 4. That arm additionally requires a **dedicated tilted,
textured colour-seam coupon** with an independently measured, pre-output Lab-D50
reference raster. It may share a physical composite target and lighting session with
the patch arm. If a combined target cannot meet the frozen population floors in step 4,
shoot a separate seam capture — **do not relax the floors after seeing outputs.**

**Exact computation.**

1. Convert the common linear output through its frozen ICC to CIELAB D50.
2. Erode each target patch by 20%; use the median Lab value.
3. Compute CIEDE2000 to the traceable patch value. No per-output matrix, white-balance,
   exposure, or gamut fit is permitted.
4. **Boundary-seam population.** Use the dedicated tilted, textured colour-seam coupon
   and its independently measured, pre-output Lab-D50 reference raster. From the common
   inputs only, compute normalised 32×32-tile Sobel focus curves, three-point peak
   coordinates, and the one-pass 3-MAD affine focus field specified by M145. Its
   half-integer contours, dilated normally by one quarter focus-step pitch, are clipped
   to single 20%-eroded colour regions and sampled every 12 native pixels from a fixed
   half-spacing phase. At each site, search the frozen corridor with paired 3×9
   median-Lab windows and score the maximum CIEDE2000 difference between the two sides'
   local reference-corrected colour errors. Freeze and hash the manifest before opening
   outputs. Require at least `1,000` sites, `10` contours, `50` sites per contour, four
   neutral regions, and eight chromatic regions. Any deficient or empty population is
   `UNMEASURED_CAPTURE_INADEQUATE`, never PASS. Output defects are scored as infinity,
   not masked. The p99 is nearest-rank at one-based rank `ceil(0.99*N)`. No
   candidate/comparator output or strehl internal map may affect membership.
5. Verify that every scored deliverable embeds the byte-identical frozen ICC and
   carries 300-DPI resolution tags.

**Success.** **SCORECARD ADDITION:** median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum
`<=3.0`; on the frozen M145 input-only seam population, nearest-rank boundary-seam p99
`<=1.0` **and** no connected contour segment has three consecutive sites `>1.0`; an
empty or sub-minimum population is `UNMEASURED_CAPTURE_INADEQUATE`; ICC/300-DPI
conformance `100%`; and no summary is worse than the best comparator.

**Known defeat.** Desaturation flatters neutral-only data; fitting a matrix to the
same patches makes the checker carry the answer; tone/gamut mapping can trade
luminance for chroma.

**Control.** All chromatic and neutral patches score; no output-specific fit is
allowed. A 10-degree hue rotation and a 5% desaturation must fail at least 90% of their
affected patches; an identity colour transform must pass. The absent target makes the
current honest state `UNMEASURED`, not “close enough on natural objects.”

### M8 — invented values / source-hull certificate

**What it measures and why.** A merge or restoration stage can ring beyond any
observed linear sample. The proposal explicitly requires a per-file hull census of
`0.0000%` or coordinates for every exception
(`2026-08-sota-path.md` lines 1579–1584).

**Input.** Every scored quality capture. Before a scored run, commission the
instrument on the development-only flat 1/2.5/6-second high-resolution-slide stacks.
This use consumes no holdout. The active placement, including the cover transform, and
the linear decoded source planes are evidence inputs.

**Exact computation.**

M8 has two mandatory censuses because a final broad hull can hide an interpolator
excursion that another frame happens to bracket. M8-R is a **SCORECARD ADDITION**;
M8-O is the proposal's per-file invariant.

1. **M8-R, per-frame resampler hull.** At the linear pre-merge and pre-clamp `f32`
   boundary, record the actual gathered value `r_k(x,y,c)` for every geometrically
   valid placed frame, sample and channel. The trace contains values and coordinates,
   never a producer-computed hull or pass flag.
2. Independently map each output sample centre through the frozen placement. For
   Catmull-Rom, read the exact 4x4 discrete source support used at that coordinate and
   define `lo_k=min(support_16)` and `hi_k=max(support_16)`. Boundary coordinate
   clamping must be reimplemented from the written resampler contract, not called from
   strehl.
3. Let
   `tau_R = 8*ULP_f32(max(1, abs(lo_k), abs(hi_k)))`. Count an M8-R violation when
   `r_k < lo_k-tau_R` or `r_k > hi_k+tau_R`. Sensor noise is already present in the
   16 observed support samples, so temporal `5*sigma` is not a legitimate tolerance.
   Here `ULP_f32(z)` is the distance from positive `f32` value `z` to its next
   representable value.
4. **M8-O v1.4, superseded final-output hull.** At the same linear coordinate and channel, define
   `lo_O=min_k(lo_k)` and `hi_O=max_k(hi_k)` over every geometrically valid input
   frame, never strehl's elected contributor list. Compare the actual final linear
   output `O` to this interval. For a 16-bit serialized audit only, add exactly
   `0.5/65535` quantisation tolerance to the largest contributing `tau_R`; no tone,
   noise or scene-adaptive tolerance is allowed.
5. For both censuses report denominator, violation count and fraction, maximum signed
   excess, and every violating `(capture, frame, x, y, channel)` coordinate. Separately
   report the one-frame/reference-frame arm: under `crop`, an integer identity
   placement must be a source copy within `tau_R`.

**Success.** **PROSPECTIVE M8-O v1.5 BAR:** representable-domain final-output
violation fraction exactly `0.0000%`. **SCORECARD ADDITION (M8-R):** resampler
violation fraction exactly `0.0000%`; the crop/reference identity arm also has zero
violations. A missing pre-clamp trace or an unrecommissioned M8-O v1.5 checker is
`UNMEASURED`, not a pass. The v1.4 M8-O computation and its exact-zero bar are
retained below only as superseded history.

> ### M8-O v1.5 — prospective bar replacement, registered before the deciding number exists
>
> **The v1.4 M8-O bar above was proven impossible to satisfy as written, and it
> is retained here rather than deleted.** The output is normalized `u16` on
> `[0,1]`. At `977,684` required census coordinates the hull has
> `lo - tolerance > 1`, so the set of representable values satisfying the hull
> condition is **empty**; every representable value is
> charged a violation regardless of what the resampler does. The census was
> pricing a limit of the output container as an algorithmic defect.
>
> **M8-O v1.4 superseded figure:** `1.326144%` was read against the v1.4 bar, which has been shown impossible as written; see `docs/research/M136-m8o-bar.md` (commit `7befe55c`).
>
> **The M8 axis verdict remains `FAIL`, independently of that superseded figure.**
> M8-R measured `1.030569%` against its achievable exact-zero bar; M166 confirms
> that a convex bilinear or direct-copy gather can satisfy M8-R
> (`docs/research/M166-bar-achievability.md`, "M8-R: ACHIEVABLE" clause). M8-R
> is the only produced-and-read score against an achievable bar.
>
> **Ruling on legitimacy.** A repair is legitimate rather than goalpost-moving
> only if it is versioned prospectively, keeps the denominator unchanged,
> projects the hull into the output domain, retains the M8-R failure, and still
> discriminates. It does discriminate: under the repaired v1.5 predicate a clean
> bilinear kernel measures exactly `0/74,173,536`, independently zero in R, G,
> and B (`experiments/M136-m8o-bar/analysis.json`, `bilinear_aggregate`), while
> the shipping Catmull-Rom kernel does not clear the diagnostic reanalysis. The
> latter is not promoted to a score. A repaired bar that the shipping code passed
> trivially would be a worse outcome than an impossible one.
>
> **Normative text.** The v1.5 bar is § 6 of `docs/research/M136-m8o-bar.md`,
> pinned at git blob `86291032355f1d6466e2357b1224d78d9716c80c`
> (commit `6712449e9defdd93e301c6ed5dcd949a3c17c4b6`). It is referenced rather
> than copied so that this bar has exactly one canonical site and cannot drift
> between two transcriptions. **M8-R is unchanged by this replacement.**
>
> **Preregistered decision rule, fixed before the number exists.**
> `experiments/M136-m8o-bar/clamped-m8o-preregistration.json`, protocol
> `"M136 clamped-Catmull-Rom representable-domain M8-O v1"`, pinned at blob
> `4d13bd2dfa00c7c7534e5c6a6b4390627ac789aa`:
>
> - **PASS iff every capture has `V=0` and aggregate `V=0`.**
> - `FAIL iff aggregate V>=1`. `V=40` is a FAIL.
> - Nonzero floor: **none**. *"No empirical or statistical allowance may be
>   introduced after observing the result."*
> - The candidate clears M8 only if M8-O `V=0`, M8-R `V=0`, **and** the
>   crop/reference identity arm `V=0`.
> - Seven named conditions force `UNMEASURED`, so a voided run is a defined
>   outcome and not a judgement call.
>
> **Status: `UNMEASURED`.** The replacement checker was corrected at `e5489d64`
> but has not been independently recommissioned, so no v1.5 M8-O score exists.
> The clean bilinear `0/74,173,536` result is achievability and discrimination
> evidence, not a candidate score. A separate clamped-kernel diagnostic has
> `0/6,131,678,976` M8-R violations, but M8-R zero does not imply M8-O zero because
> the clamp changes the gathered values supplied to the merge. No old Scale-domain
> count is registered as the expected value because M130 moved output to compact
> Crop coordinates. No diagnostic Catmull-Rom M8-O count is promoted.


**Current cover hypothesis.** The v1.3 definition was too weak: its all-frame hull and
`5*sigma` tolerance could pass Catmull-Rom overshoot if another frame bracketed the
excursion, merge/clamping removed it, or the noise tolerance absorbed it. The default
Catmull-Rom kernel has negative lobes and explicitly permits hard-edge overshoot, while
`cover=scale` resamples even the identity reference placement. Therefore scale-induced
overshoot is plausible but not yet measured. M8-R will catch it at the stage where it
is created; M8-O determines whether it survives to the deliverable. This is
sharpening-independent source support, not a resolution statistic.

**Known defeat.** Final clamping can erase M8-O evidence; a broad all-frame hull can
bracket a per-frame excursion; a producer-supplied contributor mask or hull can omit
the disproof; and destructive clipping can force a zero rate.

**Control.** The checker is a separate implementation that reads source planes,
placements and raw value traces and imports neither strehl's sampler nor its
contributor/hull code. A synthetic hard step at a frozen fractional phase must cause
at least one Catmull-Rom M8-R violation; copy and convex-bilinear nulls must produce
zero. Every sample deliberately planted at `hi+32*tau` or `lo-32*tau` must be found.
The crop/reference identity arm must produce zero. A future M1 and the retained M4
flat-power-plus-transfer component are the owner-gate controls against buying the hull
result through sharpening, attenuation, or clamping. M5 and M6 remain mandatory
disclosures that expose any accompanying coverage or dynamic-range cost. While M1 is
absent, M8 may prove only this internal invariant, not SOTA.

### M9 — acuity and effective-sample certificate calibration

**Definition status: DEFINITION BLOCKED
(`DEFINITION_BLOCKED_M1_TRUTH`).** M9 has no admitted producer of `truth_valid`.
With 500 claimed cells, a manifest labelling all 500 truth-valid yields
false-certification `0%` and true coverage `100%`; the same bytes with all 500
labelled truth-invalid yield false-certification `100%` and true coverage `0%`. The
current text cannot choose between those manifests.

The D8/FRC channel cannot fill this hole: common post-noise blur or sharpening leaves
that statistic invariant, so it cannot establish delivered acuity. M9 remains
**DEFINITION BLOCKED** until the scorecard registry admits an independent,
candidate-specific acuity-truth predicate. M1 is the currently specified and
physically actionable route to that truth, not the unique mathematical anchor; a sufficiently powered independent
same-resolution reference could in principle normalize relative transfer, but no
such route is admitted today. No threshold invented inside M9 may substitute for
external truth. The exact downstream contract below is registered now but is not a
usable bar until that first input exists.

**What it measures and why.** The proposal’s differentiator is not merely a good
image, but a file that says where and at what frequency it is trustworthy. A
certificate generated and checked by the same noise/focus model is the repository’s
signature cancellation defect. D2 proposes a CRLB channel and an empirical channel
(`2026-08-sota-path.md` lines 1554–1573), but the proposed same-capture split channel
is no longer admissible.

**Capture and prior-rule status.** All six new slide stacks are development-only, and
IBIS independently disqualifies them as repeat-pair truth. The burned grid may
commission but may not score; same-frame odd/even halves are forbidden; and bee
same-focus repeats alone cannot close the depth-stack certificate claim. The
withdrawn v1.3 `D>=1 && FRC>=1/7` rule is not truth in v1.10.

**Required truth and product contracts.** Before any candidate output is opened, the
truth producer must freeze a sampling manifest of exactly 1,000 independently
located physical `(site,band)` cells: 100 independently source-positive cells and
100 independently source-negative controls in each of `[0,.05)`, `[.05,.10)`,
`[.10,.15)`, `[.15,.20)`, and `[.20,.25] cyc/native px`. A physical site can occupy
one band only.

After output is frozen but while blinded to the candidate certificate, the
independent truth producer appends, without changing the population, the
candidate-specific `truth_valid` result, truth amplitude, truth variance, and
independently calibrated single-frame variance. Every row also contains stable
`cell_id`, capture and repeat IDs, integer output coordinate, and band.
Source-negative controls must remain truth-invalid. At least 500 cells must be
independently truth-valid or the candidate fails `INSUFFICIENT_DELIVERED_ACUITY`; the
population is not resampled to manufacture that count. M1 must define the physical
target, higher-sampling reference, candidate-preservation statistic, threshold, and
uncertainty by which those fields are admitted.

The candidate must emit hash-bound, native-grid arrays with one plane per band:

- `valid`: unsigned byte, only `0` or `1`;
- signed band-amplitude estimate: IEEE binary32;
- one-sigma uncertainty in the same amplitude units: IEEE binary32;
- `n_eff`: IEEE binary32.

The output also contains the rendered colour-output hash to which the certificate
applies. Shape mismatch, a missing plane/cell, any other validity code, or
non-finite/negative sigma or non-finite/non-positive `n_eff` at a claimed cell is a
candidate failure. Certificate planes may not be resampled; the truth manifest names
native integer coordinates. Validity must be monotone in frequency: if band `k` is
invalid, every higher band is invalid. The highest valid band is the shipped acuity
value.

For a cell, `claim_i` is exactly `valid_i==1`. Let `C` be claimed cells, `T+`
truth-valid cells, and `T-` truth-invalid cells:

- false-certification point rate is `|C intersect T-|/|C|`; an empty `C` is `+inf`;
- true-coverage point rate is `|C intersect T+|/|T+|`;
- at least 500 cells must be claimed;
- false-certification point rate and its one-sided 95% Wilson upper bound must both
  be `<=0.01`;
- true coverage and its one-sided 95% Wilson lower bound must both be `>=0.90`.

For every claimed truth-valid primary-repeat cell, define

`e_i=estimate_i-truth_amplitude_i`,

`v_i=sigma_i^2+truth_variance_i`, and

`h_i=1.959963984540054*sqrt(v_i)`.

Coverage is `|e_i|<=h_i`; point coverage must lie in `[0.93,0.97]`.

The product's `n_eff` has one operational meaning. Compute
`n*_i=single_frame_variance_i/sigma_i^2` in binary64 and round it once,
ties-to-even, to binary32. The emitted `n_eff` bit pattern must equal that binary32
value. Zero sigma or overflow is invalid, not infinite effective sample size. Every
claimed cell must also have `n_eff>=1.0`; a certificate wider than its independently
calibrated single-frame uncertainty is not a valid stacked-acuity claim.

**Exact repeat/decile calibration.** The corpus must provide two independently
captured, identically configured repeat outputs at sweep width 4 and two at sweep
width 10 for every truth-valid claimed cell. Run every calculation and bar separately
for sw4 and sw10; a pooled-across-width result is diagnostic only and both widths must
pass. Let one width's repeat amplitudes and predicted variances be
`(a_i1,s_i1^2)` and `(a_i2,s_i2^2)`. Define

`d_i=(a_i1-a_i2)/sqrt(2)` and
`p_i=(s_i1^2+s_i2^2)/2`.

Sort cells by `(p_i,cell_id)`. Decile `j=0,...,9` is the half-open index range
`[floor(jN/10), floor((j+1)N/10))`; ties are never kept together and no decile may be
empty. In each decile,

`V_emp=sum((d_i-mean(d))^2)/(n_j-1)`,

`V_pred=mean(p_i)`, and `R_j=V_emp/V_pred`.

At least nine of ten `R_j` must be in `[0.90,1.10]`. The pooled ratio, computed by the
same sample-variance and arithmetic-mean formulas over all `N`, must also be in
`[0.90,1.10]`. Two or more failing deciles, a failing pooled ratio, or any invalid
term sets `material_predicted_vs_empirical_disagreement=true` and fails M9.

The model/CRLB channel supplies `sigma` and the single-frame variance; the independent
repeat channel supplies `V_emp`. The required single-image decorrelation channel
remains a separately published diagnostic/control and may veto a broken
implementation, but it may not produce or override `truth_valid`.

**Loose-direction closure.** Universal refusal has zero true coverage and fewer than
500 claims. Universal validity fails on the 500 truth-invalid cells. A constant or
blurred output cannot supply the required 500 candidate-specific independently
truth-valid cells and calibrated amplitude intervals. Arbitrarily wide intervals fail
the `n_eff>=1` floor and upper coverage bound; arbitrarily narrow or fabricated
uncertainty fails coverage and repeat variance. Fabricated `n_eff` fails the exact
variance identity.

**Current blocker and controls.** M9 waits on a commissioned independent
higher-sampling M1 acuity-truth producer; an exactly balanced source-positive/control
manifest; fresh dense checker-only material; two matched sw4 and two matched sw10
IBIS-off repeats; independent repeat truth; dark/FPN calibration; and the
acuity/sigma/`n_eff` product. Truth may never come from strehl's model channel.
Multiplying only reported variance by 1.25 must move the variance ratio outside its
pass interval. No current above-`0.25 cyc/native px` reading satisfies decision rule
7, so every such band remains `UNLICENSED_GT_0.25`.

### M10 — physical depth product

**Definition status: PARTIALLY DEFINED after M163 and M166; still DEFINITION
BLOCKED.** M163 (`736e905a`) repaired uncertainty handling. M166 (`832a2e85`)
then froze the flat-null reduction, the stored-encoding description, the quota
selection and the synthetic populations — so this row is no longer "pending
M166". Audit M186 found that three of those four pieces are descriptions rather
than operative definitions: the quota hash **byte order** is unspecified and the
two orders select different tiles (`['00000003','00000005','00000007']`
big-endian versus `['00000002','00000000','00000007']` little-endian), the
origin divisor `N` is undefined, the manifest hash algorithm/schema and
contract-failure verdict mapping are absent, and the synthetic renderer,
PRNG-to-seed mapping, scored seed and certificate acceptance are unfixed. Only
the flat-null reduction is operative. The existing downstream draft below is
therefore still not an operable scorecard bar and may not be scored until those
choices are frozen **before** any candidate output exists. No M10 threshold or
computation is changed in this revision.

**What it measures and why.** The proposal calls for depth in physical units, not an
unlabelled frame index (`2026-08-sota-path.md` lines 192–197). A focus stacker’s depth
map is useful only if its ordering, scale, and uncertainty survive an external
geometric truth.

**Input.** A **fresh, untouched tilted-ruler unit** whose camera-relative pose and
angular uncertainty are measured externally and frozen before any output is read.
The three original `10.26`-degree stacks are **burned** — M-PHASE0-CURV and
M-PHASE0-LCA already read outcomes from them — and are development-only. Also the
flat battery null, and an
independently implemented non-planar synthetic two-layer target whose latent depths
are hidden from the estimator. The ruler’s 1/64-inch markings set lateral scale. The
fresh tilted-slide unit is development-only planarity/order commissioning and cannot
be promoted to score evidence after diagnostic use. At least 20 non-overlapping ruler
strips and 10,000 target pixels must qualify.

**Exact computation.**

1. Map ruler ticks to tick arclength `s` measured along the inclined ruler face.
   External truth is `z_true = s*sin(theta_ext)` after one fitted origin only;
   equivalently `z_true = x*tan(theta_ext)` **where `x = s*cos(theta_ext)` is the
   externally calibrated lateral projection**. Those two forms agree only under that
   definition of `x`; leaving `x` undefined was a real ambiguity (M154), because
   reading `x` as arclength instead of projection inflates the truth slope by
   `1/cos(theta_ext)`. `theta_ext` must come from
   a measurement independent of image focus and be frozen with uncertainty small
   enough to contribute at most `2.5%` slope error. The README’s “approximately
   10.26 deg” is a candidate value, not by itself traceable truth. No slope is fitted
   from strehl’s depth output.
2. Convert predicted depth to the same units using the declared capture model.
3. Report valid-pixel fraction, Spearman rank correlation, median and p95 absolute
   error in both micrometres and measured focus-step equivalents, and fitted
   predicted/true slope ratio.
4. On the flat battery, report p95 depth range. On the synthetic two-layer target,
   report layer confusion and boundary bias separately.

**Success.** **SCORECARD ADDITION:** valid target pixels `>=99%`; rank correlation
`>=0.99`; median absolute error `<=0.5` focus step; p95 `<=1.0` step; ruler slope error
`<=5%`; flat-null p95 range `<=0.5` step; synthetic layer confusion `<=1%`.

**Known defeat.** A hard-coded plane passes a tilted ruler; a checker using the same
breathing/focus model repeats its assumptions; a smoothness prior hides layer errors.

**Control.** The non-planar hidden-truth target defeats a plane, and the physical
ruler defeats a purely synthetic checker. Truth construction may not import strehl’s
focus or breathing model. Permuting the synthetic depth labels must force rank
correlation below `0.5`; an exact truth map must pass every bar. If the ruler angle
cannot be independently bounded tightly enough for the 5% slope bar, physical depth
is `UNMEASURED`.

### M11 — wall-clock throughput

**Definition and measurement status.** M11 is now well-defined, but no current
measurement is admissible. Its common-merge gate is
`UNMEASURED_COMPARATOR_QUALIFICATION`: admitted M1 and repaired M2 qualification,
required licensed-comparator outputs, and a fresh hash-bound fork build are absent.
Its absolute product-native timings are separately quarantined. `docs/STATUS.md`
§2.9.55 records three host samples averaging `93.2%` CPU with the agent host process
as the top consumer; an absolute wall time under that load carries an uncontrolled
covariate. Any absolute timing figure is quarantined on arrival until reproduced on a
quiet host or restated as a within-run ratio in which load cancels. A defined bar is
not thereby a measured bar.

**What it measures and why.** A focus stacker must turn a bracket into the delivered
master, not merely time one merge kernel. The proposal registers `>=2x` comparator,
`<=0.15 s/frame` CPU, `<=0.06 s/frame` hybrid, cold overhead `<=20 s`, and a
100-frame post-shutter latency `<=10 s`
(`2026-08-sota-path.md` lines 1957–1985).
It separately requires default quality work to remain within roughly `2x` the frozen
pre-feature wall clock (`2026-08-sota-path.md` lines 1648–1652).

Run two separately reported arms. The **common-merge arm** starts every program from
the common linear TIFFs and alone determines the `>=2x` publication-gate comparator
ratio. The **product-native arm** starts Strehl from the original ARWs through its
shipping path and measures the absolute CPU, hybrid, cold, live-latency, and
baseline-regression bars for end-to-end product statements. Neither arm may borrow or
substitute a value, setting, or verdict from the other, and product-native values
cannot satisfy or alter the M11 publication gate.

The publication comparator ratio uses warm-cache common TIFFs from the same volume;
cold comparative values are reported but cannot establish the `>=2x` claim. In the
product-native arm, report decode wall/CPU time separately from fold and write time,
but never subtract decode from the product result. If a comparator exposes no
trustworthy stage timing, its native-RAW timing is diagnostic only.

**Exact timing campaign.** Use three frozen common-input cells:

- `C33`: the first 33 ordered frames of `bee-1-cpl`;
- `C105`: all 105 ordered frames of `coffee-bean`;
- `C299`: all 299 ordered frames of `bee-1-cpl`.

Every program receives identical ordered uncompressed 16-bit linear ProPhoto RGB D50
TIFF bytes on the same volume, at native dimensions, ICC, crop, and output contract.
Candidate CPU, hybrid, and baseline settings are each invariant across
`C33/C105/C299`; comparator mode identity/settings are invariant across every capture
on which that mode is evaluated.

For an ordinary invocation, read QPC immediately before creating the root process.
Stop only after a Windows Job Object reports zero live root or descendant processes;
the output TIFF and invocation manifest have both been closed and flushed; and both
have been reopened, structurally validated, and SHA-256 hashed. Decode/load,
registration, merge, colour, write, asynchronous children, validation, and hashing
are inside the boundary.

Store start/stop as integer QPC ticks plus the integer QPC frequency; subtract ticks
before converting to binary64 seconds. Retain every root and descendant image path
and file hash. Requiring only root-process exit is invalid.

Each cell has one unscored warm-up and six scored sweeps. Odd sweeps use the frozen
forward setting order; even sweeps use its exact reverse. A failed condition or member
invalidates the entire paired sweep and campaign; no selective rerun or outlier
deletion is allowed. Report all six values and minimum, median, maximum, range, MAD,
scaled MAD, sample standard deviation, and relative range, together with CPU time,
busy fraction, GPU utilisation, bytes read/written, and per-stage banners. The score
uses the minimum valid wall time.

Preflight requires a fixed power plan and a hash-bound thermal probe. A predeclared
allowlist contains only OS display processes plus the timed Job Object; observing any
other GPU-using process invalidates the campaign. Over a 60-second preflight,
`CPU_busy=(DeltaKernel-DeltaIdle+DeltaUser)/(DeltaKernel+DeltaUser)` must be
`<=0.15`. During a run,
`external_busy=max(0,total_nonidle_CPU_time-JobObject_CPU_time) /
(logical_processor_count*wall_time)` must be `<=0.10`. CPU, thermal, throttle, and
GPU-process telemetry is sampled every 10 ms; the campaign manifest predeclares the
allowed start-temperature interval and requires no hardware throttle flag. Input byte
hashes are checked before and after every invocation. A missing telemetry sample or
condition miss invalidates the campaign.

**Comparative statistic, qualification, and ties.** For each capture `c`, let `S_c`
be Strehl's minimum 16-worker wall time. For every quality-qualified comparator mode
`m`, let `T_mc` be its minimum. Define

`T_c=min_m T_mc`, `R_c=T_c/S_c`, and
`R_pool=sum_c T_c/sum_c S_c`.

The fastest-mode tie is product ID then mode ID. Strehl must have `R_c>=2.00` for each
of `C33`, `C105`, and `C299`, and `R_pool>=2.00`. The per-capture envelope is
intentional: no slow capture or favourable global mode can hide a miss.

A comparator mode qualifies only when one binary/settings fingerprint passes the
common-input transfer/geometry contract, M1, M2, M3, M8, and the retained M4
flat-power-plus-transfer component on its frozen quality-corpus outputs; every
reading is taken from the corresponding hash-bound output bytes and no timing-cell
setting may differ. Timing outputs must independently pass the common output contract
and every quality control applicable to their captures. Required arms are licensed
Zerene PMax, licensed Zerene DMap, and the fresh best-known-source fork rebuild;
every obtainable Helicon A/B/C arm also enters. Missing required arms, an unbound
fresh fork, or absent admitted M1 makes M11
`UNMEASURED_COMPARATOR_QUALIFICATION`; it is not permission to time an unqualified
mode.

For the retained cross-worker component, scored repetition 1 is the predeclared
canonical output. At each N, the complete TIFF file SHA-256 and canonical
decoded-pixel SHA-256 must each be identical across worker counts 1/2/4/8/16. TIFF
metadata must therefore be deterministic; invocation manifests are not part of the
compared TIFF. There is no cross-N identity requirement.

**Exact product-native disclosures.** These cannot rescue or fail the common-merge
publication verdict, but each receives a separate `PASS`, `FAIL`, or `UNMEASURED`:

- CPU: `min(wall)/N<=0.15 s/frame` at each N=33/105/299, workers fixed at 16.
- Hybrid: `min(wall)/N<=0.06 s/frame` at each N under one frozen hybrid mode. An
  absent backend is `UNMEASURED_NOT_IMPLEMENTED`, not a pass.
- Default baseline: `min(candidate_warm)/min(baseline_warm)<=2.00` at each N; only
  the build hash may differ.
- Cold: six predeclared pairs at each N for both candidate CPU-16 and the frozen
  hybrid mode. Each pair begins with an actual reboot identified by a unique boot-ID
  receipt, runs cold, then runs a warm mate with identical inputs/settings and fresh
  private output/temp paths. Every `cold_j-warm_j<=20.0 s`; an “equivalent reset” is
  not admissible.
- Live first 100: use the frozen shipping-default product mode and a new signed
  acquisition trace containing monotonic shutter-close and durable
  file-close/availability timestamps for every frame. Prestart the frozen stacker,
  reveal each hash-verified file only at its recorded availability offset, and
  prohibit pre-availability access. The epoch is **shutter close of frame 100**, not
  file-100 availability. After one unscored warm-up, all six scored replays must be
  valid and `max(finalized_output_time-shutter_close_100)<=10.0 s`.

**Loose-direction closure.** A no-op, constant output, or low-quality fast mode cannot
enter the timing denominator because the identical binary/settings fingerprint must
qualify on hash-bound quality outputs and timed outputs must pass their applicable
controls. Returning before a child or asynchronous write finishes cannot shorten the
measured interval. Worker-specific cheap outputs fail full-file and pixel identity.
Capture-wise and pooled 2x bars prevent averaging one slow case away.

**Commissioning control.** The warm uncompressed common-merge arm controls storage
and RAW decode; the product-native arm prices strehl's actual decode bottleneck rather
than hiding it. A planted 1-second sleep must add `1.00+/-0.05 s`; a child that writes
after parent exit must remain inside the timer. Common-merge quality results are
published beside timing; product-native values remain separate and cannot qualify
M11.

### M12 — memory, determinism, and scaling invariance

**Publication role: MANDATORY DISCLOSURE.** Full M12 must be measured and published.
Only equality of both the complete TIFF file SHA-256 and canonical decoded-pixel
SHA-256 across the fixed-width 1/2/4/8/16-worker common-merge ladder, with the
16-worker common-merge output meeting M11, is retained as M11's anti-cheat component.
Product-native fixed-worker repeats, memory, N-scaling, and N-mod-4 remain disclosure
bars and do not independently gate the owner's verdict.

**What it measures and why.** Deep stacks must remain bounded and reproducible.
Worker-count dependence or hidden spill can make a fast-looking configuration
non-product behaviour.

**Input.** The same N=33/105/299 and worker-count matrix as M11.

**Exact computation.**

1. Run the comparative common-TIFF arm and native-ARW product arm separately. The
   absolute 6-GiB, scaling, determinism, and N-mod-4 bars apply to the native product
   arm; comparative memory is reported but is not a substitute.
2. Sample process-tree private committed bytes and working set every 10 ms; report
   peak committed bytes.
3. After one warm-up, hash the highest-precision delivered bytes from each of the six
   scored repetitions at worker counts 1/2/4/8/16 for each registered N. Do not hash
   a later 8-bit proxy.
4. **M12-D, fixed-worker determinism:** for each `(N, worker_count)`, count distinct
   hashes across its six repetitions.
5. **M12-S, cross-worker scaling invariance:** for each N, count distinct hashes
   across the canonical outputs at worker counts 1/2/4/8/16.
6. Compute warm-memory ratio `peak_N299/peak_N33`.
7. For N=96–99, divide warm wall time by N and compute
   `(max-min)/min`.

**Success.** The proposal bars are warm peak `<=6 GiB` and byte invariance. The
**SCORECARD ADDITIONS** that make “flat” numeric are
`peak_N299/peak_N33<=1.10` and N-mod-4 per-frame spread `<=2%`. M12-D requires
exactly one distinct hash in every fixed-worker six-run cell. M12-S requires exactly
one distinct hash across all five worker counts at every N. A product may pass M12-D
while failing M12-S; the two verdicts must never be conflated.

**Existing-evidence ruling.** The repository contains strong mechanism evidence but
not a scorecard reading. `byte-freeze.rs` says changing
`STREHL_PYRAMID_WORKERS` changes reduction order and moves 1 DN on about 0.2% of
pixels; `merge_cmd.rs` records 2 versus 7 workers differing on 0.2573% of a 205-frame
stack, maximum 1 DN (`byte-freeze.rs` lines 512–515; `merge_cmd.rs` lines
5322–5329). Both are outside the registered N/worker matrix. The reported
18-run sweep has six stable repetitions at each of 1/4/8 workers and three different
cross-worker hashes; its `C6765BFA...` arm matches the registered N=20
`coffee-bean-20-gate2-pyramid` byte-freeze, not N=33/105/299. That row freezes
`env_align=0`, `alignment_mode=off`, an empty scratch cache, and a pyramid path whose
own banner says photometric gain, clip census, outlier rejection, halo correction and
through-focus statistics were not applied. It also lacks workers 2 and 16 and a
scorecard command/output manifest proving the hashed artifact is the registered
highest-precision native product deliverable. Therefore it is
**diagnostic M12-D PASS / diagnostic M12-S FAIL**, while both formal sub-bars and M12
overall remain **UNMEASURED**.

**Known defeat.** Disk spill lowers RAM, monitoring only the parent misses workers,
and nondeterminism can disappear if outputs are rounded before hashing.

**Control.** Record process-tree memory, temp-file bytes, page faults, and child
lifetime. Allocate a planted 7-GiB child buffer and require the monitor to exceed the
bar; write one random output LSB and require the hash gate to fail. Hash the highest
precision common deliverable, not a later 8-bit proxy.

**Remaining registered run.** Reserve one uninterrupted **120-minute quiet-host
window**. Run native ARWs at N=33/105/299 with workers 1/2/4/8/16, one warm-up then
six alternating-order scored repetitions per cell, hashing every deliverable and
sampling the whole process tree every 10 ms. Run N=96/97/98/99 at 16 workers with the
same warm-up/six-sweep timing protocol for the modulo bar. This single run supplies
M12-D, M12-S, peak memory, `peak_N299/peak_N33`, and N-mod-4 spread; do not spend a
separate host window rediscovering the already-understood reduction-order mechanism.

## 5. Metrics deliberately rejected as primary evidence

1. **Raw band power, coarse-normalised band power, extreme-zone rank, acutance,
   MTF50, and slanted-edge SFR:** post-hoc sharpening or a tone curve can raise them
   without adding information. SFR remains a target/presentation diagnostic labelled
   unsafe; it cannot decide M1.
2. **The v1.3 `f_licensed` / `S_25` composite:** dropped. The cutoff is blind to both
   physical blur and genuine improvement. Native `S_25` moves `1.028294x` under
   USM on the superseding 64-site battery, outside the unchanged 1% bar; the earlier
   24-seed `0.995819x` apparent pass is underpowered and superseded. It also moves
   `18818.9045x` under a logistic tone curve, spans `0.004972x`–`10.381863x`
   under noise, and is angle-dependent. Tone-hardened derivatives reverse the optical
   controls. A control defeated every form, so it cannot remain a requirement merely
   because no replacement exists.
3. **Same-frame split-half FRC/SNR:** dropped. The proposal describes the halves as
   independent (`2026-08-sota-path.md` lines 1694–1733), but the commissioned lane
   found a common-mode adversary at `0.972099` and a null at `0.438734` against the
   `0.25` bar; reopening requires an independent repeated bracket, sensor-pattern
   subtraction, a non-degenerate partition, and a transferring tuner plant
   (`docs/STATUS.md` lines 156–198). M1/M9 therefore use repeated exposures only.
4. **SSIMULACRA2 / butteraugli on natural stacks:** the proposal names them
   (`2026-08-sota-path.md` lines 1525–1536) but supplies neither an all-in-focus truth
   image nor a bar. In this registered use, without an external model, prior, or
   reference, comparing two unknown renders does not create one.
   They may commission synthetic plants, but do not rank real outputs in v1.10.
5. **A single composite “SOTA score”:** weights would let noise purchase a halo or
   speed purchase lost depth. The proposal’s end-state is conjunctive.
6. **Natural-object colour agreement:** programs can agree and all be wrong. M7 waits
   for a traceable target.

## 6. Honest current position

No score below was produced under §§1–4. Historical measurements, including apparent
wins, are not imported into this table. In particular, the previous “17–27% detail
deficit” is withdrawn: the comparator arm carried `Contrast2012=+100`, and tone alone
explained 94.8%, 109.9%, and 267.1% of the apparent three-band gaps
(`docs/research/V-HEADTOHEAD2.md` lines 23–27 and 57–70). The correct present
competitive statement is **unknown**.

The fork column is explicitly `UNMEASURED` under blocker `(d)` until a fresh rebuild
of the best-known retained source revision exists under a pre-scoring commit pin, its
executable hash is frozen before rendering, and it successfully consumes the exact
common-input TIFF bytes. The historical archived fork output cannot populate this
column.

| ID | Metric | strehl | Zerene Stacker (PMax + DMap) | Fork (commit-pinned best-known-source common-merge rebuild) | Helicon Focus (when obtainable) | Current standing |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Sharpening-safe resolved information | **UNMEASURED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | CAND1 is killed; no admissible instrument or active bar remains, and fresh matched captures are absent. |
| M2 | Flat/defocused-ground noise | **UNMEASURED — INSTRUMENT VOID.** Product-native diagnostic DELIVER-V6 fractional box9 residual is `1.515208x` the historical archived fork output's median, with `0 of 12` sites below one; that output is not an admissible common-merge comparator. Blur improves the statistic to `0.571215x`, so it is not licensed for M2. | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | The adverse residual and blur-specificity failure are published, but no current value is a valid M2 verdict. |
| M3 | Halo / veil | **UNMEASURED_COMPARATOR_QUALIFICATION** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | M166 defines the population/statistic, but M1 qualification, required common-input comparator outputs, and profile-package/input-only warp evidence are absent. VEIL2 remains a build STOP, not an M3 score. |
| M4 | Artifact rate | **UNMEASURED_CAPTURE_INADEQUATE** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | M166 defines the retained flat-power/transfer component, but eligible medication/foam tiles, a separate development flat, materialized matrices/plants, and base/planted renders are absent. Full M4 remains a mandatory disclosure. |
| M5 | DOF coverage / failure rate | **UNMEASURED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | New tilted block advances development only; a replacement controlled-slide holdout remains absent. |
| M6 | Highlight/shadow retention | **UNMEASURED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | The current rail census is under-powered; detail, geometry and comparator arms are blocked. |
| M7 | Colour fidelity | **UNMEASURED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | LCA confirms an axial effect but licenses no correction and is not colour fidelity; traceable target absent. |
| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%` against the achievable bar of exactly `0.0000%`; M8-O v1.5 **UNMEASURED** because the corrected checker at `e5489d64` has not been recommissioned. Historical M8-O v1.4 `1.326144%` is **SUPERSEDED** because that bar was impossible as written. | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | **M8-R READ AND ADMITTED `76b3d9cc`.** M8-R is the only produced-and-read score against an achievable bar and remains a genuine axis-level failure. It is 100% attributable to the Catmull-Rom gather; bilinear gives `0/6,131,678,976` but costs 0.3404 dex of band detail. Under the repaired M8-O v1.5 predicate, clean bilinear measures `0/74,173,536`, independently zero in R, G, and B; this proves the bar discriminates but is not a v1.5 candidate score. |
| M9 | Certificate calibration | **DEFINITION BLOCKED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | `truth_valid` has no admitted independent candidate-specific producer through the current M1 registry route. M1 is the only currently specified and physically actionable route with an evidenced path today, not a unique mathematical anchor. M166's downstream contract is registered but cannot be used or scored. |
| M10 | Physical depth accuracy | **DEFINED; UNMEASURED after the M190 freeze** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | M163 repaired uncertainty handling; M166 froze the flat-null reduction and most validity rules; M190 then closed the four remaining definition gaps before any candidate output existed — quota digest order, origin divisor `N`, the product/manifest wire contract with a total fail-closed outcome map, and the hidden synthetic renderer with its one-draw scored-seed commitment. What remains is implementation and evidence, not definition: the product, integrated checker and physical truth are all absent. The existing downstream draft is non-operative and no M10 verdict exists. |
| M11 | Wall-clock throughput | **UNMEASURED_COMPARATOR_QUALIFICATION; absolute timing QUARANTINED** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | M166 defines the campaign, but quality-qualified required comparator outputs are absent. Full-process absolute QPC timings also await a quiet host under STATUS §2.9.55; D11/D15 component PASSes are not M11 scores. |
| M12 | Memory / determinism / scaling invariance | **FAIL** — peak `35.65745162963867 GiB` against `<=6 GiB`; five distinct TIFF and five distinct pixel hashes across workers `1/2/4/8/16` at every registered N; N-mod-4 spread `0.07618677189815302` against `<=2%`. `M12-D` **PASSES** on all 15 fixed-worker cells. `peak_N299/peak_N33` is **UNMEASURED_SAMPLING_COVERAGE**. | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | **READ AND ADMITTED `0c089f96`, and it required no licence.** M139 completed the registered matrix on a guarded host. M12-D is the first registered sub-property in this program to pass anything. M178 adjudicated the scorecard's reverse M11 dependency an unratified addition absent from the governing proposal; removing it converts M12-S from withheld to a measured FAIL, which lowers this axis rather than raising it. |

## 7. Corrections and gaps in the governing proposal

The proposal is authoritative about direction, but these parts cannot stand as written:

1. **D1/D8’s empirical spine is invalid.** Same-frame halves are not independent.
   The proposal itself priced fixed-pattern and quantisation correlation
   (`2026-08-sota-path.md` lines 1727–1733), but phase 0 showed the confound is verdict
   changing, not a small correction. Independent repeated captures replace it here.
2. **Slanted-edge SFR is not a SOTA resolution metric.** It is useful for chart
   qualification and presentation transfer, but sharpening can raise it after the
   fact. The proposal’s D1 pairing of FRC and SFR therefore cannot be used as two
   independent votes.
3. **The comparator prerequisite has two input contracts.** The operative required
   arms are licensed Zerene PMax, licensed Zerene DMap, and a fresh fork rebuild from
   the best-known retained source revision, pinned by commit before scoring, with its
   executable hash frozen before rendering; Helicon is added when obtainable. The
   common-merge track requires every included arm to receive the same hashed linear
   TIFF and is the sole source of publication-gate evidence. The archived fork output is historical /
   product-native-only diagnostic evidence: its `105` Lightroom-developed TIFF inputs
   and unbound producing binary make it inadmissible for common merge. The
   product-native track starts every current arm from one frozen source-ARW lineage
   while allowing each native stack path to consume the earliest linear
   representation it supports. It is labelled end to end and may support product
   statements only. Neither track may borrow from or be reported as the other.
4. **Colour fidelity is unspecified and presently uncapturable.** D7 discusses ICC,
   soft proof, and tone policy but names no traceable target, DeltaE computation, or
   bar. Natural subjects cannot close that gap.
5. **Perceptual metrics are named without a reference.** SSIMULACRA2 and butteraugli
   cannot rank natural all-in-focus outputs when no truth image exists.
6. **Several headline bars are placeholders.** Occlusion veil, certified acuity,
   field coverage, and CPU `[X]` are not executable in §1. This scorecard marks its
   numeric completions as additions rather than attributing them to the proposal.
7. **The proposal’s competitive axis table is historical, not this scorecard.** Its
   “ahead” labels for noise, clipping, invented structure, and speed were obtained
   under different instruments and, in the old head-to-head, asymmetric development.
   None is a v1.10 current-position value.
8. **D2’s CRLB channel cannot certify itself.** The same noise model cannot generate
   admission and then validate its own certificate. M9 requires independent repeated
   exposures and external fixed-pattern treatment.
9. **Phase-0 outcomes narrow the implementation path; they do not populate an
   axis.** The earlier C1/PHASE result still flips inside the measured convention
   interval and is not robust (`docs/STATUS.md` lines 203–223). The later closed-gate
   census, including strict scope and power rulings, is registered in §3.2. Those
   results invalidate proposal branches that remain written as open leverage, but
   none changes an M1–M12 bar or supplies a §6 score.

### 7.1 Disposition of the independent opposed-pair stress test

- **Accepted with scope correction:** noise and every available information,
  flat-power, and hull coordinate must be quoted from the same output bytes and
  settings, so no report may splice a quiet render to a different quality render.
  The full-axis values retain independent verdicts. An M4 or M8 failure must be
  published beside M2 but does not convert M2 to `FAIL` or `UNMEASURED`; likewise an
  M2 pass does not excuse either failure or license a detail or full-SOTA claim. The
  retained M4 per-capture/pooled `Q_flat<=1.00` plus per-site/channel transfer veto
  still protects the owner's overall M1/M2/M8 gate, and M8 keeps its own owner-gate
  verdict.
- **Accepted:** confidence precision and coverage are an opposed pair; and the
  common-merge fixed-width 1/2/4/8/16-worker outputs must have identical complete-file
  and canonical decoded-pixel SHA-256 values, with the 16-worker output also meeting
  runtime.
- **Accepted with correction:** “averaging fails MTF” becomes “averaging must fail a
  future commissioned sharpening-safe information constraint.” Standalone MTF remains
  inadmissible, and v1.10 has no such instrument.
- **Accepted with correction:** a future detail instrument, M8, and the retained M4
  flat-power-plus-transfer component should bracket sharpening together on the same
  output. Full M4 remains a mandatory disclosure. Hull is corroborative, not
  guaranteed: a mild or explicitly clamped sharpening pass can remain inside the
  hull, so hull alone is not the opposite of sharpening.
- **Rejected:** making every metric a Pareto pair. Colour and physical depth have
  external truths, while the source hull is an invariant; forced opposites would be
  weaker than their independent controls.
- **Rejected:** assuming a fixed detail/noise tradeoff slope. A genuinely better
  algorithm may improve both. The scorecard requires simultaneous owner-gate bars
  and the retained anti-cheat components, and reports every disclosure-axis value and
  Pareto point, but does not encode the phase-1 lane's internal acceptance numbers.

## 8. Publication rule

A result report must reproduce this scorecard verbatim by hash, publish every invalid
and refused arm, include commands and complete manifests, and state the verdict as:

- `PASS — SOTA under scorecard v1.10`, only when all seven owner gates pass on the
  common-merge track, including the retained M4 flat-power-plus-transfer component
  within M1/M2/M8 and the retained common-merge M12 cross-worker byte-identity
  component within M11, all five mandatory disclosure axes are measured on their
  registered tracks, and all five meet their complete registered bars. This is the
  only clean pass. It is unavailable now because M1 has no admitted instrument or
  bar, M9 is definition-blocked on M1 truth, and M10's remaining bar is
  ill-defined; later pre-results revisions are required.
- `DISCLOSURE MISS — owner's seven-axis SOTA claim supported`, when all seven owner
  gates pass on the common-merge track, including their retained anti-cheat
  components, and all five mandatory disclosure axes are measured on their registered
  tracks, but at least one full disclosure-axis bar misses. This state is **neither
  `PASS` nor `FAIL`**. The verdict headline and every public summary must name each
  missed axis, its value, and its bar without euphemism, omission, or a standalone
  “SOTA” shorthand.
- `FAIL — owner's seven-axis SOTA claim not supported`, when any commissioned owner
  gate misses on the common-merge track, including either retained anti-cheat
  component within its named gate. A full-axis M4, M5, M6, M7, or M12 miss alone
  never triggers `FAIL`.
- `DEFINITION BLOCKED`, when no owner gate has failed but any required axis lacks an
  operative predicate capable of selecting a population and verdict. A downstream
  contract does not clear this state when its required truth input is undefined.
- `UNMEASURED`, when every required axis is defined and no owner gate, including its
  retained anti-cheat component, has failed, but any required measurement, capture,
  instrument, or required comparator arm is absent or invalid. All twelve axes are
  required measurements. Helicon, when obtainable, is reported under the same
  protocol, but its absence or invalidity never triggers `UNMEASURED`.

Product-native results are labelled `PRODUCT_NATIVE_END_TO_END` and published with
their applicable unchanged bars, but they never supply, rescue, veto, or alter an
owner gate. The registered product-native M12 disclosure enters only the all-axes
measurement requirement and the `PASS` / `DISCLOSURE MISS` distinction stated above;
every other product-native result may support only an explicitly scoped end-to-end
product statement. No value, setting, or verdict may be spliced across tracks.

Until such a report exists, the only defensible public sentence is:

> **strehl’s competitive position against the required comparators — licensed Zerene
> Stacker PMax, licensed Zerene Stacker DMap, and a fresh commit-pinned rebuild of
> the fork's best-known retained source revision whose executable hash was frozen
> before rendering — is unknown. The fork arm is `UNMEASURED` under blocker `(d)`
> until that rebuild consumes the exact common-input TIFFs; the historical archived
> fork output cannot fill it. Helicon Focus, when obtainable, is an additional
> optional comparator and its result is reported separately.**
