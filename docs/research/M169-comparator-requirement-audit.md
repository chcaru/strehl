# M169 — Comparator-requirement constitution audit

**SCORECARD EXCEEDS PLAN: it made PMax, DMap, and the fork an axis-blind all-or-nothing gate.**

**Verdict.** The comparator *portfolio* is plan-authored; the universal conjunction
is not. The plan names licensed Zerene PMax and DMap, a fresh best-known fork, and
optional Helicon, but assigns comparison by claim. The scorecard turns the first
three into one atomic prerequisite and propagates failure to dependent axes without
an owner-ratified axis-to-arm map. That is a scorecard-level tightening, not a
faithful transcription.

**Operational consequence.** No free comparator is admitted today. Enfuse is the
only free candidate found with a documented route to direct TIFF input, 16-bit
output, and identity-space fusion; it still needs an actual §1.3 transfer witness,
geometry/profile evidence, and an owner amendment before it can replace a named arm.
A licence is not technically unique as a way to emit linear pixels. It is currently
required to instantiate the *named shipping Zerene methods*, especially DMap as the
plan's A5/depth comparator.

**Evidence discipline.**

- **VERIFIED BY RUNNING:** `experiments/M169-comparator-audit/verify.py` hashes the
  governing plan, scorecard, M157 survey, M161 ratification, M164 ruling, and prior
  M169 M3 commissioning report; checks the quoted anchors; re-parses the §3.1 axis
  ledger; validates the structured candidate matrix; and rejects six planted textual
  defects. It opens no image.
- **INFERRED BY READING:** all governance, technical-contract, candidate, and claim
  conclusions below. No stacker was installed or executed and no candidate,
  comparator, capture, or holdout pixel was opened.
- **Boundary:** this is a specification audit, not admission. It produces **NO
  SCORE**, authorizes no comparator substitution, and does not alter M164's
  identifiability ruling or duplicate M175's fork rebuild.

Line references below are to plan SHA-256
`72f8257918e929acb3f50c4606a4a7a73a44594492f040b4fcf196072e6a0b94` and
scorecard SHA-256
`cf91ec9afcaa4487a7ad1718a6c1ff9b6d2843b5869861606aaad46ec99331f1`.

## 1. What the plan requires

### 1.1 The controlling words

**INFERRED BY READING — whole-program definition.** The authoritative plan says:

> SOTA = a pre-registered scorecard, versus named comparators, on axes with
> commissioned instruments.

(`docs/proposals/2026-08-sota-path.md:164-167`)

The plan then pins this portfolio:

> Comparators pinned and priced: licensed Zerene (PMax *and* DMap — DMap has
> never rendered here and is A5's true comparator), the fork rebuilt at its
> best-known build (2.4× is the honest speed quote against it), Helicon if
> obtainable.

(`docs/proposals/2026-08-sota-path.md:1535-1539`)

Its owner-facing end-state is claim-specific:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census, stamped
> per file), no occlusion veil above [bar] (halo instrument at full reach), while
> emitting per-pixel certified acuity, n_eff, and depth in physical units that no
> comparator emits at all (D2/D8/A5/C5), in [X] s per frame on CPU (existing harness).

(`docs/proposals/2026-08-sota-path.md:190-197`)

This is not a requirement that every named executable qualify every clause:

- PMax and DMap are named on the detail clause.
- DMap is separately named as A5/depth's true method comparator.
- The fork is named beside the honest speed quote.
- Helicon is conditional: “if obtainable.”
- M3's literal clause is absolute: “no occlusion veil above [bar].”

The plan's later purchase instruction is also explicit:

> An open-source stacker is a useful foreign arm and repairs a real provenance
> defect, but it clears **no** blocker.

(`docs/proposals/2026-08-sota-path.md:2302-2309`)

That sentence is a governance fact under the current plan, not proof that free
software is technically incapable.

### 1.2 What the downstream scorecard added

**INFERRED BY READING — named set.** Scorecard rule 3 says:

> The required set is exactly licensed Zerene Stacker PMax, licensed Zerene
> Stacker DMap, and a fresh fork rebuild from the best-known source revision
> available on the freeze date.

(`docs/proposals/2026-09-sota-scorecard.md:209-214`)

The names, the need for licence/build provenance, and the optional treatment of
Helicon are faithful to the plan. The conjunction is not. Section 1.4 makes each
member fatal to every “dependent comparative” axis:

> If any required arm — Zerene PMax, Zerene DMap, or the fresh
> commit-pinned best-known-source fork rebuild — cannot produce a linear output
> that passes §1.3, the named-comparator requirement is unmet and the dependent
> comparative axes remain `UNMEASURED`.

(`docs/proposals/2026-09-sota-scorecard.md:488-494`)

No plan sentence says that failure to obtain DMap invalidates an occlusion-veil
maximum, or that failure to rebuild a speed baseline invalidates colour. The plan
does not supply the scorecard's axis-to-arm map at all. The safe derivation is
claim-specific requirement, not atomic-portfolio propagation.

**INFERRED BY READING — separate scorecard invention.** Rule 4 requires every
scored mode to retain at least 98% of the best M1-qualified comparator's information
score. The scorecard now labels this:

> **SCORECARD ADDITION — UNRATIFIED. This rule is authored here and is not
> traceable to the owner's plan.**

(`docs/proposals/2026-09-sota-scorecard.md:216-228`)

The plan independently records that rule 4 is the scorecard author's invention and
that its 98% threshold appears nowhere in the plan
(`docs/proposals/2026-08-sota-path.md:2399-2413`). Therefore removing only blocker
`(d)` would not make M3 runnable under the current scorecard: the separately
unratified global M1 gate, blocker `(a)`, would still stop it.

**Answer to question 1.** The three *names* are derived from the plan. Requiring all
three for every comparative axis, importing a comparator envelope into the absolute
M3 clause, and coupling M3 to M1/98% are scorecard additions. They need owner
ratification or removal; they must not be represented as existing owner mandates.

## 2. The load-bearing comparator contract

**INFERRED BY READING.** Product identity and measurement validity are different.
A technically valid foreign arm must satisfy the following minimum, regardless of
brand:

| Property | Why it is load-bearing | Governing source |
|---|---|---|
| Exact common input | Candidate and comparator must receive the same hashed 16-bit linear ProPhoto RGB D50 TIFF bytes. Otherwise the comparison includes development differences. | scorecard §1.2, `:372-401` |
| Native 16-bit linear output | A gamma/tone-converted or 8-bit output changes the measured signal and cannot pass as the common linear output. | scorecard §1.3, `:429-446` |
| Actual §1.3 witness | Eight identical 33-step ramps must produce per-channel slope `[0.995,1.005]`, `|intercept|<=0.001`, max residual `<=0.002`, RMS residual `<=0.0005`, strict monotonicity, and no interior clipping. A documentation claim is not enough. | scorecard §1.3, `:436-446` |
| Zero development instructions | Every file and sidecar must be free of non-zero contrast, sharpness, clarity, texture, luminance smoothing, tone-curve, or equivalent instructions. | scorecard §1.3, `:447-452` |
| No output-side beautification | Histogram matching, auto exposure/WB, tone mapping, sharpening, denoising, resizing, or retouching would let a comparator be changed after stacking. | scorecard §1.3/§1.4, `:429-435`, `:478-494` |
| Matched geometry | Native scale, at least 99% common overlap, registered scale/rotation/residual bounds, and input-only landmarks prevent an algorithm from gaining by crop or alignment. Frequency metrics may not resample an output. | scorecard §1.5, `:508-517` |
| Matched site survival | At least 80% of pre-registered sites and the metric-specific minimum must survive identically in every arm; differential attrition over two percentage points invalidates comparison. | scorecard §1.5, `:518-520` |
| Frozen reproducibility | Version, binary hash, licence where applicable, settings, output hashes, and identity must be frozen before outputs are viewed; settings cannot vary by subject. | scorecard §1.2/§1.4, `:407-414`, `:457-494` |

For M7, byte-identical frozen ICC and 300-DPI tags are separately mandatory
(`docs/proposals/2026-09-sota-scorecard.md:1447-1454`). For every axis, the ramp
witness is the load-bearing proof of linear transfer; merely writing a TIFF tagged
“16 bit” does not establish it.

What is **not** a generic measurement property:

- “PMax,” “DMap,” “fresh fork,” and “licensed” are identities chosen for the
  owner-facing claim.
- DMap is method-specific to the planned A5/depth comparison.
- The 98%-of-best-M1 qualifier is an acknowledged unratified scorecard policy, not
  part of linear-output conformance.

Thus a free implementation can satisfy the technical contract. It cannot silently
replace the plan's named commercial claim.

## 3. Free-stackers audit

**INFERRED BY READING.** “Qualifies” below means both technical capability and
completed evidence. On that standard, **none presently qualifies**. This lane used
public interface documentation, safe-to-read upstream files where permitted, and
the committed M157 evidence ledger. Repository licence discipline forbids a new
source inspection of Enfuse/Hugin, ImageJ EDF, CombineZP, or ChimpStackr; their
claims below do not depend on a fresh read of prohibited source.

| Candidate | Common-input acceptance | Linear-output result | Verdict and evidence |
|---|---|---|---|
| **Enfuse / Hugin** | **Yes**, by invoking Enfuse directly on the already aligned TIFF sequence; Hugin alignment need not run. | A documented path exists: 16-bit TIFF plus identity-space fusion. Defaults are unsuitable and no §1.3 witness exists. | **TECHNICALLY PLAUSIBLE; NOT ADMITTED.** The official [Enfuse manual](https://hugin.sourceforge.io/docs/manual/Enfuse.html) describes focus stacks; the [current Debian manual](https://manpages.debian.org/testing/enfuse/enfuse.1.en.html) documents 16-bit depth and identity blend space. M157 `:371-399` records that exposure/saturation defaults and ICC-selected perceptual blending must be overridden. |
| **PetteriAimonen/focus-stack** | **Yes** with `--no-align`. | **No as-is.** The pinned loader does not request `IMREAD_ANYDEPTH`, and the inverse-wavelet output is converted to `CV_8U`. | **DISQUALIFIED AS-IS.** Pinned upstream `0cd289e224fe24aead5b146faeaa46950775f346`: [`task_loadimg.cc`](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_loadimg.cc), [`task_wavelet.cc`](https://github.com/PetteriAimonen/focus-stack/blob/0cd289e224fe24aead5b146faeaa46950775f346/src/task_wavelet.cc). This is the upstream candidate, not M175's rebuild. |
| **ImageJ/Fiji Extended Depth of Field** | **Yes** as a stack; the plugin is macro-callable and alignment is external. | **Not established.** Official documentation does not define a native-size 16-bit linear RGB TIFF/profile path. | **NOT QUALIFIED.** [Plugin documentation](https://bigwww.epfl.ch/demo/edf/) and [Fiji headless guidance](https://imagej.net/learn/headless) establish automation, not the output contract. M157 `:439-465` records the earlier implementation audit. |
| **ShineStacker** | **Yes**; stacking and alignment are separate documented actions. | **Unproved.** Documentation claims 16-bit TIFF I/O but no identity-linear/profile contract and notes metadata limits on 16-bit TIFF. | **TECHNICALLY PLAUSIBLE; NOT ADMITTED.** Pinned upstream `85ae8793f380836313414bd066ea64b749159b91`, [manual](https://github.com/lucalista/shinestacker/blob/85ae8793f380836313414bd066ea64b749159b91/docs/main.md); M157 `:517-531`. |
| **OpenCV-based stackers as a class** | Implementation-dependent. OpenCV can expose unchanged-depth decoding; it does not force a stacker to use it. | Implementation-dependent. OpenCV supplies neither an output transfer contract nor profile/geometry policy. | **NOT A COMPARATOR.** A library cannot be admitted; each concrete binary must pass §1.3. See OpenCV's [`ImreadModes`](https://docs.opencv.org/4.x/d8/d6a/group__imgcodecs__flags.html) and [image-codec API](https://docs.opencv.org/4.x/d4/da8/group__imgcodecs.html). |
| **Stackaroni** | TIFF input exists; an alignment bypass is not part of the cited contract. | **No.** Its documented path linearizes input as sRGB and re-encodes sRGB on output. | **DISQUALIFIED AS DOCUMENTED.** The output is not the required linear TIFF. Pinned [`README`](https://github.com/nschroeter/stackaroni/blob/e696e8ef3bb75d87e05f8d071807c6b017b5cb10/README.md), revision `e696e8ef3bb75d87e05f8d071807c6b017b5cb10`. |
| **z-stackr** | TIFF input and a no-alignment mode exist. | **No.** The detailed pipeline says it stores and blends gamma-encoded sRGB end to end; brightness/gamma correction is enabled by default. | **DISQUALIFIED AS DOCUMENTED.** Pinned [`README`](https://github.com/suitable-name/z-stackr/blob/2cadffa5c1e98817dde46f946eea6888733435bd/README.md), revision `2cadffa5c1e98817dde46f946eea6888733435bd`. |
| **PICOLAY** | GUI/batch loading exists. | **No.** Its manual says TIFFs become 24-bit bitmaps internally and it cannot save TIFF. | **DISQUALIFIED AS DOCUMENTED.** [Official manual](https://www.picolay.de/picolay_helpfiles/Manual_PICOLAY_EN.pdf); M157 `:421-437`. |
| **CombineZP** | Stack input and macro automation exist. | **No as-is.** The committed implementation audit found only 24/32-bit RGB storage/export, not 16-bit per channel. | **DISQUALIFIED AS-IS.** M157 `:401-419`, pinned upstream `fbc64d84ebf6ea65318ccae33100d6e91c348462`. |
| **ChimpStackr** | A stack-only CLI is documented. | A 16-bit pipeline is claimed, but identity-linear transfer and profile behavior are not established. | **NOT QUALIFIED.** M157 `:533-551`, pinned upstream `14cb77898cccc4756f4785286bf69325768dc4ae`. A new source audit was not performed because repository licence policy forbids it. |

darktable and RawTherapee are scriptable linear developers, not focus-fusion
comparators. They can prepare the common input but cannot supply the missing
independent stack output. Legacy tools without a documented 16-bit linear TIFF path
fail at the same point as PICOLAY/CombineZP.

**Answer to question 3.** Enfuse is a real, freely obtainable **qualification
candidate**, not a qualified comparator. All others examined either have a documented
non-linear/8-bit path or lack enough evidence to assert §1.3 conformance. No free
name may be placed in the scorecard today.

The Petteri implementation finding is **INFERRED BY READING** the cited, safely
inspectable pinned upstream source. The local text-only verifier freezes the revision
and citation but does not fetch or reproduce third-party source, so it does not
independently re-prove those two implementation facts.

## 4. Axis consequences and admission cost

### 4.1 Re-derived dependency ledger

**VERIFIED BY RUNNING — current text.** The verifier parses only scorecard §3.1
(`:780-813`) and finds literal blocker `(d)` on exactly:

`M1, M2, M3, M4, M5, M6, M7` — **7 axes**.

**INFERRED BY READING — semantic dependency.** M11 omits the `(d)` glyph but its
readiness row says required common-input comparator outputs are absent and its metric
is relative speed against the fastest qualifying comparator. It is an eighth direct
semantic dependency:

`M1, M2, M3, M4, M5, M6, M7, M11` — **8 axes**.

M9 is not a ninth direct comparator dependency. Its current definition waits for
candidate-specific acuity truth through M1, so it is transitively stalled today;
the scorecard says:

> M1 is the currently specified and physically actionable route to that truth, not
> the unique mathematical anchor; a sufficiently powered independent same-resolution
> reference could in principle normalize relative transfer, but no such route is
> admitted today.

(`docs/proposals/2026-09-sota-scorecard.md:1608-1614`). Comparator availability is
therefore not intrinsic to M9. M12 has no direct comparator blocker.

### 4.2 What a free-arm qualification would clear

**INFERRED BY READING — under the unamended plan: zero.** The plan expressly says a
free foreign arm clears no blocker. Technical success alone cannot rewrite the named
claim.

**INFERRED BY READING — if the owner authorizes capability-based substitution.**
An admitted Enfuse output could satisfy the *technical comparator limb* for M1-M7
and M11, but:

1. it would replace only the arm(s) the owner names in an amended axis-to-arm map;
2. the fresh fork remains separately relevant to M11's speed baseline and is M175's
   work;
3. none of those axes becomes measured merely because a comparator exists; all
   other blockers remain conjunctive; and
4. M9 benefits only if that work helps admit an acuity-truth producer.

### 4.3 Concrete Enfuse admission work

**INFERRED BY READING.** Admission costs one bounded, pre-registered qualification
package, not a corpus-wide exploratory run:

- owner decision amending the plan/scorecard if Enfuse will replace rather than
  supplement a named arm;
- exact release/package/source identity, binary and dependency hashes;
- frozen direct-Enfuse settings before any scored output is viewed, with exposure
  and saturation weighting disabled, focus contrast enabled, identity blend space,
  native canvas/depth, and no alignment or post-processing;
- proof that exact common-input TIFF bytes are accepted;
- complete §1.3 per-channel 33-step ramp witness;
- zero non-zero development instructions in every file and sidecar;
- native-size, at least 99% overlap, profile semantics, input-only geometry, and
  proof that frequency metrics never resample an output;
- at least 80% plus the metric-specific minimum sites surviving identically in every
  arm, with differential attrition no greater than two percentage points;
- frozen settings/output hashes and no per-subject tuning;
- any separately authorized axis-specific information/anti-cheat guard; and
- only then, rendering of the registered common-input stacks.

No candidate pixels or scored outputs are needed to settle whether the specification
is viable; synthetic transfer/geometry witnesses settle admission first.

### 4.4 M3 after correcting the overreach

**INFERRED BY READING.** M3 is the clearest affected axis. Its plan clause is
absolute, and M161 has ratified the literal publication maximum at `0.05`
(`docs/research/M161-m3-ratification.md:1-5,81-89`, SHA-256
`3da41f80a05a9d1f91b35f03aa72ef1dece1d7252d21da8cc0ce5313d725b58e`).
If the owner removes both the comparator envelope and the separately unratified
global M1/98% coupling, M3 would still need:

- the frozen candidate common-input output set and manifests;
- the profile-package builder and source/output profile packages;
- input-only warp/geometry evidence;
- execution on the frozen eligible-site population;
- every absolute max, median, width, coherence, completeness, and commissioning
  guard evaluated as registered; and
- subject/capture denominators and the registered confidence intervals.

The v3 M169 battery is commissioned (`docs/research/M169-m3-veil.md:7-22,316-337`,
SHA-256
`d83eab7a42670eef54554e0638eb3cc27df48445cd34fb93f4f51e01d3869cb1`),
but those missing materials mean **NO SCORE**. This audit does not authorize one.

## 5. What is and is not unique about Zerene

**INFERRED BY READING.** No cited evidence establishes that Zerene alone can emit a
16-bit linear stack. Enfuse has a credible documented route; ShineStacker may have
one. Conversely, a Zerene purchase alone does not prove §1.3: its actual frozen
PMax and DMap exports must still pass the ramp and geometry witnesses.

What only the licensed product supplies **under the current plan** is claim identity:

1. results from the named current shipping comparator;
2. the distinct PMax and DMap commercial algorithms; and
3. DMap specifically as the plan's A5/depth method comparator.

That is why a free arm cannot silently stand in for Zerene. It is not because free
software is known to lack linear TIFF output. The purchase justification that
survives “why not free?” is:

> The current claim explicitly names the shipping Zerene PMax and DMap methods, and
> DMap is the planned depth-method comparator. A free implementation can add
> technical evidence but cannot produce Zerene-method results. If the owner no
> longer wants that named claim, amend the plan instead of buying a licence.

For M3's absolute plan clause, this justification does **not** make Zerene
load-bearing. For M1's “best shipping comparator” and A5/depth framing, it does.

## 6. Can reference truth replace comparison?

**INFERRED BY READING — current claim: no.** The governing definition says “versus
named comparators.” Absolute or reference-truth measurement can make a defensible
scientific statement, but it cannot silently satisfy this particular whole-product
SOTA sentence. “State of the art” still needs evidence about the state being
surpassed, unless the owner changes the claim to an absolute-performance claim.

There are two narrower cases:

1. **Absolute axis result.** M3's plan clause is already absolute. Once its
   non-comparator prerequisites exist, it can support “no occlusion veil above
   0.05” without a licence if the scorecard additions are removed.
2. **Truth-referenced detail result.** M164 ruled that GX can replace the meaning of
   M1's detail instrument, not the current claim's comparison. Its exact propagation
   finding is `0 of 7` explicit `(d)` dependencies and `0 of 8` semantic comparator
   dependencies removed (`docs/research/M164-gx-sota-claim.md`, SHA-256
   `59d56ffeae5156d9afd046e864efacc8dba45ef455487bd5317000f2bca0fde8`).

A new claim such as “achieves absolute truth-referenced detail X on registered
subjects” could avoid competitor outputs, but it is not the current SOTA claim. This
axis-scoping result should be routed to M164 because it changes which comparators a
claim must name; it does not alter M164's identifiability analysis.

**Answer to question 6.** Comparator framing is avoidable for M3's absolute axis and
for a newly authorized absolute/reference-truth claim. It is not avoidable for the
current plan's full named-comparator SOTA claim.

## 7. Routed correction text

**INFERRED BY READING — proposed owner amendment; not applied.** The following text
removes the unsupported propagation without weakening a claim that actually names an
arm:

> **Claim-specific comparator rule.** The plan's comparator portfolio is licensed
> Zerene PMax, licensed Zerene DMap, the fresh best-known-source fork, and Helicon if
> obtainable. A metric card must identify which arm or arms its claim requires and
> cite the plan clause that requires them. Failure or §1.3 nonconformance of a named
> arm makes only that claim's comparative limb `UNMEASURED`; it does not propagate
> to an absolute card or an unrelated axis. Until an axis-to-arm map is owner
> ratified, record each arm separately rather than treating PMax, DMap, and the fork
> as an atomic portfolio.

Replace the fatal sentence in scorecard §1.4 with:

> If an arm required by a particular metric card cannot produce a linear output
> that passes §1.3, that metric's comparative limb is `UNMEASURED`. Its failure does
> not block an absolute metric card or a card that does not name that arm.

For M3 specifically, if the owner rejects the two unratified additions:

> M3 is scored absolutely against its ratified candidate-output gates. Comparator
> summaries remain mandatory disclosure but are not a pass prerequisite. Remove the
> M1-qualified comparator-envelope gate, blocker `(d)`, and the global M1/98%
> prerequisite from M3.

This correction does not authorize Enfuse substitution, remove PMax/DMap from M1,
remove DMap from A5/depth, or remove the fork from the speed comparison. It requires
the scorecard owner to publish the missing claim-specific map.

## 8. Bottom line for the owner

**INFERRED BY READING.**

- Do **not** buy Zerene on the premise that it uniquely supplies linear output; that
  premise is unsupported.
- Buy it if the owner wants to retain the current named PMax/DMap shipping-comparator
  and DMap-depth claims.
- Do **not** let the absent licence block M3 merely through the scorecard's universal
  portfolio rule; the plan's M3 clause is absolute.
- Do **not** stop M175 globally: the fork remains relevant to its named speed
  baseline and possibly other owner-mapped claims. It is not plan-authorized as an
  M3 prerequisite.
- If the owner wants a free technical comparator, qualify Enfuse first and amend the
  governing comparator map before using it.
