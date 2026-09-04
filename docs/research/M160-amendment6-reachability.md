# M160 — Amendment 6 reconciliation and axis reachability

Status: **SCORECARD RECONCILED; REACHABILITY CLASSIFIED; NO IMAGE OR SCORE
OUTPUT READ**

This report answers two questions:

1. where scorecard v1.8 overstated or obscured the limitations adopted by the
   owner's plan in Amendment 6; and
2. which axis has the shortest practical path to the program's first pass.

The source snapshot used for the reconciliation is:

- authoritative plan: `docs/proposals/2026-08-sota-path.md`, Amendment 6,
  wording-repair commit `d839c402`, SHA-256
  `1E075C8BECEC35BC67231868781E614DC0748989F14E2F172C777E3964CEB443`;
- pre-edit scorecard: commit `1549df47`, SHA-256
  `EF7CBB5CD740C647BDAF360DD574421449BE4F24A17D971F295531A569892CCF`;
- reachability evidence cutoff: repository `HEAD` `7f0f54d4`.

Lane M166's complete M10 definition proposal landed within that evidence cutoff
at `832a2e85`. This Amendment 6 task does not transcribe that separate
specification into the scorecard; Part 2 takes M166's ruling as given for
reachability, while the scorecard's current M10 card remains non-operative until
its dedicated adoption.
As of the stated reachability cutoff, M167's blinded-admission preregistration
had landed at `20ef67e8`, with its runner, canary, and hash freeze following
through `7f0f54d4`; the canary had not yet run. This report remains a ranking
snapshot at that cutoff rather than silently incorporating later lane outcomes.

**Evidence labels.** `VERIFIED BY RUNNING` means this lane executed a command
and read its output. `INFERRED BY READING` means the conclusion is a synthesis
of the cited committed specifications, reports, or current scorecard. No
classification below is represented as a fresh measurement.

## 1. Amendment 6 inconsistencies and repairs

Every quotation in this table was re-read from the source snapshot above
immediately before editing. Scorecard line references name the pre-edit
`1549df47` blob, not the post-edit line positions.

| ID | Pre-edit scorecard | Authoritative Amendment 6 | Inconsistency | v1.9 repair |
| --- | --- | --- | --- | --- |
| A6-1 | `scorecard@1549df47:792-801`: *“No admissible detail statistic in this repository is sharpening-safe: no statistic that still responds correctly to physical blur and genuine improvement survives sharpening. ... [A] future instrument [must] have a structural reason sharpening cannot improve it.”* | Plan §16.1, lines 2678-2693: *“no output-only statistic can guarantee the intended ranking across those worlds without additional identifying assumptions or evidence”*; valid information includes an independent reference, scoped certified target, or validated prior, and *“This does not prove that every no-reference metric is impossible.”* | The scorecard described a repository inventory but omitted the load-bearing observation boundary at the point of the claim, allowing an empirical inventory to read as a universal impossibility theorem. | The inventory is now explicitly limited to tested candidates under the current output-only contract. The exact hedge — **“without an assumption or observation outside those outputs”** — and the admissible external-information families are stated in the operative rule and again where M1's structural protection is defined. |
| A6-2 | `scorecard@1549df47:855-863`: *“the existing flat-ROI statistic ... [is not] a stand-alone comparative noise instrument: a blur challenge improves it to `0.571215x`.”* The card did not state how that empirical failure related to the broader output-only argument. | Plan §16.2, lines 2701-2717: the single-image sentence is qualified, and *“The three instrument deaths ... are not all instances of one theorem.”* D8 is algebraic, band-power is empirical, and only M2 is the identifiability construction. | The old card's silence could let three differently supported failures be read as one theorem, and it did not record that M164's external-reference candidate remains synthetic-only. | M2 now separates the `0.571215x` empirical defeat from its output-only identifiability construction, distinguishes both from D8 and band power, records `Q_EIN` as unadmitted synthetic evidence, and retains `UNMEASURED`. |
| A6-3 | `scorecard@1549df47:815`: *“Input needed by a future replacement. The capture deficiency remains.”* | Plan §16.3, lines 2723-2728: *“fresh capture is the currently specified way to obtain that information. Capture is therefore a precondition of the instrument, not a way around it.”* | “Deficiency” left capture looking like a separate obstacle or an alternative route around the instrument. | The M1 card now says the listed captures are part of the currently specified instrument's construction and cannot themselves admit or replace the instrument. |
| A6-4 | `scorecard@1549df47:1454-1459`: *“M9 remains DEFINITION BLOCKED until M1 admits an independent, higher-sampling, candidate-specific acuity-truth predicate. No threshold invented inside M9 may substitute for it.”* Similar `M1-qualified` shorthand appears in M3 and M11. | Plan §16.1, lines 2690-2693: *“M1 is the current proposed implementation of that condition, not the only mathematically possible one.”* Plan §16.4, lines 2739-2754 adds that a sufficiently powered independent same-resolution reference can normalize relative transfer, while M1 remains *“the only currently specified and physically actionable route with an evidenced path to an admissible result.”* | The registry dependency was correct, but without an explicit interpretation it could be read as mathematical uniqueness. | A central rule now defines every `M1-qualified`/`M1 truth` reference as registry shorthand for the currently specified and physically actionable route. M9 repeats the distinction locally and allows an independently admitted candidate-specific truth producer without pretending one exists today. |

**INFERRED BY READING.** These changes narrow claims; they do not relax an
instrument, capture, comparator, threshold, or verdict. M1 still has no
admitted instrument or numeric bar. M2 remains `UNMEASURED`. M9 remains
`DEFINITION BLOCKED`. M8 remains `FAIL` on M8-R at `1.030569%` against exactly
`0.0000%`; M8-O v1.5 remains `UNMEASURED`.

**VERIFIED BY RUNNING.** The verifier compares all twelve at-a-glance bar rows
byte-for-byte with `1549df47`, checks the Amendment 6 source anchors by
whitespace-normalised content, checks the two protected verdicts, and checks
the twelve-row reachability partition. Its result and negative-control count
are recorded in §5.

## 2. Exactly-one blocker rule

Many axes have conjunctive blockers. To satisfy the requested exactly-one
classification without hiding later dependencies, this report uses the
**narrowest current status that already prevents the axis's next admissible
reading**:

1. `INSTRUMENT VOID`, `DEFINITION BLOCKED`, or a mandatory inherited
   qualification instrument that is absent is `(a)`;
2. a required product output that is absent, or a measured product defect that
   prevents a pass, is `(e)`;
3. a missing licence or physical reference item controlled by the owner is
   `(d)`;
4. a sound instrument whose registered physical population is absent or
   underpowered is `(c)`;
5. only when the instrument, product, purchases, and capture already exist and
   execution alone remains is the row `(b)`;
6. only an admitted pass is `(f)`.

The row still names downstream dependencies. Thus M5 and M6 are `(c)` because
their current admissible reading first stops at an absent/underpowered
population, even though later detail/comparator dependencies remain. Conversely,
`(a)` on M3 or M11 does not say their own veil or timing checker is void; it
says the complete axis cannot be adjudicated while its mandatory qualification
instrument is absent.

## 3. Twelve-axis classification and ranking

The rank is dependency depth, not a wall-clock estimate. Absolute timing is
quarantined on the current host. M3 and M8 are classified from the
orchestrator's assignment and committed scorecard only; this lane did not
investigate the live M169 or M170 work.

| Rank | Axis | Class | What precisely blocks a pass | What clears the assigned class |
| ---: | --- | --- | --- | --- |
| 1 | M8 | **(e)** | **INFERRED BY READING.** Shipping Catmull-Rom fails M8-R at `1.030569%`; M8-O v1.5 is unmeasured. | Land the clamped-cubic gather in the product, preserve the zero-violation crop/reference arm, independently recommission the corrected M8-O checker at `e5489d64`, and obtain `V=0` for both M8-R and M8-O on every scored capture. |
| 2 | M4 | **(c)** | **INFERRED BY READING.** The retained component has only 55/84 medication tiles and 0/83 foam tiles; every existing commissioning flat supplies zero eligible tiles. | Acquire a fresh untouched medication background supplying at least 84 eligible tiles, a fresh foam background supplying at least 83, and a separate non-holdout development flat supplying at least 100. M152 records the exact shortfalls as 29 medication and 83 foam tiles. |
| 3 | M7 | **(d)** | **INFERRED BY READING.** No traceable target exists, and required common-input comparator output cannot be saved under the expired Zerene trial. | Obtain a matte ISA ColorGauge Nano with a serial-linked certificate whose scored uncertainties meet `U95<=0.25 DeltaE00`, a measured illuminant (for example the specified C-800 rental), and a Zerene Professional licence; then shoot the tilted patch target plus the textured colour-seam coupon. |
| 4 | M10 | **(e)** | **INFERRED BY READING.** M166 has supplied a complete definition proposal, but strehl emits none of the required depth, uncertainty, or validity planes. | Implement the hash-bound native-grid depth/uncertainty/validity product and integrated decoder/checker contract. A fresh metrology ruler unit, independent focus-axis map, flat truth, and hidden two-layer truth are later required; product absence is the first non-substitutable blocker under the rule above. |
| 5 | M1 | **(a)** | **INFERRED BY READING.** M167's original battery is commissioned, but no deployable detail instrument has passed it. Its blinded-admission protocol is frozen but not yet commissioned and fail-closes without an attested disposable sandbox; M168 found no archive-only calibrated reference route. | Supply and attest the admission sandbox, commission the blinded protocol, admit an externally anchored detail/transfer instrument through it, then commission the instrument's current staged physical route. Capture is input to that instrument, not a substitute for it. |
| 6 | M3 | **(a)** | **INFERRED BY READING; LIVE M169 WORK NOT INVESTIGATED.** M3's own statistic is defined and its 1,233-edge input census is sufficient, but the required best-comparator envelope has no admitted M1 qualification. | Admit the current M1 registry route or another independently accepted qualification instrument, then materialize the common-input comparator outputs and profile-package/input-only warp evidence. |
| 7 | M5 | **(c)** | **INFERRED BY READING.** The burned grid and development slide cannot score; no fresh controlled-slide holdout exists. | Acquire the fresh IBIS/OSS-off controlled-slide holdout with independently repeated sw4/sw10 passes, checker-only dense sweep, witnesses, matching dark/flats, and at least 500 eligible tiles overall with 50 per capture. The current combined M1/M5/M9 request remains explicitly unsafe to shoot. |
| 8 | M6 | **(c)** | **INFERRED BY READING.** The executable census is underpowered: existing high-arm counts are salt `1,193`, battery `1,230`, and angled ruler/grid `0`, below the required `10,000` recoverable pixels per scored capture. | Acquire fresh controlled highlight/shadow stacks for the registered foam, Maldon salt, ISO-100 battery, highly angled ruler, and bright grid/fabric populations, each with at least 20 non-overlapping tiles and at least 10,000 input-defined recoverable pixels. |
| 9 | M2 | **(a)** | **INFERRED BY READING.** `R_box9` is rejected; the reference-bearing `Q_EIN` candidate has synthetic author evidence only and has not passed blinded independent admission or physical commissioning. The admission protocol itself is not yet commissioned and requires an attested disposable sandbox. | Supply and attest the admission sandbox, commission the blinded protocol, admit a scoped reference-bearing or certified featureless/defocused-ground M2 instrument with its assumptions explicit, then produce qualifying common-input comparator outputs. |
| 10 | M11 | **(a)** | **INFERRED BY READING.** The timing campaign is defined, but its denominator requires modes qualified through admitted M1 and M2 instruments; those do not exist. Absolute product timings are also quarantined. | Admit the qualification instruments first, then obtain licensed Zerene PMax/DMap and a commit-pinned fork build, build the complete harness/trace, and reproduce absolute timing on a quiet host or use an approved within-run ratio in which load cancels. |
| 11 | M12 | **(e)** | **INFERRED BY READING.** Existing diagnostics show fixed-worker determinism PASS but cross-worker scaling invariance FAIL because reduction order changes with worker count. The full bar also requires the 16-worker output to pass M11. | Make product reductions worker-count invariant, then run the registered N=33/105/299 and 1/2/4/8/16 matrix. Correctness arms may run under load; any absolute-time arm remains quarantined. |
| 12 | M9 | **(a)** | **INFERRED BY READING.** No admitted candidate-specific `truth_valid` producer exists; the current registry routes that requirement through M1. | Admit an external acuity-truth instrument, then supply the balanced 1,000-cell manifest, matched sw4/sw10 repeats, calibration, and the acuity/sigma/`n_eff` product. |

Classification partition: `(a)=5`, `(b)=0`, `(c)=3`, `(d)=1`, `(e)=3`,
`(f)=0`; total `12`.

## 4. Recommendation

### Spend the next block on M8

**INFERRED BY READING.** M8 is the only axis whose current blocker is confined
to a narrow product change plus an already specified deterministic
recommission-and-score path. It needs no owner purchase, new capture, or new
scientific instrument. The clamped gather has already shown zero M8-R
violations diagnostically; the remaining work is to land the candidate and
earn, rather than infer, both exact-zero readings.

**Case against the recommendation.** M8-R zero does not imply M8-O zero. The
clamp changes values delivered to the merge, and the corrected v1.5 M8-O
checker is not yet independently recommissioned. Any single M8-O violation
leaves the axis failed. Landing the kernel may also expose a product-quality
regression that M8 itself cannot judge because M1 remains absent. Thus M8 is
the shortest path, not a promised pass.

The next independent routes are M4 (small, exact capture deficit), M7 (bounded
purchase plus capture), and M10 (defined target but substantial product and
truth construction). M3 is attractive diagnostically because its own capture
and statistic exist, but it cannot become the first complete pass while its
M1-qualified comparator limb remains unavailable.

## 5. Verification

Commands:

```powershell
python -B experiments\M160-scope-audit\verify_amendment6.py
python -B experiments\M160-scope-audit\nc_amendment6.py
```

Result: **67/67 checks PASS, `VERDICT GREEN`; 14/14 targeted controls PASS.**
The controls individually remove the hedge, universalize the no-reference
claim, merge proof statuses, make capture a workaround, assert M1 uniqueness,
promote M2, erase the M8 failure, soften M3, damage the twelve-row partition,
replace the top pick, erase its counterargument, and corrupt source provenance;
one whitespace-only reflow remains GREEN.

## 6. Routed defects outside M160 ownership

These files were not edited by M160. The orchestrator subsequently applied all
four routed repairs at `44f9c3c0`; the quotations below are retained as the
historical routing record, not as claims about current file contents.

1. `docs/OWNER-ACTIONS.md:48-50` still says:

   > Blocker `(a)` ... is the only blocker that cannot be bought, shot, or coded
   > around. It has to be invented.

   Exact proposed replacement:

   > **Blocker `(a)`, an admissible detail/transfer instrument, is attached to
   > eight axes by the current scorecard. Capture alone cannot supply it:
   > capture provides identifying information required by the current usable
   > instrument and is therefore a precondition, not a workaround. M1 is the
   > only route with a practical path today, not the unique mathematical
   > anchor.**

2. `docs/OWNER-ACTIONS.md:329` ends *“This cannot be bought or shot around.”*

   Exact proposed replacement:

   > **A better capture is not an alternative to the instrument; it supplies
   > external identifying information that the current usable instrument
   > requires.**

3. `docs/capture-requests/2026-09-319-frame-session.md:183-186` says:

   > Six candidate detail statistics have failed because no single-image
   > measurement separates resolved detail from sharpening. The escape is an
   > independently sampled, higher-magnification image of the same patch.

   Exact proposed replacement:

   > **Six tested candidate detail statistics have failed. Under the current
   > output-only observation contract, none has separated resolved detail from
   > sharpening without an external model, prior, or reference. The current
   > usable route supplies that external information with an independently
   > sampled, higher-magnification image of the same patch.**

4. `docs/STATUS.md:6354-6357` says:

   > Most died the same structural death: no single-image high-frequency
   > statistic can separate resolved detail from sharpening, because
   > sharpening adds exactly the thing being measured.

   Exact proposed replacement:

   > **Most died through the same observed failure pattern: among the
   > candidates tested under the current output-only contract, no commissioned
   > single-image high-frequency statistic separated resolved detail from
   > sharpening. Without an external model, prior, or reference, those pixels
   > do not universally certify latent signal provenance.**
