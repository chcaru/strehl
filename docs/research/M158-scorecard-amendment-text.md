# M158 — applicable scorecard amendment text for F4, F5, F6, and F14

Source snapshot checked before drafting: commit `249f77db`.

- `docs/proposals/2026-09-sota-scorecard.md`: SHA-256
  `ff2b0348ee87dac81bd400713d477888cf1869ba68c25f6a700d4682d007d6d5`
- `docs/proposals/2026-08-sota-path.md`: SHA-256
  `218a7a0c8748ac3e5e13594ff9b11f13c23f559f19d81ff3accdca597111cc22`

Every anchor below is a literal substring wholly contained on one physical source
line. Counts are ordinal, case-sensitive substring counts in the named file.

**DIRECT ANSWER: YES — even with unratified rule 4 treated as absent, the current
independent clauses make M2, M3, M4, and M11 unscoreable today because M1 has no
admitted instrument or bar.**

## F4 — independent M1 dependencies

### 1. CURRENT TEXT

The following live clauses recreate the M1 dependency independently of rule 4.

**Joint M2/M4/M8 row**

> | M1 information + M2 noise + M4 flat power + M8 hull | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | M1 presently has no admissible statistic. When it is replaced, publish the replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output and pass every bar simultaneously. Until then neither a noise-only nor a detail claim is valid. |

Anchor: `| M1 information + M2 noise + M4 flat power + M8 hull |`  
Measured scorecard count: **1**.

**Joint M3 row**

> | M3 boundary integrity + local source coherence/width | Blur can hide a halo or veil while widening the edge and reducing agreement with the independently sharp source. | The same boundary render must pass M3's width bar and M5's local `rho_best>=0.90`; the build must also pass a future commissioned M1 on independent-repeat captures. |

Anchor: `| M3 boundary integrity + local source coherence/width |`  
Measured scorecard count: **1**.

**M1 Success**

> **Success.** There is deliberately no active numeric success bar. M1 remains
> **UNMEASURED**, and no detail, matched-information, quality-qualified comparator or
> SOTA claim is licensed until a replacement statistic and numeric bar survive
> commissioning.

Anchor: `**UNMEASURED**, and no detail, matched-information, quality-qualified comparator or`  
Measured scorecard count: **1**.

**M2 exact computation**

> 4. `eta = sigma_res / sigma_ideal`. The comparator ratio uses paired ROIs and only
>    modes within `98%` of a future replacement-M1 information envelope. No comparator
>    mode qualifies in v1.7.

Anchor: `modes within `98%` of a future replacement-M1 information envelope. No comparator`  
Measured scorecard count: **1**.

**M2 Control**

> **Control.** Input-only cross-light ROI selection prevents output cherry-picking;
> §1.3 fixes gain and tone; a future replacement M1 must remain green. A
> Gaussian-output-blur plant must improve raw noise while failing the edge-width/gain
> guard. Added independent noise of `0.25 sigma_1` must increase `eta` by at least
> `0.20`; the untouched temporal mean must fall in `0.90 <= eta <=1.10`. Until M1 is
> replaced, `eta` is diagnostic only.

Anchor: `§1.3 fixes gain and tone; a future replacement M1 must remain green. A`  
Measured scorecard count: **1**.

**M3 Control**

> **Control.** The score is excess over the source interval/reference, not absolute
> optical halo. A future replacement M1, `rho_edge`, and the width guard catch blur.
> Crops and plateaus are frozen. A 6% planted rim and 6% 200-px veil must be detected on
> at least 95% of sites; untouched raw frames must have false-positive rate `<=1%`.
> Any checker that convicts the raw null is not admitted.

Anchor: `optical halo. A future replacement M1, `rho_edge`, and the width guard catch blur.`  
Measured scorecard count: **1**.

**M4 Control**

> **Control.** A future replacement M1 must catch blur. The checker sees inputs and
> final pixels, never weights. A planted 32-px spatial selector must make at least 95%
> of planted flat tiles exceed `Q=1.25`; a fixed-weight mean must produce no more than
> 1% failures. Shifting the output by one tile must destroy edge correspondence without
> changing its spatial spectrum, demonstrating that the edge arm is not merely a
> texture detector.

Anchor: `**Control.** A future replacement M1 must catch blur. The checker sees inputs and`  
Measured scorecard count: **1**.

**Comparator envelope**

> For higher-is-better metrics, the comparator envelope is the maximum qualifying value
> over all registered modes. For lower-is-better metrics it is the minimum. For speed it
> is the fastest mode that passes the complete quality scorecard. This is intentionally
> conservative toward strehl.

Anchor: `is the fastest mode that passes the complete quality scorecard. This is intentionally`  
Measured scorecard count: **1**.

**M11 computation**

> 7. Comparator speed uses the fastest mode that passes all quality gates at identical
>    dimensions, bit depth, ICC, and common input.

Anchor: `7. Comparator speed uses the fastest mode that passes all quality gates at identical`  
Measured scorecard count: **1**.

**M11 summary and Control**

> | M11 | Wall-clock throughput | Warm common-input throughput `>=2.00x` fastest quality-qualified comparator; candidate/default baseline ratio `<=2.00`; native-RAW CPU at 16 workers `<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; 100-frame live master `<=10 s` after last shutter. |

Anchor: `| M11 | Wall-clock throughput | Warm common-input throughput`  
Measured scorecard count: **1**.

> **Control.** The warm uncompressed common-input arm controls storage and RAW decode;
> the native arm prices strehl's actual decode bottleneck rather than hiding it.
> Alternating sweeps and per-setting minima follow `AGENTS.md` rule 16. Input/output
> hashes and quality qualification prevent omitted work. A planted 1-second sleep must
> add `1.00+/-0.05 s`; a child that writes after parent exit must remain inside the
> timer. A cold arm must begin after a documented reboot or equivalent machine-wide
> cache reset on a dedicated benchmark host.

Anchor: `Alternating sweeps and per-setting minima follow `AGENTS.md` rule 16. Input/output`  
Measured scorecard count: **1**.

**Readiness classifications**

> | M2 | **(a)(b)(d)** | Residual noise can be computed diagnostically, but the registered matched-information verdict cannot. |
> | M3 | **(a)(b)(d)** | Artifact counts without a licensed detail/matched-presentation arm cannot support the competitive claim. |
> | M4 | **(a)(b)(d)** | Flatness is computable diagnostically, but its detail-preserving comparator verdict is blocked. |

and:

> | M11 | **(a)(b)(d)** | A quiet host is additionally required; native-decode timing alone is a diagnostic, not the registered competitive verdict. |

Anchors and measured scorecard counts:

- `| M2 | **(a)(b)(d)** |` — **1**
- `| M3 | **(a)(b)(d)** |` — **1**
- `| M4 | **(a)(b)(d)** |` — **1**
- `| M11 | **(a)(b)(d)** |` — **1**

**Derived scoreboard statement**

> **Resulting scoreboard:** **0 of 12 axes MEASURED; 12 of 12 UNMEASURED.** M1 carries
> the greatest logical weight because it has neither an instrument nor a bar and is a
> qualification dependency for multiple quality and comparator axes. M8 remains the
> only complete quality axis immediately measurable, but a pass there cannot rescue
> an absent M1.

Anchor: `the greatest logical weight because it has neither an instrument nor a bar and is a`  
Measured scorecard count: **1**.

**Opposed-pair disposition**

> - **Accepted with correction:** “averaging fails MTF” becomes “averaging must fail a
>   future commissioned sharpening-safe information constraint.” Standalone MTF remains
>   inadmissible, and v1.7 has no such instrument.
> - **Accepted with correction:** a future detail instrument, M4, and M8 should bracket
>   sharpening together. Hull is corroborative, not guaranteed: a mild or explicitly
>   clamped sharpening pass can remain inside the hull, so hull alone is not the
>   opposite of sharpening.

Anchors and measured scorecard counts:

- `- **Accepted with correction:** “averaging fails MTF” becomes “averaging must fail a` — **1**
- `- **Accepted with correction:** a future detail instrument, M4, and M8 should bracket` — **1**

### 2. REPLACEMENT TEXT

Replace the joint rows with the following. The first row is shared with F14 and
should be applied once:

> | M2 noise + M4 flat power + M8 hull; M1 detail when available | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | Publish every available value `(detail, eta, Q_flat, M8-R, M8-O)` from the same output bytes and settings. Each axis retains its own bar and verdict; the tuple has no aggregate pass state. M1's absence blocks M1 and the full SOTA sentence, not M2, M4, or M8. An M2 result licenses only its stated noise claim. |
> | M3 boundary integrity + local source coherence/width | Blur can hide a halo or veil while widening the edge and reducing agreement with the independently sharp source. | The same boundary render must pass M3's own excess, width, and `rho_edge` bars. A future M1 value, when available, is reported separately and does not determine M3's verdict. |

Replace M1 Success with:

> **Success.** There is deliberately no active numeric success bar. M1 remains
> **UNMEASURED**, and no detail or full SOTA claim is licensed until a replacement
> statistic and numeric bar survive commissioning. M1's absence does not block an
> M2, M3, M4, or M11 verdict; each is decided by its own registered instrument,
> controls, and evidence.

Replace M2 exact-computation step 4 with:

> 4. `eta = sigma_res / sigma_ideal`. The comparator ratio uses paired ROIs from every
>    registered mode that passes §1.3. No M1 result or retained-information percentage
>    qualifies an M2 comparator arm. Report any available detail, `Q_flat`, M8-R, and
>    M8-O values from the same output beside M2, but decide each axis independently.

Replace M2 Control with:

> **Control.** Input-only cross-light ROI selection prevents output cherry-picking;
> §1.3 fixes gain and tone. A Gaussian-output-blur plant must improve raw noise while
> failing the edge-width/gain guard, so the report exposes the known route by which
> blur can buy a lower noise value. Added independent noise of `0.25 sigma_1` must
> increase `eta` by at least `0.20`; the untouched temporal mean must fall in
> `0.90 <= eta <=1.10`. M2 receives its own `PASS`, `FAIL`, or `UNMEASURED` verdict
> without M1; it licenses a noise claim only, never a detail claim.

Replace M3 Control with:

> **Control.** The score is excess over the source interval/reference, not absolute
> optical halo. `rho_edge` and the width guard catch blur within M3 itself; neither
> imports M1's verdict. Crops and plateaus are frozen. A 6% planted rim and 6% 200-px
> veil must be detected on at least 95% of sites; untouched raw frames must have
> false-positive rate `<=1%`. Any checker that convicts the raw null is not admitted.

Replace M4 Control with:

> **Control.** The checker sees inputs and final pixels, never weights. A planted
> 32-px spatial selector must make at least 95% of planted flat tiles exceed
> `Q=1.25`; a fixed-weight mean must produce no more than 1% failures. Shifting the
> output by one tile must destroy edge correspondence without changing its spatial
> spectrum, demonstrating that the edge arm is not merely a texture detector. M4
> certifies only the named patchwork/ghost defects; it does not certify preserved
> detail and does not depend on M1.

Replace the comparator-envelope paragraph with:

> For higher-is-better metrics, the comparator envelope is the maximum qualifying
> value over all registered modes. For lower-is-better metrics it is the minimum. For
> speed it is the fastest registered mode that passes §1.3 and emits the required
> dimensions, bit depth, ICC, and crop. Quality-axis results are reported beside
> speed, but neither M1 nor an unrelated quality verdict qualifies the M11 arm. This
> is intentionally conservative toward strehl without importing an unavailable
> detail instrument.

Replace M11 exact-computation step 7 with:

> 7. Comparator speed uses the fastest registered mode that passes §1.3 at identical
>    dimensions, bit depth, ICC, crop, and input contract. Report its quality-axis
>    results beside the timing result, but do not condition M11 on M1 or any unrelated
>    quality verdict.

Replace the M11 at-a-glance row with:

> | M11 | Wall-clock throughput | Warm common-input throughput `>=2.00x` fastest registered comparator mode passing §1.3; candidate/default baseline ratio `<=2.00`; native-RAW CPU at 16 workers `<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; 100-frame live master `<=10 s` after last shutter. |

Replace M11 Control with:

> **Control.** The warm uncompressed common-input arm controls storage and RAW decode;
> the native arm prices strehl's actual decode bottleneck rather than hiding it.
> Alternating sweeps and per-setting minima follow `AGENTS.md` rule 16. Input/output
> hashes, frozen commands, mandatory-stage banners, and dimensions/bit-depth/ICC/crop
> checks prevent omitted work. Quality-axis results are published beside timing but do
> not qualify M11. A planted 1-second sleep must add `1.00+/-0.05 s`; a child that
> writes after parent exit must remain inside the timer. A cold arm must begin after a
> documented reboot or equivalent machine-wide cache reset on a dedicated benchmark
> host.

Replace the four readiness rows with:

> | M2 | **UNMEASURED; no `(a)` dependency** | M1 is not a prerequisite. The scorecard M2 verdict still lacks an eligible second-light repeat, a complete aggregation/RGB rule, and the required comparator output. |
> | M3 | **UNMEASURED; no `(a)` dependency** | M1 is not a prerequisite. Full-reach eligibility and an executable commissioned checker remain unresolved; the required comparator output is absent. |
> | M4 | **UNMEASURED; no `(a)` dependency** | M1 is not a prerequisite. The scored population, `noise_floor`, site manifest, commissioned checker, and required comparator output remain unresolved. |
> | M11 | **UNMEASURED; no `(a)` dependency** | M1 is not a prerequisite. The complete timing contract, required comparator output, and quiet-host run remain absent. |

Replace the derived scoreboard statement with:

> **Resulting scoreboard:** M1 has the greatest publication consequence because the
> owner's full SOTA sentence includes detail and M1 has neither an admitted instrument
> nor a bar. It is not a qualification dependency for M2, M3, M4, or M11. Those axes
> retain their own `UNMEASURED` states only for the axis-local reasons recorded above.
> M8 remains `FAIL`; no other axis is converted to `PASS` by this amendment.

Replace the two opposed-pair bullets with:

> - **Accepted with correction:** when an admissible detail coordinate exists, publish
>   it beside noise from the same output. Until then, the Gaussian-blur plant and M2's
>   local edge-width/gain diagnostic expose the trade without importing M1 as a gate.
>   M2 remains a noise-only verdict.
> - **Accepted with correction:** detail, M4, and M8 should be reported together when
>   available, but each keeps its own verdict. Hull is corroborative, not guaranteed:
>   a mild or explicitly clamped sharpening pass can remain inside the hull, so hull
>   alone is not the opposite of sharpening.

### 3. PLAN LICENCE

> Scorecard decision rule 4 — which I wrote — propagates blocker `(a)` to four
> axes that do not require it intrinsically. Mechanically re-derived
> (`experiments/M140-readiness/readiness.json`): `b+d` yields **2** measurable
> axes with the rule and **6** without; `b+c+d` yields **4** versus **8**.
> Intrinsic to `M1, M5, M6, M9`; propagated to `M2, M3, M4, M11`.

Plan anchor: `axes that do not require it intrinsically. Mechanically re-derived`  
Measured plan count: **1**.

The licence is direct: the plan names exactly these four axes and says they do not
require M1 intrinsically. This finding therefore survives with rule 4 treated as
absent; the quoted joint/card/comparator clauses independently recreate what the
plan says is merely rule-4 propagation.

### 4. BAR TEST

**LOUD FLAG — THIS MAKES FOUR AXES SCOREABLE WITH RESPECT TO M1.** It removes no
M2, M3, M4, or M11 numeric success bar and retracts no `FAIL`. It does remove the
cross-axis eligibility condition that presently makes all four `UNMEASURED` whenever
M1 is uninstrumented. M135's `NO-GO for D8 as M1` and its common-post-noise
invariance proof make that the present state, not a hypothetical one. None becomes
`PASS` by this text: M2 still has capture,
aggregation, and comparator defects; M3 and M4 lack complete commissioned
instruments; M11 lacks the complete comparator/quiet-host run. Rule 4 is assumed
absent as instructed; if left operative, it independently reinstates the same M1
dependency and defeats this correction.

## F5 — native-RAW competitive path

### 1. CURRENT TEXT

The scope sentence currently requires one input protocol:

> **Therefore, for strehl, SOTA means that
> the shipping default satisfies every clause of that sentence against the licensed
> comparator set under one common linear-input protocol, while also emitting
> independently calibrated trust and depth products.** It is not an average, a weighted
> score, or “wins most axes.”

Anchor: `comparator set under one common linear-input protocol, while also emitting`  
Measured scorecard count: **1**.

The operative input section is:

> ### 1.2 One common linear input
>
> Competitive quality is measured only at a common merge boundary:
>
> 1. Decode each ARW once with one independently versioned LibRaw-based converter whose
>    executable hash is frozen before rendering.
> 2. Apply sensor black/white levels and one frozen deterministic-pattern map estimated
>    from independent matching dark/flat captures; if no matching map exists, M1/M9 are
>    `UNMEASURED`. Apply the recorded camera white balance and one camera matrix once.
>    Demosaic once. Write **uncompressed** 16-bit **linear ProPhoto RGB, D50** TIFFs at
>    the native active-image dimensions.
> 3. Ignore every XMP sidecar. Disable auto-brightening, exposure compensation, tone
>    curves, contrast, clarity, texture, sharpening, denoising, chromatic-aberration
>    correction, lens correction, local contrast, gamut compression, and output resize.
> 4. Strip development tags from the derivative and embed only the frozen linear ICC,
>    provenance, and source hash. Hash the pixel payload and whole TIFF.
> 5. Zerene, Helicon, and strehl must receive the exact same TIFF bytes. A strehl TIFF
>    adapter or a bit-for-bit hash identity at strehl’s internal pre-merge linear-frame
>    boundary is a prerequisite. Until one exists, **competitive quality remains
>    UNMEASURED**; feeding TIFFs only to the commercial tools is forbidden.
>
> This deliberately separates the fair merge comparison from a native-RAW product run.
> A native-RAW run is reported as a product diagnostic but cannot establish a
> competitive detail, noise, clipping, or colour win unless its pre-merge samples pass
> the same identity audit.

Anchor: `### 1.2 One common linear input`  
Measured scorecard count: **1**.

The following §1.3 rationale assumes that exclusive protocol:

> Because all programs consume one hashed
> linear TIFF and all metrics run before a common external display transfer, the
> `Contrast2012=+100` asymmetry that killed the previous comparison cannot occur in one
> arm. It would change the shared input hash or fail the ramp.

Anchor: `Because all programs consume one hashed`  
Measured scorecard count: **1**.

The proposal-correction section repeats the exclusivity:

> 3. **The comparator prerequisite is larger than a licence/export.** The proposal says
>    the scorecard needs a Zerene licence, chart/export, and sharp subject
>    (`2026-08-sota-path.md` lines 183–187). It also needs a common linear merge boundary
>    in strehl. Without that, repeating the old RAW-versus-developed-TIFF asymmetry is
>    unavoidable.

Anchor: `3. **The comparator prerequisite is larger than a licence/export.** The proposal says`  
Measured scorecard count: **1**.

### 2. REPLACEMENT TEXT

Replace the scope sentence with:

> **Therefore, for strehl, SOTA means that the shipping default satisfies every clause
> of that sentence against the licensed comparator set under the applicable frozen
> input contract, while also emitting independently calibrated trust and depth
> products. Competitive reports must distinguish common-merge results from
> product-native results and may not splice them into one fictional arm.** It is not
> an average, a weighted score, or “wins most axes.”

Replace §1.2 in full with:

> ### 1.2 Two frozen input contracts
>
> Competitive quality has two separately reported tracks. They answer different
> questions, and neither may borrow a value, setting, or verdict from the other.
>
> **Common-merge track.** Decode each ARW once with one independently versioned
> LibRaw-based converter whose executable hash is frozen before rendering. Apply sensor
> black/white levels and one frozen deterministic-pattern map estimated from independent
> matching dark/flat captures; if no matching map exists, M1/M9 are `UNMEASURED`.
> Apply the recorded camera white balance and one camera matrix once. Demosaic once.
> Write uncompressed 16-bit linear ProPhoto RGB, D50 TIFFs at the native active-image
> dimensions. Ignore every XMP sidecar and disable auto-brightening, exposure
> compensation, tone curves, contrast, clarity, texture, sharpening, denoising,
> chromatic-aberration correction, lens correction, local contrast, gamut compression,
> and output resize. Strip development tags, embed only the frozen linear ICC,
> provenance, and source hash, and hash both pixel payload and whole TIFF. Every program
> in this track receives the exact same TIFF bytes. A strehl TIFF adapter or bit-for-bit
> identity at strehl's internal pre-merge linear-frame boundary is required for this
> track.
>
> **Product-native track.** Freeze one source-ARW manifest before any output is viewed.
> Strehl receives those original ARWs through its shipping native path. Each registered
> comparator receives the earliest linear input its shipping stack path supports,
> derived once from the same ARWs under the frozen settings above. No arm receives
> per-subject development, retouching, post-sharpening, denoising, tone adjustment, or
> output resizing. Freeze and publish every source hash, derivative hash, converter
> hash, program version, setting, output-transfer result, and output hash.
>
> The common-merge track isolates behaviour after a shared demosaic. The product-native
> track measures the shipping products end to end and is the claim-bearing track for a
> mechanism, such as C1, whose defining operation consumes photosites and subsumes
> demosaic. A product-native competitive result must be labelled
> `PRODUCT_NATIVE_END_TO_END`; it may establish an output-quality win but may not
> attribute that win to merge alone. Input representations are deliberately different
> in that track and must never be described as byte-identical.
>
> Every metric must name its track. A result is `UNMEASURED` if its required track lacks
> a frozen input lineage, a qualifying comparator output, or the metric's own evidence.
> A common-merge result cannot veto or substitute for a product-native result, and a
> product-native result cannot be used to claim a controlled post-demosaic merge win.

Replace the §1.3 rationale with:

> In the common-merge track, all programs consume one hashed linear TIFF, so a
> one-arm `Contrast2012=+100` instruction changes the shared input hash or fails the
> ramp. In the product-native track, the source ARWs, comparator derivative, converter,
> and every development setting are frozen and published separately; §1.3 still
> forbids output-side tone or sharpening asymmetry. That track is explicitly
> end-to-end and does not claim pre-merge sample identity.

Replace proposal-correction item 3 with:

> 3. **The comparator prerequisite has two input contracts.** The common-merge track
>    requires a licensed export and a byte-identical linear-TIFF boundary. The
>    product-native track starts every arm from one frozen source-ARW lineage while
>    allowing each shipping product to consume the earliest linear representation it
>    supports. The first isolates post-demosaic merge behaviour; the second is required
>    to score C1's photosite-consuming path and is labelled end to end. Neither track
>    may be reported as the other.

### 3. PLAN LICENCE

> ### C1. Sample-level fusion — the merge consumes photosites
>
> **The claim (ARGUED):** the single largest un-refuted quality lever in this project is
> to stop feeding the merge *resampled estimates* and start feeding it *the sensor's
> actual samples*, each carrying its exact warped position, channel and σ — one estimator
> that subsumes demosaic, warp resampling, merge, and (at a finer output lattice)
> super-resolution.

Plan anchor: `### C1. Sample-level fusion — the merge consumes photosites`  
Measured plan count: **1**.

The plan also supplies claim-bearing acceptance:

> **Acceptance / kill bars (pre-registered against D1's instruments):** FRC gain over the
> current default on the §33 subject and the §30 chart; demosaic-artifact disappearance
> on a zone-plate/fine-check target (false-colour moiré must *decrease* — a signature
> interpolation cannot fake); the M115 split-half SNR instrument re-run on the
> sample-fusion arm (R_SNR must exceed 1 where phase coverage is reported high, and must
> not fall below 1 anywhere); hull discipline per contributing sample set; noise at
> matched band ≤ current default;

Plan anchor: `**Acceptance / kill bars (pre-registered against D1's instruments):** FRC gain over the`  
Measured plan count: **1**.

And the implementation order is explicit:

> C1 lands in two rungs: **1× lattice first** (demosaic-free merge — strictly a
> correctness/efficiency win that also closes §2.4, no SR claim), then **2×** behind the
> D1 instruments with C12's alias census gating engagement per tile.

Plan anchor: `C1 lands in two rungs: **1× lattice first** (demosaic-free merge — strictly a`  
Measured plan count: **1**.

An exclusive already-demosaiced input cannot exercise the mechanism the plan directs
the program to build and score. The two-track replacement preserves the controlled
TIFF experiment while restoring a claim-bearing route for the native product.

### 4. BAR TEST

No numerical quality bar is lowered and no `FAIL` is retracted. **LOUD FLAG — this
does make native-RAW competitive quality eligible for future scoring where the
current text forbids it.** It creates no present `PASS`: M1 remains uninstrumented,
and every native-track result must still meet the metric's unchanged bar, output
transfer, geometry, holdout, commissioning, comparator, and provenance requirements.
The trade is explicit rather than hidden: common-merge results support causal
post-demosaic comparisons; product-native results support only end-to-end product
claims.

## F6 — blanket prohibition above 0.25 cyc/native px

### 1. CURRENT TEXT

The global rule says:

> 7. No pass/fail decision or public numerical detail claim may use a frequency above
>    `0.25 cyc/native px`. A checker that reads higher must emit only the explicit
>    `UNLICENSED_GT_0.25` label.

Anchor: `7. No pass/fail decision or public numerical detail claim may use a frequency above`  
Measured scorecard count: **1**.

M1 repeats the prohibition:

> **Exact computation.** None is admitted in v1.7. A replacement must be
> pre-registered before its fresh holdout is rendered, must use no frequency above
> `0.25 cyc/native px`, and must be implemented and audited independently of the
> pipeline producing the render.

Anchor: `pre-registered before its fresh holdout is rendered, must use no frequency above`  
Measured scorecard count: **1**.

M9 makes it a permanent scoring ceiling:

> 1. For each tile and 0.05-cyc/px band whose upper edge is `<=0.25 cyc/px`, truth is
>    the future independently commissioned M1 condition. The withdrawn v1.3
>    `D>=1 && FRC>=1/7` rule is not truth in v1.7.
> 2. A claimed band is the highest licensed band strehl’s output certificate marks
>    valid. Bands above `0.25 cyc/px` must be labelled `UNLICENSED` and cannot improve
>    the score.

Anchor: `2. A claimed band is the highest licensed band strehl’s output certificate marks`  
Measured scorecard count: **1**.

### 2. REPLACEMENT TEXT

Replace decision rule 7 with:

> 7. Frequency does not license itself. A pass/fail decision or public numerical
>    detail claim above `0.25 cyc/native px` is admissible only when the scored subject
>    has input-verified real contrast in that band and a pre-registered, independently
>    commissioned instrument distinguishes real scene information from aliasing,
>    interpolation, sharpening, and noise. The instrument must state its physical
>    optical/sampling ceiling and refuse above it. Existing FRC, slanted-edge, and
>    single-image certificate readings remain `UNLICENSED_GT_0.25` unless separately
>    admitted under this rule. Absence of a licensed high-frequency instrument makes
>    only that band `UNMEASURED`; it does not forbid a future C1 or C12 instrument from
>    earning credit there.

Replace M1 Exact computation with:

> **Exact computation.** None is admitted in v1.7. A replacement must be
> pre-registered before its fresh holdout is rendered, must declare and commission its
> licensed frequency range, and must be implemented and audited independently of the
> pipeline producing the render. Any claimed band above `0.25 cyc/native px` must also
> satisfy decision rule 7's independent scene-content, alias-disambiguation, and
> optical/sampling-ceiling requirements.

Replace M9 steps 1 and 2 with:

> 1. For each tile and 0.05-cyc/px band inside the independently commissioned truth
>    instrument's licensed range, truth is that instrument's condition. The withdrawn
>    v1.3 `D>=1 && FRC>=1/7` rule is not truth in v1.7.
> 2. A claimed band is the highest licensed band strehl's output certificate marks
>    valid. A band above `0.25 cyc/native px` may improve the score only when its truth
>    instrument separately satisfies decision rule 7; otherwise emit
>    `UNLICENSED_GT_0.25` for that band.

### 3. PLAN LICENCE

The plan makes an above-0.25 subject a prerequisite, not a forbidden domain:

> The scorecard needs three purchases/captures that no algorithm can substitute for: a
> Zerene licence (the trial saves zero bytes — README), the slanted-edge chart and its
> Lightroom-export half (§30/§32), and one subject with real contrast above 0.25 cyc/px
> (§33). These are cheap against the months of instrument-building they unblock, and
> **every fine-detail claim in this proposal is contingent on them.**

Plan anchor: `Lightroom-export half (§30/§32), and one subject with real contrast above 0.25 cyc/px`  
Measured plan count: **1**.

It also names the intended signal:

> **What it buys at 2×:** alias-unfolded R/B at full resolution (the honest,
> physics-backed form of "beyond the demosaic"), and genuine super-Nyquist recovery in
> the mid-to-outer field at f/5.6 where M88 says the optics deliver it.

Plan anchor: `**What it buys at 2×:** alias-unfolded R/B at full resolution (the honest,`  
Measured plan count: **1**.

And C12 supplies an explicit above-plane-Nyquist consumer:

> 1. **A super-Nyquist focus cue.** The disagreement statistic responds *only* to the
>    finest transmissible structure — precisely the band where Tenengrad's response is
>    weakest relative to its noise, and the band that decides "critically sharp" from
>    "nearly sharp".

Plan anchor: `1. **A super-Nyquist focus cue.** The disagreement statistic responds *only* to the`  
Measured plan count: **1**.

### 4. BAR TEST

No existing numeric bar is lowered and no `FAIL` is retracted. The amendment replaces
a frequency ban with an evidence gate: above-0.25 credit remains unavailable until a
new instrument passes stricter scene-content, alias, sharpening, noise, and physical
ceiling controls. No current above-0.25 reading becomes licensed, and M1/M9 remain
`UNMEASURED`. A future C1/C12 result becomes eligible to be measured; it does not
become easier to pass once measured.

## F14 — M4/M8 veto on the independent M2 noise verdict

### 1. CURRENT TEXT

The operative joint row is:

> | M1 information + M2 noise + M4 flat power + M8 hull | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | M1 presently has no admissible statistic. When it is replaced, publish the replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output and pass every bar simultaneously. Until then neither a noise-only nor a detail claim is valid. |

Anchor: `| M1 information + M2 noise + M4 flat power + M8 hull |`  
Measured scorecard count: **1**.

The axis is also named as though M1 supplied a matched-information condition:

> | M2 | Noise efficiency at matched information | Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |

Anchor: `| M2 | Noise efficiency at matched information |`  
Measured scorecard count: **1**.

> ### M2 — noise efficiency at matched information

Anchor: `### M2 — noise efficiency at matched information`  
Measured scorecard count: **1**.

The later disposition preserves the reporting requirement:

> - **Accepted:** noise and information must be quoted jointly from the same output;
>   confidence precision and coverage are an opposed pair; and determinism must be
>   demonstrated at the worker count that also meets runtime.

Anchor: `- **Accepted:** noise and information must be quoted jointly from the same output;`  
Measured scorecard count: **1**.

### 2. REPLACEMENT TEXT

Use this same shared replacement for the joint row as in F4; apply it once:

> | M2 noise + M4 flat power + M8 hull; M1 detail when available | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | Publish every available value `(detail, eta, Q_flat, M8-R, M8-O)` from the same output bytes and settings. Each axis retains its own bar and verdict; the tuple has no aggregate pass state. M1's absence blocks M1 and the full SOTA sentence, not M2, M4, or M8. An M4 or M8 failure does not change M2's noise verdict, and an M2 result licenses only its stated noise claim. |

Replace the at-a-glance row and metric heading with:

> | M2 | Flat/defocused-ground noise | Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |

> ### M2 — flat/defocused-ground noise

Replace the disposition bullet with:

> - **Accepted with scope correction:** noise and every available information,
>   flat-power, and hull coordinate must be quoted from the same output bytes and
>   settings, so no report may splice a quiet render to a different quality render.
>   The values retain independent verdicts. M4 or M8 failure must be published beside
>   M2 but does not convert M2 to `FAIL` or `UNMEASURED`; likewise an M2 pass does not
>   excuse either failure or license a detail/full-SOTA claim.

### 3. PLAN LICENCE

The plan gives noise its own status and blocker:

> | Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5; 9.9× flat-field rms on the deepest stack with the compound eye indistinguishable (README) | Nothing — quotable now |

Plan anchor: `| Noise, flat/defocused ground | **Ahead, measured.**`  
Measured plan count: **1**.

### 4. BAR TEST

No M2, M4, or M8 numeric bar is lowered, and the standing M8 `FAIL` is not retracted.
**LOUD FLAG — this permits M2 to receive an independent future `PASS` while M8 remains
`FAIL`.** That is the authorised scope correction: the same bytes and all adverse
coordinates remain published, but M8 no longer vetoes the narrower noise verdict.
It does not make M2 pass today. M159's newly measured owner-plan flat-ROI result is
`FAIL` for the current shipping output, while the scorecard's richer M2 protocol
remains `UNMEASURED` on its own capture, aggregation, and comparator requirements.
