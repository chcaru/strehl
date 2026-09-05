# M152 — shared input-only M3/M4 site census

**Status:** census frozen and run; M3 capture is sufficient; M4 needs new
capture. The historical pooled-mean M3 checker correctly failed commissioning;
the amended side-max reduction now passes its full supplemental battery and
empirical clean-noise controls. The M3 axis remains
`UNMEASURED_COMPARATOR_QUALIFICATION`, not scored.

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
| **total** | **178** | **250** | **112-site shortfall** |

| scored edge capture | eligible | frozen quota |
|---|---:|---:|
| fabric f/5.6 | 2,435 | 50 |
| fabric f/8 | 2,284 | 50 |
| fabric f/11 | 2,121 | 50 |
| duck tape | 1,289 | 50 |
| flower/fern | 2,226 | 50 |
| **total** | **10,355** | **250** |

The frozen `first_failure_counts` assigned every rejected flat tile to the
temporal-band condition because it was the first true predicate in a fixed
priority order. That additive attribution does not establish that the other
predicates passed; see the explicit erratum below.

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

## M4 independent-predicate diagnostic, erratum and capture feasibility

### Independent-predicate diagnostic

**Status: MEASURED INPUT-ONLY.** The frozen flat census forms the conjunction
of all four predicates at `experiments/M152-site-census/census.py:645-673`,
removes a site permanently at `:693`, and assigns each rejected site exactly
once in the fixed band, low-rail, high-rail, signal order at `:675-691`.
Consequently, `first_failure_counts` is an additive first-cause diagnostic; it
is not the independent incidence of every true predicate.

The independent diagnostic retained the original 1,768-site denominator and,
instead of pruning it, accumulated for every tile:

```text
band_ratio = max_over_frames(band_rms / temporal_band_threshold)
signal_sigma = min_over_frames(tile_median / sigma_temporal(tile_median, ISO))
low_rail = max_over_frames(fraction(tile <= 0))
high_rail = max_over_frames(fraction(tile >= usable_range - 1))
```

It reused the frozen decoder at
`experiments/M152-site-census/census_common.py:115-178`, temporal model at
`:180-198`, band RMS at `:225-244`, grid extraction at `:247-259`, and
nearest-rank percentiles at `:51-60`. The thresholds remain ratio `<1.0`,
signal `>=10 sigma`, low rail `<=0.01`, and high rail `<=0.001`, frozen at
`experiments/M152-site-census/census-definition.json:205-214`. The driver was
a one-off read-only PowerShell standard-input script; the persisted kernels
and complete reduction contract above are its reproducible provenance. It
opened no candidate output and changed no frozen selection.

| capture and evaluated frames | independent band failures; max-ratio min / median / p95 / max | independent signal failures; minimum signal | independent low-rail failures; max | independent high-rail failures; max | joint eligible |
|---|---|---|---|---|---:|
| coffee bubbles, 19/19 | 1,768/1,768; **1.091006 / 5.279854 / 211.877004 / 680.844818** | 0; **11.665702 sigma** | 0; 0 | **176; 0.133789** | **0** |
| foam, decisive frames 1-2/100 | 1,768/1,768; **1.358369 / 4.123867 / 8.467059 / 22.160248** | 0; **17.417903 sigma** | 0; 0 | 0; 0 | **0** |

Coffee therefore fails principally because the scene is not flat in the
20-60 px band, not because it is underexposed. It also has localized clipping.
Even a favorable fixed-noise scalar-exposure counterfactual leaves only eight
coffee tiles with any band-plus-signal-feasible exposure interval, far below
the 100-site development quota. A different target is required.

### ERRATUM: priority masking in the frozen counters

**The frozen census remains usable as published for eligibility, selection,
quotas and the capture-sufficiency verdict.** The validity decision used the
full conjunction before pruning, so priority affects only diagnostic
attribution. The `178` eligible, `138` selected and `112` shortfall figures do
not change.

The published inference that first assignment to band power meant "not
clipping" is withdrawn. The frozen `first_failure_counts` values remain
numerically correct only as priority-assigned first causes and must not be
used as independent predicate counts. In particular, the previously implied
independent coffee high-rail count of zero was wrong: the corrected value is
**176/1,768**, with a maximum fraction of **0.133789** against the **0.001**
limit. Every one of those tiles had already failed band power, so coffee's
eligible count remains zero. Foam's independently evaluated first two frames
have zero signal or rail failures. Medication and bee were not rerun with the
independent diagnostic, so this erratum makes no independent rail-incidence
claim for them.

### Frames do not generate sites

Each frame repeats the same 1,768 spatial candidates, and a site must pass
every frame. The survivor update at
`experiments/M152-site-census/census.py:607-706` is therefore monotone
non-increasing: more exposures can preserve or remove sites, never create
them.

| capture | registered frames | eligible / 1,768 | observed spatial yield | required / 1,768 |
|---|---:|---:|---:|---:|
| medication pill | 146 | 55 | **3.11%** | 84 = **4.75%** |
| bee background | 299 | 123 | **6.96%** | 83 = **4.69%** |
| foam | 100 | 0 | 0% | 83 = **4.69%** |
| development flat | 19 | 0 | 0% | 100 = **5.66%** |

These are scene yields, not sites per frame. No number of additional
exposures of an unchanged field can close the medication, foam or development
deficit.

### Foam plausibility under a favorable fixed-noise model

For an intentionally favorable diagnostic, multiply each black-subtracted
foam tile by one common scalar `k` while holding the frozen temporal noise
fixed. Each tile then requires
`10/signal_sigma <= k < 1/band_ratio`. Over the first two decisive frames, the
maximum common-exposure survivor count is **113** at approximately
**`k=0.416` (`-1.265 EV`)**. At least 83 sites survive for
**`0.374 <= k < 0.486`**.

This is **plausibility under a favorable fixed-noise model, not sufficiency**.
A physical reshoot changes shot noise, and the remaining 98 frames can only
reduce the every-frame survivor count. The existing foam stack cannot be
repaired by adding frames, but smoother foam at a preregistered lower exposure
is plausible rather than proven sufficient.

### Capture recipe

- Use a genuinely featureless transilluminated opal diffuser for development,
  medication on the same uniform background, and smoother closed-cell foam or
  an openly replaced subject.
- Use flicker-free diffuse illumination, 200 mm, f/5.6 and ISO 50/100. Keep
  every selected common-TIFF RGB pixel at least 512 codes from either rail for
  M166's integer plant, and keep median signal above `10 sigma`.
- If retaining the original f/8, ISO-1000 foam setup, use approximately
  **0.67-0.83 s** as the preregistered starting range instead of 1.6-2 s. This
  is the `0.416x` plausibility result, not a guarantee.
- Commission only on a separate development session; do not inspect a
  protected score session to tune these conditions.

### Open definitional questions

1. M166's "at least 29 additional eligible medication flat tiles"
   (`docs/research/M166-bar-definition-repairs.md:582`) conflicts with its
   fixed 84-site medication quota and "no cross-capture substitution"
   (`:194-199`). A replacement session must supply all **84** unless the owner
   explicitly permits supplementation.
2. M166 defines a `1000 by N_frames` Dirichlet matrix (`:212-219`) but no
   minimum `N_frames`. The conservative **146 medication + 100 foam + 100
   development = 346 frames** budget is therefore **preregistration-owed, not
   derived**. Frame count must be frozen as an acquisition rule before
   shooting; it does not follow from the spatial quotas.

### Scorability

The retained M166 `Q/g/r` component is scoreable and can mathematically pass
without blocker `(a)` and without Zerene. Its constructive convex-source
implementation has `Q<=1`, `g=1`, and `r=0`
(`docs/research/M166-bar-definition-repairs.md:190-305`). Actual Strehl
performance remains unmeasured.

Full M4 remains blocked `(a)(b)(d)` by its detail-qualified common track,
ghost/M3-boundary population and required best-comparator comparison
(`docs/proposals/2026-09-sota-scorecard.md:809,843`). Satisfying these capture
needs would **not** produce an M4-axis PASS.

### Versioned successor manifest

A versioned successor can be prepared before capture in **6-10 engineering
hours** by retaining M152's input-only order and adding M166's exact
common-TIFF RGB plant-headroom predicate, capture/session schema, frame-count
rule, tests and hashes. Once captures arrive, allow **2-4 hours plus render
time** to run the census, bind the selected sites, and materialize the
Dirichlet matrices and plants, then produce the base/planted renders.

## Historical M3 checker and commissioning

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

### Historical commissioning failure: the pooled broad veil was not admissible

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

## Side-max amendment and recommissioning

Scorecard amendment `4b79b6dc` replaced the pooled two-side mean with
`v_e=max(v_e_neg,v_e_pos)`. The current scorecard later adopted M161's
versioned scorer, which also separates broad and narrow source-step
normalization. M152's v1 checker, definition, and red artifact remain unchanged
as historical evidence. The supplemental definition is
`side-max-commission-definition.json`; it pins the canonical M161 scorer and
all local and historical dependencies.

The primary clean-noise arm uses the exact 500 frozen site IDs and their frozen
`step_broad_dn` and `sigma_temporal_dn`, but opens no protected site pixels.
It replays eleven adjacent-pair differences from the non-holdout ISO-100 dark
session as empirical sensor-noise traces, scales them to each frozen site's
already-registered temporal sigma, and forms a defect-free mean profile. The
far reference is one member of that mean, preserving production-like
covariance. A disjoint-reference arm is the conservative covariance stress;
ISO-1000 repeats both roles as a pre-registered noise-tail morphology stress.
Trace allocation is fixed before decode and never filters on a measured value.

Artifact: `out/m3-side-max-commission-v2.json`, SHA-256
`0df4593573b85cc611005ac112f80c6c9a47949f130ddfd377129db2dff937c4`.

| clean-noise arm | legacy median / p99 | side-max median / p99 | inflation median / p95 / max | affected | Wilson UCB95 |
|---|---:|---:|---:|---:|---:|
| ISO-100 production covariance, **primary** | 0.003405 / 0.011209 | **0.003547 / 0.011920** | **1.0409 / 1.1290 / 1.2023** | 0/500 | 0.005382 |
| ISO-100 disjoint reference | 0.003745 / 0.012330 | 0.003902 / 0.013111 | 1.0409 / 1.1290 / 1.2023 | 0/500 | 0.005382 |
| ISO-1000 production covariance | 0.003032 / 0.010203 | 0.003294 / 0.010476 | 1.0515 / 1.1526 / 1.2589 | 0/500 | 0.005382 |
| ISO-1000 disjoint reference | 0.003335 / 0.011224 | 0.003623 / 0.011524 | 1.0515 / 1.1526 / 1.2589 | 0/500 | 0.005382 |

All four populations had 500/500 sites with unequal side means and both
dominance directions represented. Their maximum amended `v_e` values were
0.015246, 0.016771, 0.014019, and 0.015421. There were zero new-only 5%
threshold crossings. The primary arm therefore clears the unchanged median
0.01, p99 0.05, point-rate 1%, and Wilson-UCB 2% bars with substantial margin.
**No threshold adjustment is indicated.**

The identity arm remains exactly legacy/amended median `0/0`, p99 `0/0`, and
affected `0/50`; it is retained only as a wiring check. Unlike that frozen
probe, every empirical arm is nonzero and exercises side asymmetry.

### Full amended battery

| arm | median `h_e` | legacy median `v_e` | side-max median `v_e` | affected |
|---|---:|---:|---:|---:|
| synthetic identity wiring null | 0.000000 | 0.000000 | 0.000000 | 0/500 |
| 6% rim | 0.059943 | 0.002919 | 0.002919 | 500/500 |
| 6% opposite-sign rim | 0.059943 | 0.002919 | 0.002919 | 500/500 |
| 6% two-sided veil | 0.059972 | 0.060000 | 0.060000 | 500/500 |
| 6% one-sided `+33..+232` veil | 0.000000 | **0.027243** | **0.054486** | **500/500** |
| 6% rim plus veil | 0.119885 | 0.060000 | 0.062919 | 500/500 |
| 0.5% rim plus veil improvement | 0.009885 | 0.005000 | 0.005243 | 0/500 |
| blur guard | 0.136315 | 0.000077 | 0.000077 | 500/500 |

The one-sided plant's amended/legacy ratio was exactly `2.000000000000` at
all 500 sites, matching the analytic limit. The improvement arm remains below
the bar and lower than the 6% paired defect. Separate accounting is:

- checks run/passed: **15/15**;
- mutation arms planted/killed: **6/6**, 3,000/3,000 mutated sites charged;
- inert controls run/survived: **6/6**;
- improvement controls preserved: **1/1**; and
- arms regressed: **0**.

The first frozen supplemental run is preserved separately at
`out/m3-side-max-commission.json`, SHA-256
`52fb035d98cd4463a4431fc7abf49b08a99e373f08238a3ecb6291f9eb0974a6`.
It returned red because the new helper accidentally omitted the
already-pinned M152 patch texture, leaving the coherence band nearly empty;
only the improvement arm's `rho_edge` check failed. Commit `5d6df895` restored
the historical fixture exactly before the v2 rerun. No metric, plant,
threshold, or empirical-noise rule changed, and the empirical values reproduced
exactly.

This is a reduction-level commission, not an M3 product result. The empirical
amplitude is conditioned on M152's frozen temporal-noise model, so it cannot
validate that calibration. Dark differences also do not represent ProPhoto
output conversion, registration residual, or scene-dependent render error.
Only eleven temporal pair clusters feed 500 spatial traces, so the reported
Wilson value is the scorecard-shaped mechanical count, not a claim of 500
independent noise captures.

## Can the bars bite?

### M3

**The amended reduction can bite and remains passable on the commissioned
clean-noise surrogate.** It charges both rim signs, two-sided and one-sided
veils, and blur; the one-sided case is no longer diluted. The empirical tail
does not threaten the unchanged bars.

M3 still cannot produce a registered product score: no common-input
candidate/comparator outputs or external source-profile warps were supplied,
and the scorecard still requires an M1-qualified comparator envelope. Its axis
verdict is `UNMEASURED_COMPARATOR_QUALIFICATION`, not PASS or FAIL.

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
python experiments\M152-site-census\test_m3_side_max_commission.py
python experiments\M152-site-census\commission_m3_side_max.py
python experiments\M152-site-census\verify_artifacts.py
```

`commission_m3.py` is historical and expected to exit 3 after writing the
pooled-mean red artifact. `commission_m3_side_max.py` is expected to exit 0
and reproduce the versioned side-max result.

## What remains undetermined

1. I could not commission real external-warp robustness because no registered
   common-input warp/profile package exists. The untouched-RAW identity null
   and empirical-noise surrogate do not answer that question.
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
