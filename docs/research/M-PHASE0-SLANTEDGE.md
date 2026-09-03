# M-PHASE0-SLANTEDGE — audit of the slanted-edge detail instrument

**Status: complete. Verdict: NO COMMISSIONED SLANTED-EDGE RESOLUTION
INSTRUMENT.**

<!-- claim:verdict -->
The implementations exist, and all three recover a known Gaussian blur
quantitatively.  All three nevertheless report an information-free unsharp
mask as **9.24–9.87% more resolution**, with no warning or refusal.  They are
therefore not fit to be the sole basis of a resolution claim.

This independently confirms the correction already present in
`docs/proposals/2026-09-sota-scorecard.md` sections 4 and 5: MTF50 and SFR are
`SHARPENING-UNSAFE` presentation diagnostics and cannot determine M1.  The
older D1 wording in `docs/proposals/2026-08-sota-path.md` is not a usable
two-instrument prescription: split/repeat FRC is unavailable, and slanted-edge
SFR is not a sharpening-safe substitute.  The detail axis currently has no
admissible implemented instrument.

## What exists

The commissioned search covered `experiments/`, `docs/research/`, `crates/`
and `scripts/` for slant/slanted-edge, SFR, MTF, MTF50, ESF, LSF and
edge-spread.

| implementation | finding |
|---|---|
| `experiments/M88-optical-ceiling/src/m88lib.py` | Canonical, full ISO-12233-style RAW SFR: edge fit, projected ESF, LSF, corrected MTF and optical-cutoff fitting. Its own report says every one of 22 real ROI/plane results failed the validity gate, so its real cutoff is `UNIDENTIFIED`. |
| `experiments/M104c-mtf/mtf.py` | Independent compact slanted-edge MTF50 reimplementation. Synthetic blur/null passed historically; `mtf_real.py`/`mtf_slant.py` found no trustworthy real edge and read a rendered TIFF green channel. |
| `experiments/BUILD-RESAMP/slanted_edge.py` | Full rendered-raster MTF50/SFR with automatic discovery, fixed-site comparison and a 2–10 degree gate. Its committed commissioning failed sigma-1 blur, scale and noise arms; the report says the corpus has no ISO-valid target. |
| `experiments/M88b-merge-sharpness/src/m88blib.py` | Adapter around M88 for paired 10–90 ESF rise, not an independent SFR implementation. |
| `experiments/M128-razor-ladder/src/sfr_run.py` | Adapter around M88 with a replacement locator. `out/controls.json` ends 5 PASS / 5 FAIL and stops before real measurement. Its true-sharper-edge control is useful but is not a post-render sharpening challenge. |
| `experiments/BUILD-SHARP/src/esf.py` and other ESF helpers | Edge-width/shape diagnostics, not slanted-edge SFR/MTF50. |
| `crates/strehl-core/src/restore.rs`, `crates/strehl-cli/examples/build-resamp-mtf.rs`, other MTF hits | Analytic/kernel MTF models or synthetic diagnostics, not an image slanted-edge instrument. |
| `scripts/` | No matching implementation. |

Generated `M-PHASE0-PIPE/out/source-*` and
`SCORECARD-BASELINE/work/source/*` trees are snapshots, not additional
implementations.

## Independent commissioning

The preregistration and executable audit are in
`experiments/M-PHASE0-SLANTEDGE/`.  `measure.py` generates plants without
calling any candidate's synthetic helper.  `commission.py` runs measurement
as a child process, imports neither generator nor candidate, and checks only
serialized values against literal analytic predicates.

The checker first passed an all-GREEN literal fixture and caught **8/8**
single-property sabotages: identity, blur, true improvement, sharpening, tone,
noise, angle and licensing.

All frequencies below are cycles/native-pixel.

| candidate | base (truth .124927) | +sigma .75 blur (truth .111738) | blur ratio (truth .894427) | true sharper ratio (truth 1.25) | USM ratio |
|---|---:|---:|---:|---:|---:|
| M88 SFR→MTF50 | .125126 | .112002 | .895115 | 1.248631 | **1.098673 RED** |
| M104c | .124786 | .111667 | .894870 | 1.248849 | **1.098679 RED** |
| BUILD-RESAMP | .127374 | .114637 | .900002 | 1.238651 | **1.092354 RED** |

The base is a sigma-1.50 neutral Gaussian edge at 5 degrees.  The defect arm
adds known sigma-0.75 blur.  The genuine improvement arm independently samples
sigma 1.20.  Both quantitative arms pass the frozen 5% bar in every
implementation.  The decisive arm applies unclipped float USM, radius 1.0,
amount 0.5, after rendering.  It adds no independent scene information, yet
every implementation scores it as improved resolution.

The untuned identity null is bit-exact in all three.  Thus this is not a
constant-zero or wrong-sign metric: it responds correctly to real blur and
real improvement and still fails the sharpening defeat.

## Defeat audit

| defeat | M88 | M104c | BUILD-RESAMP |
|---|---|---|---|
| **Sharpening** | **VULNERABLE**, +9.87%, no detector | **VULNERABLE**, +9.87%, no detector | **VULNERABLE**, +9.24%, no detector |
| **Tone** | **VULNERABLE estimator**; canonical RAW input protects deployment from developed tone | **VULNERABLE** rendered path | **VULNERABLE** rendered path |
| **Noise** | **VULNERABLE MTF50**; E2's separate noise-floor bound is protected but is not a cutoff | **VULNERABLE/unstable** | **VULNERABLE** |
| **Angle/selection** | **VULNERABLE gate**, selection otherwise geometric/frozen | **VULNERABLE/partial** | angle **PROTECTED**, straightness **VULNERABLE** |
| **0.25 licence** | **VULNERABLE** | **VULNERABLE** | **VULNERABLE** |
| **Demosaic/colour** | **PROTECTED**: direct linear RAW G1/G2 | **VULNERABLE**: rendered RGB green | **VULNERABLE**: rendered RGB green |

### Tone

Affine gain/pedestal moved every MTF50 by numerical zero, as expected from DC
normalisation.  That is not monotone-tone invariance.  Gamma 3 raised MTF50 by
**17.41–17.67%** and a strictly increasing logistic curve raised it by
**49.30–50.71%**.  No path detected or refused either transform.  This is the
same class of failure as the retracted tone-based detail result; unlike
V-HEADTOHEAD3's ordinal statistic, these paths are not invariant to monotone
point transforms.

### Noise

The plant adds Gaussian sd 0.02 to a 0.60-contrast edge over 24 fixed seeds.
M88 scored 13/24 noisier arms above base, up to **+55.91%**. BUILD-RESAMP
scored 14/24 above base, up to **+15.78%**. M104c scored none above base but
collapsed to **0.202–0.282x** base, so it also fails noise separation rather
than providing a stable resolution estimate.  The three frozen noise bars are
RED.

### Edge angle and selection

M88 measures angle and selects geometrically before frequency analysis, which
protects against selecting on the answer.  Its finder nevertheless admits
**0.4–12 degrees**; the 0.5-, 1- and 12-degree plants were numerically
measurable and would pass that gate.  M104c's callers gate 2–12 degrees but
lack clipping, straightness and single-transition gates.  BUILD-RESAMP alone
passed the frozen 2–10 degree challenge and pins sites across arms, but its
declared `MAX_RESID_PX` is unused and `edge_fit` reports residual 0.0.

### Licensing and colour path

A sigma-0.60 edge has true MTF50 0.312318, above the repository's licensed
0.25 endpoint.  M88, M104c and BUILD-RESAMP emitted the numeric values
**0.312262, 0.309089 and 0.310031**, respectively.  None emitted
`UNLICENSED_GT_0.25`.

M88 is the only path protected from demosaic/development: it reads one linear
RAW green sublattice in sensor coordinates, with no white balance, colour
matrix, sharpening or resampling.  M104c and BUILD-RESAMP read the green
channel of rendered RGB/TIFF output, where demosaic/output processing can
determine apparent edge sharpness.

## Scope and reproduction

No capture, holdout, reserve or Rust source was opened or changed.  Synthetic
commissioning used Python 3.12.10, NumPy 2.4.4 and SciPy 1.17.1 with one
thread.  It cannot determine how a new, correctly tilted physical chart would
behave, nor does it commission M1's currently blocked independent-repeat
instrument.

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M-PHASE0-SLANTEDGE\commission.py
python scripts\corpus_lint.py --root .
```

## Survivor follow-up: M1 and ordinal Q25

**Status: complete. Verdict: NO SURVIVOR IS ADMITTED BY THE FULL FROZEN
BATTERY.**  This follow-up does not revive slanted-edge MTF50.  It asks whether
SCORECARD-BASELINE M1 and V-HEADTOHEAD3's ordinal statistic resist USM while
still responding to physical blur and improvement.

The outcome-independent registration is
`experiments/M-PHASE0-SLANTEDGE/SURVIVOR-PREREGISTRATION.md`.  Relevant
candidate functions were copied verbatim into the owned tree.  A separate
process checked the three full source hashes and 11 function ASTs before each
run; the adapter imported only the copies.  The checker imported neither
plants nor candidates, passed a literal all-GREEN fixture, and caught **10/10**
single-property sabotages, including source drift and MTF50 relabelling.  Two
complete child-process runs were bit-for-bit deterministic.

Neither candidate reports MTF50, so native outputs are not renamed.  The
absolute Gaussian MTF50 anchors are unsupported.  Ratios below are nevertheless
judged against the unchanged frozen bars: blur `0.894427 +/-5%`, improvement
`1.25 +/-5%`, USM `<=1.01`, tone movement `<=1%`, and noise median/worst
movement `<=3%/5%`.

### SCORECARD-BASELINE M1

The adapter supplied 24 independent noisy A/B/reference triplets.  Physical
blur/improvement changed A/B before noise; post-render USM filtered complete
noisy A/B renders; the independent reference remained fixed.

| native field | base | identity | blur | improvement | USM |
|---|---:|---:|---:|---:|---:|
| `f_licensed` | .150000 | 1.000000x | 1.000000x **RED** | 1.000000x **RED** | 1.000000x GREEN |
| `S_25` | 6.68974e-5 | 1.000000x | .226526x **RED** | 8.274764x **RED** | .995819x GREEN |
| `gain_median` guard | .109115 | 1.000000x | .670214x | 1.919579x | 1.271414x |

The claim-bearing cutoff sits at its 0.15 floor for base, blur, real
improvement and USM: on this frozen fixture it is
`USM_INVARIANT_BUT_BLIND`.  The second claim-bearing output is not blind:
`S_25` moves strongly in the correct directions under both physical arms while
USM changes it by only -0.418%.  It is not quantitatively calibrated to MTF50,
however, and fails the unchanged ratio bars.  The sharpening-unsafe
`gain_median` guard correctly remains presentation-sensitive and is not used
as resolution evidence.

Affine tone is numerically invariant in both claim fields.  Gamma-3/logistic
move `S_25` by **4.8400x/18818.9045x**; logistic also moves `f_licensed` from
.15 to .25.  The extra-noise `S_25` median is `.330086x`, range
`.004972x-10.381863x`; thus some noisier arms score much better.  Native score
ratios at 0.5/1/5/12 degrees are `1/1/1/1` for the floored cutoff and
`1.42205/1.18548/1/0.65802` for `S_25`; M1 emits no edge-angle/refusal output.
The sigma-.60 arm returns `.17` and `.008855`, respectively.  M1 reads only
`[.15,.25)` and caps the cutoff, so frequency licensing is structurally
protected, although the frozen exact-sentinel interface is unsupported.

**M1 disposition: NOT COMMISSIONED BY THIS HARNESS.**  It demonstrates a
useful sharpening-safe, bidirectional `S_25` response, but its resolution
cutoff is blind on the plant and the composite fails tone, noise, angle,
absolute-calibration and exact-sentinel bars.  This synthetic adapter cannot
adjudicate formal scorecard M1: it lacks the registered tile-eligibility
denominator and dark/flat noise floor.

### V-HEADTOHEAD3 licensed ordinal Q25

| native field | base | identity | blur | improvement | USM |
|---|---:|---:|---:|---:|---:|
| licensed `Q25` | 9.52160e-4 | 1.000000x | .841501x **RED** | .977981x **RED/wrong sign** | **5.560744x RED** |
| historical `A20_25` | .0310560 | 1.000000x | .796069x | 1.097075x | .591780x |

The decisive candidate, licensed Q25, reports the information-free USM as
**+456.07% improved** while a genuine sigma-1.20 improvement reads **-2.20%**.
It is therefore neither sharpening-safe nor a calibrated resolution
instrument on this plant.  Affine/gamma/logistic ratios are
`.999963/1/.999966`, passing the tone bar.  Noise ratios are
`15.9320-18.3498x` (median `17.0056x`).  The 0.5/1/5/12-degree ratios are
`.961215/.966181/1/1.064245`; there is no angle gate.

Q25's numerator is structurally restricted to `[.20,.25)` and its denominator
is spatial rank variance, so it does not import an above-cap spectral result;
the exact sentinel interface remains unsupported.  The historical statistic
cannot rescue the result: its six-band denominator reaches 0.40 and is
unlicensed, and it also misses both physical ratio bars and the noise bar.

**Q25 disposition: REFUSED.**  It passes point-tone invariance but fails the
decisive sharpening and genuine-improvement controls.  No real capture,
holdout, reserve, Rust source, SCORECARD-BASELINE path or V-HEADTOHEAD3 path
was modified.

## S25 hardening build

**Status: complete. Verdict: NO ADMISSIBLE S25 VARIANT.**  Six
outcome-independent variants were frozen before measurement.  None combines
tone invariance, sharpening safety, quantitatively correct bidirectional
optical response, noise robustness and the angle contract.  This finite search
does not prove the trade-off fundamental.

The preregistration is
`experiments/M-PHASE0-SLANTEDGE/S25-HARDENING-PREREGISTRATION.md`.
`s25h_fixtures.py` owns plants, `s25h_variants.py` owns candidates, and
`s25h_commission.py` imports neither: it invokes measurement and source
provenance as child processes and checks literal predicates.  Relevant commits
are `f78e8288` (freeze), `ee2b0a3c` (implementation), `c90e13d4`/`da0efcb2`
(pre-outcome warning repair), and `aa540580`/`80a56369` (retain every
disqualified diagnostic).  Independent verification then found three
specification mismatches; `2b377e21` froze their correction before
`9fbc9b21` repaired calibration stream construction, licensed-bin activation,
strict non-positive-D refusal and the executed zero-floor mutant.

The first implementation run stopped before adjudication because NumPy warned
while interpolating non-finite flat-bootstrap sentinels.  The registered repair
uses the exact lower 5% order statistic.  The next valid run found the main
edge ineligible and therefore exposed no V1–V5 score.  A second registered
repair retained latent diagnostics while keeping every public status
`REFUSED`; diagnostics can never pass a gate.

### Full frozen matrix

All entries are arm/base ratios.  Identity is exactly `1.000000` for every
variant.  Daggers are diagnostics behind the already-failed source-eligibility
gate, not admissible measurements.  Noise is `median [min,max]`; the frozen
worst-case 5% bar is applied to every one of 24 retained readings.
Native/diagnostic base values are `9.56626e-5, 8.45709e-5, .472695, .472695,
.472695, .481947` in row order.

| variant | blur | improvement | USM | affine / gamma-3 / logistic | noise | disposition |
|---|---:|---:|---:|---:|---:|---|
| `C0_NATIVE_MIN` | .293334 | 2.297574 | **1.028294 RED** | 1 / 1.215825 / 12352.494864 | .405570 [.215095,.980975] | RED: every target property except affine/identity |
| `V1_FLOOR_ELIG_MIN`† | .301519 | 2.414290 | **1.163158 RED** | 1.131153 / 1.375283 / 3424.239914 | .458762 [.243305,1.109633] | REFUSED; floor/min does not harden S25 |
| `V2_GES_OLS`† | **1.268326 wrong sign** | **.923468 wrong sign** | 1.000425 | 1.000349 / 1.216039 / 1.792007 | 1.161719 [1.062812,1.277234] | REFUSED; shape conversion reverses optics |
| `V3_RAMP_GES_OLS`† | **1.268326 wrong sign** | **.923468 wrong sign** | 1.000425 | 1 / .999859 / .999896 | 1.161719 [1.062812,1.277234] | REFUSED; tone fixed, optics/noise fail |
| `V4_RAMP_GES_OLS_ANGLE`† | **1.268326 wrong sign** | **.923468 wrong sign** | 1.000425 | 1 / .999859 / .999896 | 1.161719 [1.062812,1.277234] | REFUSED; same plus angle gate |
| `V5_RAMP_GES_TS_ANGLE`† | **1.236317 wrong sign** | **.897858 wrong sign** | 1.007743 | 1 / .999972 / 1.000030 | 1.129713 [1.035713,1.283063] | REFUSED; robust slope changes no conclusion |

The expanded 64-site control also overturns the apparent native-S25
sharpening safety from the earlier 24-seed run: USM is now **+2.829%**, outside
the unchanged 1% bar.  The empirical noise floor activates in **96.25%** of
licensed base bin/site cells, yet V1's USM error grows to **+16.316%** and its
noise median stays at .458762x.  A fixed floor does not preserve the common-filter
cancellation: unclipped USM raises repeat-difference energy above the floor
selectively.

The Gaussian-equivalent shape conversion restores USM invariance but is not a
resolution statistic: blur scores sharper and real improvement scores worse.
It also lets extra white noise improve the score by median 13.0–16.2%.
Independent 33-step PCHIP linearisation is the one clean success: V3–V5 move
under affine/gamma/logistic by at most **0.0141%**, without losing their USM
result.  Tone can therefore be fixed without ordinality, but that does not fix
the optical/noise defeats.

### Controls and formal-M1 preflight

The source-only eligibility bins from 0.20 upward read
`point/LCB = 2.715/1.978, 3.645/2.051, 2.051/1.018,
2.045/.865, 1.373/.254`; only the first two pass.  Equal-focus and flat
sources refuse.  The point-only plant reads 2.1875 with LCB 1.296875 and
refuses.  V1–V5 refuse both untouched and USM flat ROIs; C0 instead emits
numeric values whose USM/base ratio is 1.008060.

The reference-derived angle estimates are
`.513040, 1.025409, 5.118501, 12.262438` degrees.  V4/V5's `[2,10]` gate
correctly separates the four geometries in isolation, but the required
5-degree numeric arm remains officially refused because the source itself is
ineligible.  C0–V3 have no angle gate.

The checker catches **27/27** single-property sabotages, including an executed
zero-floor child mutant, point-only eligibility, flat admission, survivor-only
output and MTF50 relabelling.  Two full child runs are exactly deterministic;
all three inherited source hashes and 11 function ASTs pass.

Formal real M1 remains blocked without opening pixels: matched bee darks/flats
are both count zero, the defocused-source denominator is undefined, current
outputs are linear sRGB against a ProPhoto contract, every baseline output is
scale-invalid, and the independent repeat's second block remains over the
registration gate at `.107703` native px.  Absolute MTF50 was explicitly
out of scope; every hardening variant reads only `[.20,.25)`.

Reproduce from the repository root with all numerical thread variables set to
one:

```powershell
python -B experiments\M-PHASE0-SLANTEDGE\s25h_commission.py --checker-only
python -B experiments\M-PHASE0-SLANTEDGE\s25h_real_preflight.py
python -B experiments\M-PHASE0-SLANTEDGE\s25h_commission.py
```
