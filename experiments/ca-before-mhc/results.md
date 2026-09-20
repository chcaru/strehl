# CA ordering: first generated result

MEASURED, experimental and default off. No photographic improvement or SOTA
claim follows from this result. The original 20-case screen completes but
records `photographic_replay_admitted=false`: every fine-colour case fails the
predeclared baseline witness-strength requirement. Preserve that result.

Commands actually run from the repository root with Python 3.12:

```text
python -I -B -X faulthandler experiments/ca-before-mhc/run.py build --out experiments/ca-before-mhc/build-2
python -I -B -X faulthandler experiments/ca-before-mhc/run.py controls --build experiments/ca-before-mhc/build-2 --out experiments/ca-before-mhc/operator-1 --filter merge_cmd::ca_before_mhc::independent_controls::independent_operator_controls
python -I -B -X faulthandler experiments/ca-before-mhc/run.py controls --build experiments/ca-before-mhc/build-2 --out experiments/ca-before-mhc/screen-1 --filter merge_cmd::ca_before_mhc::independent_controls::independent_quality_screen
```

Fresh compilation of both `strehl-cli` and `strehl-native-gpu-gather` is recorded
in build-2/process.log. Build-1's compilation failure remains recorded: the
independent fixture needed an explicit digest byte formatter and the QuadSource
trait import. Those repairs and a trailing blank-line removal changed neither
the candidate arithmetic nor its acceptance thresholds. Build-2 cli-tests.exe
SHA256 is `234e3ab8dc7391bb68df989002b4da20be46c4ebe24efea38c7815d39c591526`.

The operator controls pass. Zero CA reproduces the existing GPU route and the
absent-profile CPU rounded consumer exactly. Native known sites and corrected
green sites are exact; affine colour-field maximum error is 0.5 DN in each of
the three arms. Wrong-sign CA is a live destroyer. Unsupported and nonfinite
pulls refuse, original u16 inputs remain unchanged, and extra blur, half detail
and desaturation fail the metric controls. See operator-1/output/operator.json.

All 20 cases have lower RGB and chroma truth error with Before than Current.
The four flat RGB ratios are 0.9104–0.9120; flat chroma ratios are
0.9392–0.9717. Neutral-chip chroma ratios are 0.7056–0.8364 across both ISOs
and alignment phases. These errors can reward smoothing, so they cannot alone
establish useful detail retention. Colour-edge RGB/chroma errors also improve.

All eight fine/focus cases are refused because Current's R/B in-phase recovery
is below the required 0.5: approximately 0.366–0.469. Before increases R and B
recovery in each case, while green retains at least 0.988 of Current. Thus this
is an inadequate retention witness under the frozen criterion, not an observed
loss of fine R/B detail caused by Before. The `component_pass` field includes
the baseline-strength condition; its false value must not be described as a
measured candidate attenuation. See screen-1/output/screen.json for all arms,
including quadrature components. Truth-capped in-phase recovery can miss other
artifacts, which is why RGB/chroma truth errors accompany it.

The actual original-noise probe changes with Before. StagedAfter retains the
Current green inputs, guide, probe, variance and final green planes exactly;
zero-CA actual merge is also exact. These are operator checks, not an optical
calibration: the injected sensor model and radial coefficients are supplied
constants. Generated performance cannot validate those constants on real data.

Root decision, supported by independent review: add one separately declared
half-frequency colour qualification, leaving the original failed screen intact.
Its purpose is to supply the missing strong baseline witness with the same
thresholds and unchanged candidate. No frequency search, second reduction or
algorithm adjustment is authorized by this decision. A passing qualification
can admit one complete photographic comparison; it cannot promote the product.
