# M147 — in-field magnification preflight

Status: **SYNTHETIC COMMISSIONING PASS; FIELD COMMISSIONING BLOCKED; DO NOT
SHOOT**

## 0. Verdict first

**MEASURED — YES, CONDITIONALLY.** On burned real RAW material the final
estimator resolves the `1.54%` design margin: a planted `2.031200x` ratio is
recovered as `2.0329159x`, with conservative interval
`[2.0126457, 2.0672587]`, so its lower bound clears `2.0`. Five scale plants
from `1.9720x` through `2.0517x` have point errors no larger than `0.0845%`.
The final same-state null reads `1.0003039x`, covers `1.0`, and correctly
returns `FAIL`. Full-resolution two-RAW runtime is `25.40 s`.

**MEASURED.** The frozen synthetic battery passes all 38 recorded arms:
18 named scale/nuisance/refusal/regression arms plus 20 interval-coverage
trials. It includes perspective, `3%` anisotropy, strong and weak second- and
third-harmonic traps, mild and hopeless blur, partial grid, no grid, a
single-site defect, and a rotated-site mapping attack. All 20 independent
analytic perturbations cover truth; none of 14 truths at or below `2.0`
passes.

**UNVERIFIED.** This is still not a field-commissioned gate. There is no real
converter-on/converter-off grid pair in the corpus. The current `0.25%`
systematic expansion is empirically conservative for the commissioned
synthetic and real-frame-resampling arms, but it remains explicitly unbound
for a change of optical train. The real-optics interval near `2.03x` is the
gating unknown, and the program must not infer it from the synthetic pass.

**DECISION.** Do not shoot the 891-frame session. The owner-facing two-frame
request is live as Ask 2a: photograph the same physically unmoved calibration
slide once with the converter fitted at maximum reproduction and once with it
removed near `1.32x`. Those two RAWs decide whether the registered target has
enough margin or must move. The tool prints an explicit provisional-build
warning until that measurement is adjudicated.

## 1. What the tool measures

**DERIVED.** For one physical grid pitch `g`, sensor pitch `p`, and
magnifications `m_ref` and `m_TC0`, the measured sensor-pixel periods are

```text
P_ref = g * m_ref / p
P_TC0 = g * m_TC0 / p
P_ref / P_TC0 = m_ref / m_TC0.
```

The grid pitch and sensor pitch cancel. The tool therefore divides measured
periods directly. It never derives absolute magnification and never reads EXIF
focal length into the decision. The cancellation argument in the capture
design is correct.

**IMPLEMENTED.** `experiments/M147-preflight/preflight.py`:

1. accepts two explicitly role-labelled `.ARW` paths;
2. hashes the original files with SHA-256;
3. copies `rawpy.raw_image_visible` while the decoder context is alive;
4. uses the two native CFA green sub-lattices independently, with no demosaic
   and no resize;
5. detrends overlapping local `512 x 512` green-site tiles and applies a Hann
   window;
6. finds two non-collinear reciprocal-lattice peaks in each local 2-D Fourier
   spectrum, refines their coordinates parabolically, and converts their
   determinant to local pixels per grid period;
7. selects the dominant period family, refuses competitive families, and
   explicitly tests second- and third-harmonic alternatives whose implied
   primitive remains in the admitted period range;
8. requires agreement between green phases, local period stability, adequate
   peak evidence, and compatible two-axis scale and rotation;
9. maps reference sites into TC0 and retained TC0 sites back into reference
   coordinates using the measured scale and signed rotation, then takes the
   median of mapped block ratios as the decision point; and
10. retains every quality-cleared mapped site, before block aggregation, in
    the lower-bound envelope, so one spatially bad strip/site cannot disappear
    inside a plausible block or global median.

This local reciprocal-lattice design was chosen because defocus attenuates a
periodic peak without moving it, affine illumination is removed before the
FFT, and rotation changes the two peak vectors without changing their
determinant. The coordinate map is necessary: equal sensor coordinates do not
represent the same physical target location after a `2x` scale change. Spatial
block results remain in the JSON rather than being discarded behind one
global number.

**FROZEN / BOUNDED.** The admitted primitive period is `20` to `96` green
pixels. The upper bound is specific to this commissioned slide: the burned
reference measures about `63.5` green pixels and the expected TC0 state about
`31` to `32`, leaving roughly `50%` headroom above the reference. A
second- or third-subharmonic alternative refuses only when it clears all
three evidence floors: `12 dB` above the global spectral floor, `20 dB`
above its local floor, and `-50 dB` relative to the selected peak. The first
two reuse the lattice evidence scale; the relative floor was frozen with a
`13 dB` guard from the strongest commissioned Hann-leakage case
(`-62.9 dB`) and a `17 dB` guard from the weak planted primitives
(`-33.0 dB`). This is a declared detectability bound, not proof against an
arbitrarily invisible primitive.

## 2. Interval and gate

**IMPLEMENTED.** The current interval independently resamples accepted
spatial-block period estimates in each image for `10,000` deterministic draws
(seed `14720260904`), recomputes the direct ratio of medians, takes percentile
`[0.025, 0.975]`, envelopes all four cross-green ratios and all mapped-local
ratios, and expands the result by a relative `0.0025` on each side. The
reported interval covers the spatial-block extraction variation represented
inside the supplied pair, spatial variation visible in those two frames,
green-phase disagreement, and that additional fixed development allowance.
It is not a temporal repeat-capture interval and does not cover physical drift
after the preflight frames.

**MEASURED / UNBOUND.** The `0.0025` began as a conservative development
choice, not a derived constant. In the frozen synthetic perturbation family,
all `20/20` claimed intervals cover planted truth and the maximum point error
is `0.0307%`; this is evidence that `0.25%` is conservative in that domain.
It still has no empirical or physical derivation for converter-dependent
distortion, different optical blur, target non-coplanarity, or a real change
of optical train. It therefore remains visibly provisional until the requested
optical pair is measured; it must not be tuned downward after seeing that
pair.

**IMPLEMENTED.** A numerical reading is eligible only after RAW, lattice,
spatial stability, green-phase, anisotropy, rotation, and precision checks.
The decision then uses unrounded values:

```text
PASS if and only if interval_lower >= 2.0.
```

A point estimate above `2.0` with a lower bound below `2.0` is a `FAIL`. A
measurement refusal is also a `FAIL` and carries no ratio. There is no
separate symmetric/full-width cutoff: only the lower tail can create an unsafe
pass, while a broad upper tail is harmless to this one-sided decision.

## 3. Frozen commissioning results

The real source frames are deliberately burned development material. None of
these values is a score. The final artifact is
`experiments/M147-preflight/out/commission.json`.

### 3.1 Null and planted scale

| Arm | Truth | Recovered | Conservative interval | Gate | Commission result |
|---|---:|---:|---:|---|---|
| Real same-state null, consecutive `DSC00042/43.ARW` | `1.0000000` | `1.0003039` | `[0.9934196, 1.0072404]` | `FAIL` | truth covered; correct refusal |
| TC0 `-1.0%` | `2.0517172` | `2.0526370` | `[2.0215391, 2.0882257]` | `PASS` | correct |
| Nominal target | `2.0312000` | `2.0329159` | `[2.0126457, 2.0672587]` | `PASS` | correct |
| TC0 `+1.4%`, just inside nominal margin | `2.0031558` | `2.0042409` | `[1.9844104, 2.0383956]` | `FAIL` | correct conservative gate |
| TC0 `+1.7%`, just outside margin | `1.9972468` | `1.9982202` | `[1.9784753, 2.0323448]` | `FAIL` | correct |
| TC0 `+3.0%` | `1.9720388` | `1.9729452` | `[1.9554179, 2.0071546]` | `FAIL` | correct |

**MEASURED.** The real null's point error is `+0.0304%`; its axis ratios are
`1.0002391` and `1.0002802`, and its full relative interval width is
`1.3817%`. The two original full active-area RAWs complete in `25.40 s`.

**MEASURED.** Maximum point error among the five scale plants is `0.0845%`,
about `18x` smaller than the `1.54%` margin. The nominal lower bound is
`2.0126457`, with `0.6323%` headroom over the hard gate. Its lower-side
uncertainty is `0.9971%` of the point estimate. Thus this synthetic plant
resolves the nominal margin, but with about a `1.54x` lower-side margin, not
the earlier null-based `2.06x` projection.

**MEASURED.** The just-inside arm illustrates the intended gray zone: its
point estimate accurately remains above `2.0`, but its lower bound does not,
so the tool says `FAIL`. This is not a point-estimation error; the owner must
reduce TC0 magnification enough to clear uncertainty.

**LIMITATION.** The scale plants resample one real capture, so source pixels
are correlated and interpolation adds non-optical blur. They prove scale
recovery and gate direction under controlled truth. They do not predict the
interval of a real converter change.

### 3.2 Required nuisance and refusal arms

| Arm | Plant | Observed | Result |
|---|---|---|---|
| Perspective | `3.5%` projective scale gradient around nominal | global-looking point `2.0313995`; mapped-local minimum `1.9971411`; lower bound `1.9921483` | `FAIL`; bad local region cannot average away |
| Single retained-site defect | one mapped site at `1.99` inside an otherwise `2.02` block | block-median point `2.02`; site envelope minimum `1.99`; lower `1.985025` | `FAIL`; site cannot be medianed away |
| Rotated-site mapping | `+10 deg` map; `1.99` site exists only at physically correct rotation | site envelope minimum `1.99`; lower `1.985025` | `FAIL`; signed `[y,x]` map reaches the bad site |
| Anisotropic scale | axis ratios `2.0312` and `2.092136` | measured disagreement `2.978%`, over `1.500%` limit | typed `ANISOTROPIC_SCALE_CHANGE` refusal |
| Wrong-period alias, second harmonic | true ratio `1.0`; scored second harmonic made dominant | coherent `1/2` alternative detected | typed `AMBIGUOUS_HARMONIC` refusal |
| Weak-primitive second harmonic | same, but primitive is `-33.02 dB` relative to selected harmonic | alternative is `59.03 dB` above global and `55.53 dB` above local floor | typed `AMBIGUOUS_HARMONIC` refusal |
| Wrong-period alias, third harmonic | true ratio `1.0`; scored third harmonic made dominant | coherent `1/3` alternative detected | typed `AMBIGUOUS_HARMONIC` refusal |
| Weak-primitive third harmonic | same, but primitive is `-32.90 dB` relative to selected harmonic | alternative is `62.77 dB` above global and `59.11 dB` above local floor | typed `AMBIGUOUS_HARMONIC` refusal |
| Mild blur/gradient/rotation | truth `2.0312`; Gaussian blur `2.5` green px, `35%` gradient, `-4 deg` | `2.0310200`, interval `[2.0240627, 2.0365495]` | `PASS`; `0.0089%` point error |
| Hopeless blur | Gaussian blur `40` green px | only `3` lattice candidates, below required `12` | typed `NO_COHERENT_GRID` refusal |
| Partial grid | centered `320 x 400` green-pixel window only | only `9` lattice candidates, below required `12` | typed `NO_COHERENT_GRID` refusal |
| No grid | smooth illumination plus correlated noise | largest coherent cluster has `7`, below required `12` | typed `NO_COHERENT_GRID` refusal |

**MEASURED — DEFECT FOUND AND FIXED.** The initial estimator failed the
factor-two trap: on truth `1.0` it returned a confident numeric
`2.0000017`. It happened not to pass only because the provisional expansion
pushed the lower bound below `2.0`; that was accidental protection, not alias
recognition. The preserved artifact is `out/alias-defect-v0.json`. The frozen
estimator now refuses strong and weak explicit second- and third-harmonic
alternatives.

**MEASURED — INDEPENDENT REVIEW DEFECTS FIXED.** A first independent
`gpt-5.6-sol`/max verification found three genuine false-PASS paths:

1. the conventional `[x,y]` rotation matrix had been applied to `[y,x]`
   coordinates, missing a planted `1.99` site and returning `PASS`;
2. local samples were median-collapsed by block before the lower envelope, so
   one retained `1.9896` sample disappeared; and
3. a relative-only `-30 dB` harmonic test accepted factor-two and factor-three
   aliases whose primitives were about `-33 dB`, returning numeric `PASS`.

It also found that a RAW quality refusal could omit already-computed input
provenance. The frozen implementation corrects the rotation sign, maps both
directions, envelopes individual sites before aggregation, uses the
three-part harmonic evidence rule above, and carries file/decoded provenance
through quality refusals. The two mapping regression arms and two weak-alias
arms specifically reproduce the former false-PASS cases. A final independent
`gpt-5.6-sol`/max re-verification reproduced those attacks against the frozen
tree, confirmed all now fail closed, independently accepted all `38/38`
commissioning predicates, and reported no production-gate defect.

**MEASURED — BLUR LIMIT.** A planned `18`-green-pixel blur arm unexpectedly
remained measurable: it returned `2.0202` with an interval covering the
`2.0312` truth. It was therefore not honestly a hopeless-input test. The
frozen hopeless arm uses `40` green pixels and refuses for insufficient
coherent evidence. The instrument does not reject blur merely because it is
large; it rejects when the lattice is no longer measurable.

### 3.3 Interval calibration

**MEASURED.** Twenty deterministic trials use independently generated
reference and TC0 lattices, rather than resampling shared source pixels. Truth
is sampled from `[1.94, 2.07]`; period, phase, independent noise, relative
rotation, blur, and illumination gradient vary by trial.

| Calibration quantity | Result |
|---|---:|
| Truth covered | `20/20` (`100%`) |
| Wilson 95% interval on coverage probability | `[0.8389, 1.0000]` |
| Truths at or below `2.0` | `14` |
| False passes at or below `2.0` | `0` |
| Truths above `2.0` | `6` |
| Passes above `2.0` | `6` |
| Maximum point error | `0.0307%` |
| Median point error | `0.0121%` |
| Interval full-width range | `0.5004%` to `0.5042%` |

**LIMITATION.** `20/20` does not prove universal 95% coverage; the binomial
uncertainty is wide, as the Wilson interval shows. It calibrates only the
declared analytic perturbation family. The real null supplies one additional
covered truth under actual capture noise, but no existing data calibrates a
converter-dependent optical systematic.

### 3.4 Freeze and provenance

**VERIFIED.** The final artifacts record:

- estimator parameter SHA-256
  `bfb4b7d297a3f2c0e42c9d964fc140d0a03c663b8486d474a7b0742acf843739`;
- production source SHA-256
  `29ba7b8de9db80b7167fd068a3d96269d4d91287db5c823109ebeb149b1b8e98`;
- commissioning source SHA-256
  `41a2652136aed92268f866cc006fe14ff8daa0bcd65d9582a1ee33f7af7c91c7`;
  and
- commissioning-rules SHA-256
  `195f8a7674f0a23b25f3ed5ff79e4a5585217111dddb0acf494c0aa308b462d7`.

The final production source and parameters were frozen in commit `699d03f6`;
the strengthened battery and independent verifier were frozen in commit
`92d25dd2`. Both preceded completion of the final 38-arm artifact. No
production parameter was tuned after that campaign. The artifact file hashes
are:

- `out/null.json`:
  `2488be480821c66fb37998d552078e6773f4b273dc142840744de1045a85c236`;
- `out/commission.json`:
  `93930d869ef5aa373ea5039ccd836241766193e3782308683d481060a7784ba9`;
  and
- `out/verification.json`:
  `8fa86fbb8e1878006178dbbf40bd1b42e9e89d5b603cfd13a2570a581aa4c122`.

The independent `verify.py` does not import production modules. It re-hashes
both sources, parameter/rule sets, RAW files and decoded arrays; independently
recomputes arm sets, gate invariants, coverage counts, alias/mapping
regressions, each stored arm predicate, and field-blocked state; verifies that
a parameter mutation
changes the hash; and estimates the real null by 2-D spatial autocorrelation.
Its 24 checks pass and it independently obtains `1.0001490x` for the null.

## 4. Missing real pair

**VERIFIED.** M141's complete inventory reports that all `10,509` inventoried
ARWs use focal length `200 mm` and lens identity
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`. It explicitly concludes that
no frame proves the bare-lens TC0 state
(`docs/research/M141-capture-inventory.md:255-274`). The repository therefore
contains no real converter-on/converter-off grid pair at any ratio.

**REQUIRED.** The pending two-frame measurement must use:

1. the calibration slide, converter installed, maximum reproduction; and
2. the same physically unmoved slide, converter removed, TC0 near `1.32x`.

Use original full-resolution ARWs. Preserve the target plane and camera
roll/yaw; move axially to reframe. No scored session should begin before this
pair produces a commissioned lower bound at least `2.0`.

## 5. Operator command

Run from the repository root after the two frames exist:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\preflight.py `
  --reference-arw "D:\path\TR-REF-PREFLIGHT.ARW" `
  --tc0-arw "D:\path\TC0-PREFLIGHT.ARW" `
  --output-json "experiments\M147-preflight\out\field-result.json"
```

Expected successful form:

```text
M147 MAGNIFICATION PREFLIGHT
WARNING: provisional build; real converter-on/off commissioning is still required before shooting.
Reference period: <value> sensor px
TC0 period:      <value> sensor px
Sampling ratio:  <value>
Conservative 95% interval: [<lower>, <upper>]
Verdict: PASS
PASS: the interval lower bound is at least 2.0. Preserve the rig settings and proceed with the capture protocol.
Artifact: <absolute path>
Elapsed: <seconds> s
```

During the present provisional phase, even a literal `Verdict: PASS` does not
authorize the 891-frame session; the warning is intentional. After the
requested real pair is reviewed and the build is admitted, anything other than
literal `Verdict: PASS` means do not shoot. On a measured ratio failure the
tool reports the approximate percentage by which to reduce TC0 magnification
and also asks the operator to verify converter seating and maximum reference
reproduction. On a quality refusal it tells the operator whether to refocus,
reframe, correct the target plane, or retake.

## 6. Remaining field commissioning

All requested synthetic modes are complete. One arm remains:

| Arm | Required decision |
|---|---|
| Real converter-on/off pair | Run the frozen CLI on the two unmoved-slide frames. Admit the capture only if measurement status is `OK`, no local or alias gate refuses, and the unrounded lower bound is at least `2.0`. |

**CORRECTION TO THE EARLY PROJECTION.** Applying half the real-null full width
to the nominal ratio gave a projected lower bound `2.016039` and a `2.058x`
width safety factor. That arithmetic was correct, but transferring same-state
null width to a `2x` scale change was not established. The final physically
mapped nominal plant has lower bound `2.012646` and only a `1.54x` ratio of
design margin to observed lower-side uncertainty. It still passes, but the
earlier `2.06x` characterization must not be used.

The real optical pair is decisive. A synthetic result cannot bind the
converter-dependent systematic. If the frozen real result cannot clear `2.0`
at the registered setup, move the TC0 target lower; do not narrow the
interval, the `0.25%` expansion, or a quality gate after seeing the result.

## 7. Commands already run

Real null:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\preflight.py `
  --reference-arw "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00042.ARW" `
  --tc0-arw "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00043.ARW" `
  --output-json experiments\M147-preflight\out\null.json
```

Each final commissioning arm was run separately so the JSON remained
incremental. For example:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\commission.py --arm scale-nominal
python experiments\M147-preflight\commission.py --arm perspective
python experiments\M147-preflight\commission.py --arm alias
python experiments\M147-preflight\commission.py --arm coverage-00
```

Independent verification:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\verify.py
```

No command wrote beneath `D:\personal\macro` or `D:\edited\macro`.
