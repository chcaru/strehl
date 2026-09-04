# M152 — shared input-only M3/M4 site census

**Status:** census frozen and run; M3 capture is sufficient; M4 needs new
capture; M3 checker built but **not admitted** after a required commissioning
arm exposed a one-sided broad-veil blind spot.

**Pre-output census freeze:** commit `f7dde90a`, definition SHA-256
`b2e872a6a8214d4fbe379287f52fc57b8f5e61f292aab4c30e96b11d49325879`.

**Measured census artifact:** `experiments/M152-site-census/out/census-manifest.json`,
SHA-256 `35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d`.

## Headline

**M3 has enough existing input capture. M4 does not.**

| axis | input-only result | verdict |
|---|---|---|
| M3 | 1,233 broad-eligible edges; 221 duck tape, 399 chia, 511 flower/fern, 102 razor; every site has 400 native-pixel reach; every capture exceeds 50; exactly 500 sites frozen for scoring | **SUFFICIENT — no new M3 photons** |
| M4 edge arm | 10,355 eligible sites; 2,435 / 2,284 / 2,121 on the three fabric stacks, 1,289 duck tape, 2,226 flower/fern | **SUFFICIENT** |
| M4 flat arm | 178 eligible sites: medication pill 55, exact bee background 123, foam 0; the frozen scored quotas are 84 / 83 / 83 | **NEEDS NEW CAPTURE** |
| M4 flat commissioning | coffee bubbles 0; all three already-burned flat-slide stacks 0 | **NEEDS A SEPARATE DEVELOPMENT CAPTURE** |

The existing M4 corpus selects only 138 of its required 250 flat sites and all
250 edge sites: 388/500 scored sites. The edge surplus is deliberately unable
to dilute the missing flat population.

`D:\edited\macro` contains zero ARWs and contributes zero input stacks.

## Governing text and holdout discipline

The scorecard says that the holdout unit is subject plus uninterrupted capture
session, and permits a holdout to be decoded only to construct a common input
and input-only manifest
(`docs/proposals/2026-09-sota-scorecard.md:345-349`). M3 requires 500 edges,
50 per capture and 400 px reach (`:654-657`). M4 requires 500 sites and 50 per
scored capture (`:699-702`).

M146 correctly left both capture questions undetermined because frame count is
not site count (`docs/research/M146-unlock-audit.md:208-213,295-300`). It also
identified the missing M3 temporal sigma / p99 definitions
(`:180-190,223-226`) and the missing M4 `noise_floor`, population mix and bee
path (`:302-315`).

M152 observed the holdout rule structurally:

- the definition and implementation were committed at `f7dde90a` before a
  protected pixel was decoded;
- `probe` refuses every capture not explicitly registered `NOT_HOLDOUT`;
- the protected `run` requires the exact frozen definition hash;
- each configured evidence class is checked against M141's holdout register;
- the only image decoder accepts `.ARW` files below the two registered input
  roots;
- no command has an output-image argument; and
- the manifest records zero candidate outputs, zero comparator outputs and
  zero stacker runs.

No visual inspection occurred. No holdout output or output-derived statistic
was produced or read.

## Frozen census definition

The normative machine-readable definition is
`experiments/M152-site-census/census-definition.json`. The code consumes that
file rather than accepting threshold overrides.

### Common input representation

For each decoded ARW:

1. copy `raw_image_visible` while the LibRaw context is alive;
2. subtract the decoder's per-channel black levels;
3. average the two Bayer-green samples in each 2x2 CFA cell; and
4. retain coordinates in native-pixel units, with green samples spaced by
   2 native pixels.

This is a decode of a registered input, not a render. Edge discovery uses 17
deterministic, evenly indexed source frames per stack (all frames when a stack
has fewer than 17). The 17-frame census is a lower bound on available edges,
not an estimate inflated to all frames.

### M3 edge rule

For every discovery frame:

1. Gaussian-smooth green luma at sigma 1 green pixel.
2. Take the strongest gradient in each fixed 64x64-native-pixel candidate
   cell, up to 2,048 candidates per frame.
3. Orient its profile dark-to-bright from the input gradient.
4. Require exactly one central 50% crossing, midpoint within 8 px, and bounded
   reverse variation.
5. Require both narrow source plateaus `[-64,-48]` and `[48,64]` and both
   broad plateaus `[-400,-320]` and `[320,400]`.
6. Require each narrow and broad step to be at least
   `10*sigma_temporal`, narrow/broad step agreement within 35%, and robust
   plateau dispersion below the frozen fractions.
7. Greedily de-duplicate in descending input quality at 64 native-pixel
   Euclidean spacing.

The full profile is sampled to +/-400 native pixels before a site can enter
the M3 pool. The selected population takes 50 sites from each capture first,
then round-robins the remaining input-quality order to exactly 500. The final
split is duck 133, chia 133, flower/fern 132, razor 102.

As a post-result robustness diagnostic only, an axis-aligned 800 px frame inset
still leaves 876 sites (151 / 287 / 382 / 56), so the 500/50 result is not
carried by sites sitting barely 400 px from the sensor edge. This diagnostic
did not alter the frozen manifest.

The selector finds isolated, high-CNR step boundaries on the named subjects.
It does not independently certify that every natural edge separates two
physical depth planes. That semantic fact is not available from metadata and
is an explicit limitation of the current M3 population.

### M4 flat and edge rules

Flat candidates are a fixed non-overlapping 128x128-native-pixel grid with a
128 px outer margin. A site survives only if **every input frame** passes all
of:

- its Hann-windowed orthonormal-FFT RMS in `1/60` through `1/20` cycles/native
  pixel is strictly below the independent temporal-noise p99;
- low-rail fraction is at most 1%;
- high-rail fraction is at most 0.1%; and
- median signal is at least ten temporal sigmas above black.

Once no tile survives, later frames are logically irrelevant and the scan
short-circuits. All 146 medication frames and all 299 bee frames were evaluated.
Foam reached zero after two evaluated frames; coffee bubbles after 15.

M4 edge sites use the same input-only edge selector with +/-64 px support.

The proposed scored population is exactly:

- 250 flat sites: medication pill 84, bee background 83, foam 83; and
- 250 edge sites: 50 each from fabric f/5.6, fabric f/8, fabric f/11, duck tape
  and flower/fern.

Equal category weight prevents a large edge population from making flat
failures disappear in the combined rate. Near-equal flat-subject quotas prevent
one easy background from deciding the flat arm. No cross-capture substitution
is allowed after outputs exist.

The compact machine-readable operational freeze is
`experiments/M152-site-census/m4-freeze.json`. It additionally pins the 1,000
Dirichlet(1) draws to NumPy `Generator(PCG64)` seed `15240420260904` and freezes
nearest-rank p99 for `B99`.

**Scorecard defect:** the current text calls medication/bee/foam/coffee flat
sites "for commissioning" but its success bar requires a candidate
`median Q_flat`. A scored flat population therefore does not exist literally.
The 250/250 population above is an operational proposal, not a silent claim
that the current scorecard already says it. M4 cannot produce an official
verdict until the owner adopts a scored flat population.

## Frozen noise definitions

### `sigma_temporal`

For black-subtracted green-luma level `S` in DN:

```text
g_measured = max(ISO,100) / 446.2232509163197
g_shipped  = max(ISO,100) / 436.8
RN_e       = 4.20 below ISO 400, else 1.2392

sigma_temporal(S,ISO)
  = sqrt(g_measured*S + (RN_e*g_shipped)^2) / sqrt(2)
```

The gain/read constants are the independently measured A7C II values already
recorded in `crates/strehl-core/src/profile.rs`; the shipped gain is retained
only in the measured dark-floor product. This is not spatial scene variance.

### Temporal band p99 and `noise_floor`

The control is
`D:\personal\macro\requests\6-11-extended-dark-frames`, explicitly
`CONTROL — NOT HOLDOUT`. M152 used 11 disjoint adjacent pairs at ISO 100 and
11 at ISO 1000, each differenced and divided by `sqrt(2)`.

| ISO | measured band RMS p50 DN | measured band RMS p99 DN | model dark sigma DN | p99/model |
|---:|---:|---:|---:|---:|
| 100 | 0.150717321 | 0.200136937 | 0.679910367 | 0.294357826 |
| 1000 | 0.399349235 | 0.537032849 | 2.006059348 | 0.267705364 |

The frozen conservative factor is their maximum, `0.2943578255886622`.
For a tile with median `S`, its flat-eligibility threshold is that factor times
`sigma_temporal(S,ISO)`.

For M4:

```text
noise_floor(ISO)
  = 0.2943578255886622 * sigma_temporal(0,ISO) / usable_raw_range
```

The measured normalized floors are:

- ISO 50/100: `1.26102285354196e-5`;
- ISO 1000: `3.72061790502189e-5`.

This floor is independent of any candidate output. `B99` remains the
scorecard's 1,000 frozen Dirichlet blends (seed `15240420260904`) plus every
source frame and the uniform mean; the future M4 scorer must use
`max(B99, noise_floor)` exactly.

### Exact bee background

The frozen path is:

```text
D:\personal\macro\bee-1-cpl
```

It is the contiguous registered 299-frame focus-stack capture. The alternative
`requests\12-bee-iso-var-no-bracket-32-repeat-diff-light` changes ISO and light
and contains a continuity break, so it is not a coherent focus-stack input for
this denominator.

## Census results

### M3

| capture | frames | eligible 400 px sites | floor |
|---|---:|---:|---:|
| duck tape | 197 | **221** | 50 |
| chia | 130 | **399** | 50 |
| flower/fern | 299 | **511** | 50 |
| horizontal razor control | 67 | **102** | 50 |
| **total** | 693 | **1,233** | 500 |

**Verdict: sufficient.** No new M3 photon capture is required for the
500/50/400 input requirement.

### M4

| scored flat capture | eligible | frozen quota | shortfall |
|---|---:|---:|---:|
| medication pill | 55 | 84 | **29** |
| bee background | 123 | 83 | 0 |
| foam | 0 | 83 | **83** |
| **total** | **178** | **250** | **112 selected sites** |

| scored edge capture | eligible | frozen quota |
|---|---:|---:|
| fabric f/5.6 | 2,435 | 50 |
| fabric f/8 | 2,284 | 50 |
| fabric f/11 | 2,121 | 50 |
| duck tape | 1,289 | 50 |
| flower/fern | 2,226 | 50 |
| **total** | **10,355** | **250** |

Every rejected flat tile was first rejected by the temporal-band condition,
not clipping or the ten-sigma signal floor.

The commissioning-only census found:

- coffee bubbles: 0 eligible sites;
- burned flat slide, 1 s: 0;
- burned flat slide, 2.5 s: 0; and
- burned flat slide, 6 s: 0.

The latter artifact is
`out/supplemental-commissioning-census.json`, SHA-256
`8d6efde46be8a4314b7880e176bf9db44d2ee9ada947a2089837fedc6a2162e4`.
None may score regardless.

### Exact missing photons

Under the frozen, pre-output population, M4 needs:

1. a fresh untouched medication-pill flat/background session that supplies at
   least 84 qualifying tiles (the existing session supplies 55);
2. a fresh untouched foam flat/background session that supplies at least 83
   qualifying tiles (the existing session supplies zero); and
3. a separate deliberately non-holdout development flat session supplying at
   least 100 qualifying tiles for commissioning, because coffee bubbles and
   all existing burned flat-slide stacks supply zero.

The captures should reserve broad truly featureless background, keep each
128x128 tile above the ten-sigma black floor and below clipping, and avoid
20–60 px texture in every focus frame. The score and development sessions must
be separate: commissioning on a protected replacement would burn it.

If the owner replaces the near-equal flat-subject quotas with only the
scorecard's stated 50-per-capture minimum, the old medication capture already
clears 50 and one new protected flat session with at least 72 sites could close
the 250-flat total. That would be a new population version chosen openly; M152
does not rewrite its frozen quotas after seeing the result.

## M3 checker and commissioning

The checker definition is
`experiments/M152-site-census/m3-checker-definition.json`, SHA-256
`882440eb073caba2c285f42b2baac0e92d49ad254d90d61a1e67eb188efc2221`.
It pins the census-manifest hash and uses:

- nearest-rank empirical percentiles, one-based rank `ceil(q*N)`, no
  interpolation;
- one-sided Wilson UCB95, `z=1.6448536269514722`;
- no output-driven site deletion (missing/non-finite output is `+infinity`);
- `a_e=max(h_e,v_e)` for the comparator summary; the best comparator is the
  one with the lowest pooled nearest-rank p99 on the identical frozen sites,
  and Strehl's pooled p99 is compared to it.

The low-level scorer accepts externally warped source profiles plus frozen
normalization, far-reference and sharp-source indices. It does not select
sites from an output.

Commissioning artifact:
`out/m3-commission.json`, SHA-256
`cd997c28a6e0532c48858350f0f3c0c0434285ede91413ce43952a6880b36ad6`.

| arm | median `h_e` | p99 `h_e` | median `v_e` | p99 `v_e` | affected rate |
|---|---:|---:|---:|---:|---:|
| synthetic healthy null | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0% |
| 6% rim | 0.059943 | 0.059999 | 0.002919 | 0.002919 | 100% |
| 6% opposite-sign rim | 0.059943 | 0.059999 | 0.002919 | 0.002919 | 100% |
| 6% two-sided 200 px veil | 0.059972 | 0.059999 | 0.060000 | 0.060000 | 100% |
| 6% one-sided far 200 px veil | **0.000000** | **0.000000** | **0.027243** | **0.027243** | **0%** |
| 6% rim plus veil | 0.119885 | 0.119998 | 0.060000 | 0.060000 | 100% |
| improved to 0.5% rim plus veil | 0.009885 | 0.009998 | 0.005000 | 0.005000 | 0% |
| blur guard | 0.136315 | 0.166072 | 0.000077 | 0.000130 | 100% |

The blur arm also moved median width ratio to `1.771028` and median
`rho_edge` to `0.036907`, so those guards can fail.

The untouched horizontal-razor RAW identity null used 50 registered control
sites and measured median/p99 `h_e=0/0`, median/p99 `v_e=0/0`, false-positive
rate `0%`. This is a real decoder/coordinate/interpolation null, but it is
tautological as an artifact null because the same untouched profile is present
in its source interval and serves as its far reference. It does not commission
external warp error. The synthetic null independently proves numerical
quietness but not real registration robustness.

The improvement arm moves median `h_e` `0.119885 -> 0.009885` and median `v_e`
`0.060000 -> 0.005000`. The statistic therefore responds in both directions;
it is not merely a non-negative defect readout that can only stay fixed.

### Commissioning failure: the registered broad veil is not admissible

The one-sided plant occupies offsets `+33` through `+232`, exactly 200 native
pixels. It begins outside `h_e`'s last sample at 32 px. The registered `v_e`
averages both sides, so the unaffected side dilutes the measured 6% veil to
`0.027243`; no site crosses the 5% affected threshold. A population affecting
fewer than half but more than 1% of sites can therefore pass median, p99 and
affected-rate absolute gates simultaneously: its p99 remains 0.027243 and its
affected count remains zero.

The non-normative side-max diagnostic,
`max(v_e_negative_side,v_e_positive_side)`, detects 100% of those sites and
reads approximately 0.0545. That is the smallest repair demonstrated here.
M152 does **not** silently substitute it for the scorecard's literal mean.

The commissioning command consequently writes its artifact and exits 3 with:

```text
NOT_ADMITTED_COMMISSIONING_FAILED
failed: one_sided_far_veil_detected_at_least_95pct
```

This is the M3 counterpart of M145's sparse-seam lesson: a pooled reduction can
be numerically correct and still fail to charge the spatial failure it names.

## Can the bars bite?

### M3

**Partly, but not enough to admit the current bar.** The input capture is
sufficient. The checker strongly charges both rim signs, a two-sided veil and
blur, stays quiet on its identity null, and scores a planted improvement lower.
But the literal broad-veil reduction fails its own required one-sided 200 px
plant. Until the scorecard adopts a per-side maximum (or another commissioned
local guard), M3 is unfalsifiable for a substantial class of sparse one-sided
far-field veils. The checker is correctly red, not shipped green.

M3 also cannot yet produce a registered product score: no common-input
candidate/comparator outputs or external source-profile warps were supplied,
and the scorecard still carries the separate future-M1 dependency.

### M4

**No, not today.** The input-only edge detector has abundant power, but the
frozen flat population is underfilled, the real commissioning flat population
is empty, and the scorecard does not currently say which flat inputs are
scored. A future M4 scorer was outside this lane's priority order and was not
built after the census returned `NEEDS_NEW_CAPTURE`.

## Read-only verification

Before and after the protected census:

| root | files | bytes | path/size/mtime hash |
|---|---:|---:|---|
| `D:\personal\macro` | 10,724 | 487,169,829,957 | equal |
| `D:\edited\macro` | 387 | 141,333,902,406 | equal |

`out/readonly-verification.json` records `all_trees_unchanged: true`. The
supplemental burned-input census repeated the same guard.

## Reproduction

From `projects\strehl`:

```powershell
python experiments\M152-site-census\test_census.py
python experiments\M152-site-census\census.py definition-hash
python experiments\M152-site-census\census.py calibrate-noise
python experiments\M152-site-census\census.py run --confirm-definition-sha256 b2e872a6a8214d4fbe379287f52fc57b8f5e61f292aab4c30e96b11d49325879
python experiments\M152-site-census\census_commissioning.py
python experiments\M152-site-census\test_m3_checker.py
python experiments\M152-site-census\commission_m3.py
python experiments\M152-site-census\verify_artifacts.py
```

`commission_m3.py` is expected to exit 3 after writing the reproducible red
artifact. Treating that exit as success would erase the main finding.

## What remains undetermined

1. I could not commission real external-warp robustness because no registered
   common-input warp/profile package exists. The untouched-RAW identity null
   does not answer that question.
2. I could not run paired comparator p99 because no common-input comparator
   outputs were opened or supplied; doing so on holdout before the score run
   would violate the holdout rule.
3. I could not make M4 executable without changing its scorecard population
   and acquiring qualified flat inputs. `B99` and `Q_flat` were therefore
   specified but not scored.
4. The input-only selector establishes isolated step geometry, not independent
   physical depth labels for every natural-scene edge.
5. `rho_edge` assumes a future scorer supplies one sample per native pixel in
   each 128x128 patch; this lane did not build the common-output adapter.
