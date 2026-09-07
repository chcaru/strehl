# M194e independent scalar conversion oracle controls

2026-09-07, `roadmap_audit`. **MEASURED: 46/46 controls pass** after one retained
independent fixture-construction failure and the prospective rail clarification
described below. These controls commission the
independent reader on known private arrays. They do not execute the author's
renderer/emitter, supply a successful float commission, or commission real
M194e CFA output. The prospective choices are in
[independent-emission-design.md](independent-emission-design.md), approved by
root before implementation.

Executed from the repository root:

```text
python -B experiments/m194e-joint-pupil/independent-cfa-controls.py --out experiments/m194e-joint-pupil/independent-cfa-controls-1
python -B experiments/m194e-joint-pupil/independent-cfa-controls.py --out experiments/m194e-joint-pupil/independent-cfa-controls-2
```

The first command exited1 after11 passing checks. Its wrong-WB fixture used
integer `/4`, making a float where the independent exact-rational quantizer
requires a Fraction. The sole correction replaces that expression with
`Fraction(int(scalar[y,x]),4)`. Original source, the11 check records and copied
tool traceback remain in `independent-cfa-controls-1/`; this was a harness
failure, not evidence about the author's conversion or optical model.

The second command exited0 using Python3.12.10 and NumPy2.4.4. It ran all39
checks:11 positive/null,14 destroyer and14 malformed-input checks. Every
fixture and checked source hash remained unchanged across the run. The result
and per-check log are in `independent-cfa-controls-2/`.

| Artifact | SHA-256 |
| --- | --- |
| `independent-cfa-oracle.py`, both runs | `1c4c1b4f8deac557986a1c630bdbe2b6564ce05e1887f5bde2beef96eaa00246` |
| `independent-cfa-controls-1/first-controls.py` | `0251fc676917911c342b64367ef05628a77d24704900e9e07869921ddbf9aa06` |
| `independent-cfa-controls-2/checked-controls.py`, second run | `5dcb5505067b1c237b3d13efed53096c900d80fd5935af2f67de7073acd7e94f` |
| `independent-cfa-controls-2/result.json` | `3c43f0a2b01eec80ebf15901ca98d1110266f6d8ef84620014f74968e95f1617` |

The oracle independently chooses native RGGB parity and uses scalar binary-f64
multiplication followed by an explicit floor/fraction/even-integer decision.
It calls neither the author's conversion nor NumPy's rounder. Constant20e and
12000e fields agree with the fixed literal channel tables. Seven parity-specific
tie cases agree with exact rational expectations at the tie and on both sides
using ±2^-20e. The half-up destroyer disagrees in all four even-down cases;
three even-up ties and the ordinary non-tie companion remain inert as expected.
These choices expose a wrong tie rule without pretending every tie distinguishes
rounders.

Actual nonconstant48×64 NPY and headerless little-endian u16 files pass an
initial and final read. Thirteen altered-file controls reject: phase, red
factor, omitted gain, added WB, black offset, balanced deterministic noise,
isolated CFA sample, row reversal, transposed flattening, big-endian payload,
truncation, append and isolated expected-electron change. All destroyers are
asserted to change the stimulus. NPY/coordinate/quantizer controls separately
reject wrong dtype, endian, dimensions, complex/bool, negative/nonfinite values,
truncated/appended/malformed containers and invalid indices. NPY loading has
pickle disabled; raw u16 is independently read with `struct`.

The wrong noise/WB arrays are deliberate conversion corruptions, not an
optical-model or noise-calibration experiment. Fixture files have no genuine
float/model authority and are ineligible for final emission evidence. The
second-run helper recorded white/over-white occurrences without deciding the
then-pending white-rail endpoint admission rule. Receipt binding, exact
source/model/control provenance, actual observer off/count/placebo execution,
and the five genuinely commissioned emitted frames remain dependent checks.
No production, RAW, quality-matrix, scorecard or historical-artifact change.

## Prospective rail clarification and third run

After the second run, the author pinned nonnegative finite electrons, valid
black512, unquantized DN in `[512,15360)`, and a rounded code strictly below
15360. Values just below white that round onto white refuse; no clipping.
Before adding that validation, the second-run oracle/control sources were
copied to `independent-cfa-controls-2/checked-oracle.py` and
`checked-controls.py`, preserving their recorded hashes.

```text
python -B experiments/m194e-joint-pupil/independent-cfa-controls.py --out experiments/m194e-joint-pupil/independent-cfa-controls-3
```

This command exited0 with46/46 checks: the previous39 plus black/zero and
near-white valid companions, and five white-endpoint/rounding refusals. All
sources and original fixture files stayed unchanged. At a green site,59389e
gives DN15359.25/code15359 and passes;59390e gives a tie rounded to15360 and
refuses.59391e,59392e,59393e and59392−2^-20e also refuse for their recorded
rounding or unquantized rail condition. No optical reference or actual author
emission was used by these controls.

| Third-run artifact | SHA-256 |
| --- | --- |
| `independent-cfa-oracle.py` | `1b23d656481752fc3c34384c489fc6556e78a74925d8cd717f4faa350040d48a` |
| `independent-cfa-controls.py` | `40f6da304c24fce4bb0961d884d220e31a5fd822b731518794ca5a3b73944906` |
| `independent-cfa-controls-3/result.json` | `a051fa295294781df3ba3ad08152b59aac287dc5bd679eedf3497c1d565fcfc5` |
