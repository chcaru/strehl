# M190 — M10 definition freeze

**Verdict: DEFINED; UNMEASURED.**

This is a preregistration, not a score. It adopts M163's five uncertainty vetoes,
adopts M166's value populations and reductions, leaves M186's grade-(A) flat-null
definition unchanged, and closes the four choices M186 found still capable of making
two honest implementations disagree.

**Normative freeze commit:** `PENDING_FREEZE_COMMIT` (filled by a provenance-only
follow-up after the freeze commit exists).

**Algorithm precommit, before the scored seed was drawn:**
`1fb63317b147280956e2b3ba827eeb60644ea530`.

No candidate M10 product, integrated checker, scored truth capture, or M10 verdict
existed when these choices were made. The live scorecard records exactly that at
`docs/proposals/2026-09-sota-scorecard.md:815,849`; M186 localised the remaining
degrees of freedom at `docs/research/M186-m10-definition-audit.md:23-26`. No RAW,
render, metric, or output under `D:\personal\macro` or `D:\edited\macro` was opened.
The public development seed is synthetic and disposable.

## 1. Normative scope and precedence

The governing plan asks for metric depth in micrometres and a depth-plus-uncertainty
TIFF product (`docs/proposals/2026-08-sota-path.md:1154-1179`). M163 froze the five
uncertainty requirements at
`docs/research/M163-m10-uncertainty.md:98-104`. M166 then supplied the upstream
populations, product semantics, reductions, boundary vetoes, and truth-envelope
rules, but expressly left M10 without a verdict until its missing inputs exist
(`docs/research/M166-m10-definition-repair.md:634`).

The operative definition is therefore:

1. M163's uncertainty decision, unchanged;
2. M166 §§2–7, including its fixed-denominator validity rules, nearest-rank value
   quantiles, hierarchical confidence rules, seven retained value bars, and two
   mandatory boundary vetoes;
3. the four replacements in this document and
   `experiments/M190-m10-definition-freeze/contract-v1.json`.

Where this document and M166 differ on one of those four replacements, M190 wins.
Nothing here changes a threshold. M186's flat-null definition remains exactly

`nearest_rank(e_step,0.975) - nearest_rank(e_step,0.025) <= 0.5 step`

at every 1,000-pixel site and pooled population, with validity `>=0.99`;
M186 already graded that contract (A)
(`docs/research/M186-m10-definition-audit.md:25`).

## 2. Freeze 1 — quota SHA-256 order

### Decision

For

`SHA256(UTF8("M10-POP-V1|") || UTF8(cell_id))`,

compare the 32 digest bytes lexicographically. This is equivalent to interpreting the
digest as one unsigned 256-bit **big-endian** integer. The complete sort key is:

1. digest bytes;
2. unsigned integer `y`;
3. unsigned integer `x`;
4. `cell_id` UTF-8 bytes.

The fourth key makes even a SHA-256 collision at one coordinate a total order.
Duplicate `cell_id` remains a truth-package error before sorting.

### Why

The byte order is genuinely arbitrary. Nothing in the optics or the statistic
prefers big-endian to little-endian. I chose raw digest-byte lexicographic order
because Python, Rust, PowerShell/.NET, and most hash tools can implement it without
first constructing a 256-bit integer. The worked integer interpretation exists only
to remove doubt.

### Worked round trip

Input:

`cell_id = ruler|capture-01|strip-07|00000123|00000456`

UTF-8 preimage bytes:

`4d31302d504f502d56317c72756c65727c636170747572652d30317c73747269702d30377c30303030303132337c3030303030343536`

SHA-256 digest:

`e0dc8a1fe8bb66b1e6e22eb0de1c5cd969bd18d8fde53f6e6a5280f47071a4ef`

Unsigned big-endian decimal:

`101707737738166663357154239799626950601313803761331969497607860115891805070575`

Both the Python reference and an independent PowerShell/.NET implementation computed
those bytes and values.

### Disagreement foreclosed

M186 demonstrated that big- and little-endian order select different quota members
(`docs/research/M186-m10-definition-audit.md:23`). This freezes one population.
Two conforming checkers can no longer score different cells while both claiming to
implement “unsigned 256-bit.”

## 3. Freeze 2 — the origin divisor `N`

### Decision

Within one capture and one admitted truth realization:

`included = truth_target && candidate_valid`

`N = count(included)` over the complete, fixed, **unresampled** capture population.

`origin_step = exact_sum(raw_step[included]) / N`.

The exact real sum of the binary64 summands is rounded once to binary64; division is
binary64 round-to-nearest, ties-to-even. Reference-error perturbation occurs before
this fit. The origin is then held fixed during site resampling. It is not recomputed
per site, layer, strip, boundary side, or bootstrap subset.

If `N=0`, every origin-dependent metric takes its M166 candidate-worst value.
Candidate-invalid targets remain in every fixed validity denominator and synthetic
interior invalidity remains a confusion violation.

### Why

This choice is not arbitrary. It makes the one allowed origin the unweighted
arithmetic-mean residual of the finite estimates that actually exist: the
least-squares additive translation on those estimates. Dividing the same sum by all
truth targets would silently impute zero residual to every refusal, pull the origin
toward zero as validity worsens, and make the fitted translation mean something other
than “remove one additive offset.” Missingness is already and separately priced by
the fixed validity denominator; it must not also move the origin through an implicit
zero.

### Worked round trip

Raw steps `[1.0, 2.0, 99.0, 4.0]`, validity
`[true, true, false, true]`:

- `N = 3`;
- exact sum `= 7.0`, binary64 `401c000000000000`;
- origin `= 7/3`, binary64 `4002aaaaaaaaaaab`;
- valid residual binary64 values:
  `bff5555555555556`, `bfd5555555555558`,
  `3ffaaaaaaaaaaaaa`.

Using all four truth targets would instead divide by four and produce `1.75`; the
commissioning control confirms the bits move.

### Disagreement foreclosed

One checker can no longer use the number of candidate-valid estimates while another
uses the number of fixed truth targets. They now fit the same physical translation
and cannot change rank/error verdicts by choosing a different denominator.

## 4. Freeze 3 — stored product, hashes, and total failure mapping

### 4.1 Exact package

One submitted capture is one directory containing exactly:

- `rgb.tif`;
- `depth-um.tif`;
- `depth-sigma-um.tif`;
- `depth-valid.tif`; and
- `depth-manifest.json`.

The JSON manifest must validate against
`experiments/M190-m10-definition-freeze/depth-manifest.schema.json`.
It is RFC 8259 UTF-8 without BOM. Duplicate keys, `NaN`, `Infinity`, unknown fields,
uppercase digests, and implicit defaults are invalid.

The three product TIFFs preserve M166's semantics
(`docs/research/M166-m10-definition-repair.md:112-139`) and now have a complete
wire contract:

- little-endian BigTIFF version 43;
- no compression (`Compression=1`) and no predictor (`Predictor=1`);
- `PhotometricInterpretation=BlackIsZero`, `PlanarConfiguration=Chunky`,
  `Orientation=1`, no extra samples;
- depth and sigma: one IEEE-754 binary32 sample, `SampleFormat=3`,
  `BitsPerSample=32`;
- validity: one unsigned sample, `SampleFormat=1`, `BitsPerSample=8`, values only
  `0` or `1`;
- row-major decoded order, the campaign's exact width/height, and no checker
  resampling.

At mask `1`, depth and sigma are finite and the sigma sign bit is zero. At mask `0`,
both float planes carry exactly binary32 bits `0x7fc00000` (little-endian file bytes
`00 00 c0 7f`). Negative zero is therefore invalid as a valid sigma.

The manifest binds the exact byte length and digest of the RGB/product files and of
the independently frozen common-input manifest, capture manifest, focus-axis map,
field-curvature profile, gear profile, executable, settings, and output-grid
descriptor.

### 4.2 Hash algorithm and encoding

Every manifest hash is:

`lowerhex(SHA256(exact_file_bytes))`.

There is no text decoding, newline conversion, TIFF decoding, canonical-JSON
re-serialization, or length prefix before hashing. The length is a separate mandatory
field.

This choice has an arbitrary part and a measurement-serving part. Lowercase rather
than uppercase hex is arbitrary. Hashing the exact bytes rather than parsed content is
not: it binds the object actually scored and prevents two parsers from normalizing
different byte streams into one apparent artifact.

Worked raw-artifact fixture:

- input bytes: `00 ff 0a 4d 31 39 30`;
- byte length: `7`;
- SHA-256 lowerhex:
  `a88b7727323b709011d7d67069c7ab4462660cf49842925709ea816f3303ad6f`.

### 4.3 Total mapping — no skip state

The checker runs in this order:

1. checker-contract recognition;
2. truth/instrument preflight, before candidate bytes are opened;
3. product availability;
4. candidate product contract;
5. metric decision.

Every emitted record is exactly one of:

`PASS`, `CANDIDATE_FAIL`, `PRODUCT_UNMEASURED`, `TRUTH_UNMEASURED`, or
`CHECKER_ERROR`.

The mandatory identity is:

`total_examined = PASS + CANDIDATE_FAIL + PRODUCT_UNMEASURED + TRUTH_UNMEASURED + CHECKER_ERROR`.

There is no `SKIP`. If a failed parent prevents evaluating a required child, the child
receives the parent's attribution and a `DEPENDENCY_BLOCKED` reason. Any unknown
failure code maps to counted `CHECKER_ERROR` and overall
`UNMEASURED_CHECKER_ERROR`.

Record outcomes project to exactly one verdict: `PASS -> PASS`,
`CANDIDATE_FAIL -> FAIL`, and every product/truth/checker unavailable outcome
`-> UNMEASURED`. If several failures coexist, the checker reports all codes sorted by
the frozen stage and code order and uses the first as `primary_disposition`; the
verdict itself remains singular.

Top-level mapping is total:

| Condition | Verdict |
|---|---|
| Unknown schema, internal exception, unmapped condition, or bad count partition | `UNMEASURED_CHECKER_ERROR` |
| Missing/invalid ruler, focus scale, flat certificate, repeat uncertainty, truth envelope, synthetic seed/render/certificate, or truth manifest | the corresponding named `UNMEASURED_*` truth disposition |
| Availability query before a candidate package exists | `UNMEASURED_PRODUCT_ABSENT`; this mode cannot emit M10 `PASS` or `FAIL` |
| Declared score run with a missing/malformed/hash-mismatched product package | `FAIL_PRODUCT_CONTRACT` |
| Product and truth valid; every admitted realization passes | `PASS` |
| Product and truth valid; every admitted realization fails | `FAIL` |
| Product and truth valid; admitted realizations split pass/fail | `UNMEASURED_TRUTH_ENVELOPE` |

The fixture exercises all five record outcomes: `1+1+1+1+1=5` examined. The
commissioning suite separately plants an unknown manifest member named
`default_pass`; it is rejected.

### Disagreement foreclosed

Writers and checkers now agree on file names, JSON shape, TIFF tags, byte order,
sentinel bits, hash bytes, digest text, and every reachable failure disposition.
A missing or malformed check cannot disappear from the denominator or print like a
pass.

## 5. Freeze 4 — hidden synthetic instrument

### 5.1 What this arm is for

The synthetic arm is a structural falsifier for a hard-coded plane, layer collapse,
and boundary smoothing. It is not a synthetic claim about this camera's photon
statistics. The physical ruler remains the independent physical anchor, as M166
requires (`docs/research/M166-m10-definition-repair.md:243-280`).

For that reason the scored synthetic arm has **no added sensor noise**. This is a
measurement-serving choice: a self-authored noise model would create a second
calibration dependency and could only validate itself. Randomness hides the surface,
texture, boundary, and target realization; it does not pretend to be camera
calibration.

Several renderer details — a square box PSF, 8-micrometre step, and the exact texture
range — are arbitrary controlled-stimulus choices. They are not defended as optical
truth. They are frozen because two renderers must produce the same test, and because
the arm's job needs exact depth truth, both layers inside the bracket, a real
transition band, and enough non-affine curvature to prove a plane cannot pass.

### 5.2 Seed preregistration

The complete algorithm was committed first at
`1fb63317b147280956e2b3ba827eeb60644ea530`. Only then did
`System.Security.Cryptography.RandomNumberGenerator.Fill` draw one 32-byte scored
seed. There were no retries and the seed was not printed.

Public commitment:

`063f5e250148c211517f538e78595064e43b5042ec779ae59396229993c0e87e`

where

`commitment = SHA256(ASCII("M10-SYNTH-SEED-COMMIT-V1") || 0x00 || seed[32])`.

The public receipt is
`experiments/M190-m10-definition-freeze/scored-seed-commitment.json`.
The local escrow is the ignored DPAPI ciphertext
`experiments/M190-m10-definition-freeze/private/scored-seed.dpapi`,
262 bytes, ciphertext SHA-256
`eeddacc49ae8daf580c03a1d99aefeef95828bc0f7f1daab7299df4750fdbf0f`.

Disclosure is permitted only after the candidate executable, settings,
common-input manifest, and campaign manifest are hash-frozen. The candidate process
receives rendered frames, not the seed or latent truth. Truth is released only after
candidate product hashes are frozen. Missing escrow, a commitment mismatch, a second
draw, or early disclosure makes the synthetic arm
`UNMEASURED_SYNTHETIC_TRUTH`; it does not license another seed.

### 5.3 PRF and worked round trips

All synthetic random access uses one function:

`SHA256("M10-SYNTH-PRF-V1\0" || seed[32] || uint8(label_len) || ASCII(label) || payload)`.

All payload integers are unsigned big-endian.

Development seed:

`000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`

Parameter block for instance `0`, label `PARAM`, payload `00000000`:

- preimage:
  `4d31302d53594e54482d5052462d563100000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f05504152414d00000000`;
- digest:
  `cf449d6ac395e87a74b9c682a14b12a09d31022aba31b9f019aad5001751808a`;
- decoded parameters:
  boundary `131`, phases `(4,5,2)`, base `15`, separation `13` steps.

Texture block for instance `7`, far layer, B channel, local `(130,111)`:

- payload `0000000701020082006f`;
- preimage:
  `4d31302d53594e54482d5052462d563100000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f035445580000000701020082006f`;
- digest:
  `3a79a37eacc4678e5033736f5fea68d962e354d08c4701acf1fb0ce071c4ab4e`;
- resulting unsigned-16 texture value: `23161`.

The independent PowerShell implementation re-derived both preimages and digests.

### 5.4 Exact surface, renderer, and populations

The scene is twenty independent `256x256` tiles in a `5x4` grid
(`1280x1024`). For local integer `(x,y)`:

`tent8(t) = 4 - abs((t mod 8)-4)`.

Seeded instance parameters are defined byte-for-byte in the machine contract. The
two depths in focus-step units are:

`z_near = base + 3*(tent8(x+phase_x)-2) + (tent8(y+phase_y)-2)`

`z_far = z_near + separation + (tent8(y+far_phase_y)-2)`.

Truth micrometres are exactly `8*z`. The 42 focus frames are integer steps `0..41`.
On the public development seed, all selected truth lies strictly inside the bracket
at steps `4..38`, and the minimum layer separation is `10` steps against the required
`8`.

The latent boundary is the vertical continuous line
`x=boundary_column+0.5`; signed distance is exact and half-integral. The near layer
occupies integer columns through `boundary_column`; the far layer exists everywhere.
Each layer/channel texture is the specified PRF value in `[8192,57343]`.

At frame `f`, each layer's square blur radius is
`min(12,abs(z_layer(x,y)-f))`. Windows clip at their tile, never cross into another
instance, and the exact premultiplied composite is:

`round_ties_even((near_sum*far_area + (near_area-near_count)*far_sum) / (near_area*far_area))`.

Normative frame bytes are row-major interleaved RGB unsigned-16 little-endian. A
TIFF/DNG wrapper is admitted only if an independent decode reproduces those bytes
exactly.

The renderer probe contains four `(instance,frame,x,y)` points. Its 24 output bytes
are:

`7871ce77c86e626d0c753968c36cc672426e2c73996e9670`

with SHA-256:

`ab9bc1314d52f68ace7837883212570781ce1e4e2f2552e7d084db5f9607ab5b`.

Every instance has exactly:

- 500 near-interior targets, distance `<-32`;
- 500 far-interior targets, distance `>+32`;
- 500 near-boundary targets, `-32<=distance<0`;
- 500 far-boundary targets, `0<distance<=32`.

Thus the scored synthetic population is exactly 20,000 interior and 20,000 boundary
pixels. Target construction and its PRF ordering are fully specified in
`contract-v1.json`.

### 5.5 Affine-certificate acceptance

Every 2,000-cell instance carries 101 disjoint, equally spaced collinear triples.
Each triple must be in the scored population and satisfy:

`abs(z0 - 2*z1 + z2) > 4 steps`.

This is a proof, not a numerical optimizer. For residuals to any affine plane, the
plane's second difference is zero. If all three absolute residuals were `<=1`, the
triangle inequality would give an absolute residual second difference `<=4`.
Therefore every accepted triple forces one distinct residual `>1`. With 101 such
residuals among 2,000 values, nearest-rank q95 is strictly `>1`. No affine plane can
meet the retained p95 bar.

The public development fixture gives exactly 101 accepted triples for every one of
20 instances, with minimum absolute second difference `6`. After the one scored seed
was committed, the verifier checked the same certificate condition at 20/20 without
printing the seed or any candidate metric.

### Disagreement foreclosed

Two instruments can no longer choose different surfaces, texture RNGs, seed
mappings, scored seeds, blur kernels, target masks, boundary distances, or
certificate heuristics. A plane's defeat is accepted by one constructive inequality,
not by a checker-specific optimizer or tolerance.

## 6. Machine-checkable artifacts and verification

| Artifact | Role | SHA-256 at freeze |
|---|---|---|
| `experiments/M190-m10-definition-freeze/contract-v1.json` | Four normative contracts and total failure map | `a873779e28fee08dd5d51aa500a39fab556a92f7d4be7027b7baa311df8d314b` |
| `experiments/M190-m10-definition-freeze/depth-manifest.schema.json` | Strict manifest JSON Schema | `737755e055bbbd67c83e4b6acb4b8e82f171700ba54f18cab00685eae518b1e8` |
| `experiments/M190-m10-definition-freeze/fixtures.json` | Hash/origin/renderer/certificate round trips | `594e37ff5a90ecd917599aba659ba122c3a32818f33f1df11234f5edb02b819a` |
| `experiments/M190-m10-definition-freeze/reference.py` | Executable reference semantics | frozen in the normative commit |
| `experiments/M190-m10-definition-freeze/verify_hash_fixtures.ps1` | Independent hash/order reimplementation | frozen in the normative commit |
| `experiments/M190-m10-definition-freeze/scored-seed-commitment.json` | One-draw public seed receipt | frozen in the normative commit |

Commands run from the repository root:

```powershell
python experiments\M190-m10-definition-freeze\generate_fixtures.py
python experiments\M190-m10-definition-freeze\verify_freeze.py
python experiments\M190-m10-definition-freeze\commission.py
& experiments\M190-m10-definition-freeze\verify_hash_fixtures.ps1
& experiments\M190-m10-definition-freeze\seed_ceremony.ps1 -Action Verify
```

Read results:

- Python contract/fixture verifier: every line `PASS`, final `VERDICT GREEN`;
- independent PowerShell hash verifier: 13 `PASS`, final `VERDICT GREEN`;
- mutation commissioning: `COMMISSIONED 8/8`;
- scored-seed escrow and certificate check: commitment PASS, certificates 20/20,
  minimum separation PASS, plaintext not printed.

The eight planted failures are little-endian quota interpretation, all-target origin
division, uppercase digest, an extra `default_pass` member, only 100 affine triples,
a weakened second difference, one flipped renderer bit, and including the invalid
origin row. All eight were caught.

## 7. Exact scorecard replacements routed to the owner

Both anchors below are complete physical lines in the live file, not
whitespace-collapsed matches.

### Anchor `:815`

Current text, occurrence count **1**:

> | M10 | Physical depth product | **PARTIALLY DEFINED; DEFINITION BLOCKED.** M166 froze the flat-null reduction and most validity rules, but the quota hash byte order, the origin divisor `N`, the manifest hash/schema contract, and the hidden synthetic instrument remain open, so two implementations can still diverge. Provisional bars are valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`; flat-null span `<=0.5` step; layer confusion `<=1%`; boundary bias `<=0.5` step and p95 `<=1.0` step; uncertainty coverage `[0.93,0.97]`, at least 9/10 decile variance ratios in `[0.90,1.10]`, and reported half-width median `<=0.5`/p95 `<=1.0` step. These are not yet usable bars and no M10 verdict exists. |

Replacement:

> | M10 | Physical depth product | **DEFINED; UNMEASURED — MISSING PRODUCT, CHECKER, AND SCORED TRUTH.** M190 adopts M163's five uncertainty vetoes and M166's value populations/reductions, leaves the flat-null rule unchanged, and preregisters the quota digest order, origin divisor, product/manifest wire contract with total fail-closed outcomes, and the hidden synthetic renderer, one-draw seed commitment, target populations, and affine certificate. Bars are valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`; flat-null span `<=0.5` step; layer confusion `<=1%`; boundary bias `<=0.5` step and p95 `<=1.0` step; uncertainty coverage `[0.93,0.97]`, at least 9/10 decile variance ratios in `[0.90,1.10]`, and reported half-width median `<=0.5`/p95 `<=1.0` step. No compatible candidate product, commissioned integrated checker, or scored physical/synthetic truth package exists, so no M10 verdict exists. |

### Anchor `:849`

Current text, occurrence count **1**:

> | M10 | **PARTIALLY DEFINED; DEFINITION BLOCKED; (b)(c)** | M166 froze the flat-null reduction and most validity rules, so this is no longer "pending M166". The remaining definition blockers are the quota hash byte ordering, the origin divisor `N`, the product-manifest contract, and the hidden synthetic instrument. Product and checker implementation is compute work; fresh ruler, focus-axis and repeat truth is capture/metrology work; certifying the existing flat battery may avoid fresh flat capture. No scored truth capture or compatible product exists and M10 has no verdict. Not `(e)`: `:834` defines `(e)` as scientifically measurable now, which M10 is not. |

Replacement:

> | M10 | **DEFINED; UNMEASURED; (b)(c)** | M190 closes the four remaining definition gaps before any candidate output: quota SHA-256 is byte-lexicographic/big-endian with a total tie-break; origin `N` is the full-capture count of candidate-valid truth targets; the depth/sigma/valid package has a strict JSON/TIFF/hash contract and total fail-closed outcome map; and the hidden synthetic renderer, PRF, one-draw scored-seed commitment, exact populations, and affine-certificate proof are frozen. Remaining blockers are implementation/evidence: a compatible native-grid product and commissioned integrated checker, fresh ruler and independent focus-axis/repeat truth, and either output-blind certification of the existing flat battery or a fresh flat. The scored synthetic arm is defined and precommitted but has not been rendered against a frozen candidate. No M10 verdict exists. Not `(e)`: `:834` defines `(e)` as scientifically measurable now, which M10 is not. |

## 8. Final disposition

**M10 becomes `DEFINED; UNMEASURED`, not `DEFINITION BLOCKED`.**

What remains is concrete execution and evidence: Strehl still emits no compatible
depth/sigma/valid product (`docs/research/M163-m10-uncertainty.md:216`); no integrated
checker has been commissioned; fresh ruler, focus-axis, and repeat/local truth are
absent; the flat battery still needs output-blind planarity certification or
replacement; and the precommitted synthetic arm must be rendered and scored only
after candidate hashes freeze. None of those leaves a researcher free to choose the
statistic, encoding, population, seed, or certificate after seeing a result.
