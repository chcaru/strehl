# M-PHASE0-SLANTEDGE — audit preregistration

Status: **frozen before this lane ran any new slanted-edge measurement**.

## Question and disposition

Can any slanted-edge/SFR implementation already in the repository support the
detail axis by itself?  This lane audits existing code; it does not create a
replacement instrument and opens no capture.

The candidates are fixed as:

1. `experiments/M88-optical-ceiling/src/m88lib.py` — the canonical
   single-green-sublattice RAW SFR;
2. `experiments/M104c-mtf/mtf.py` — an independent compact MTF50
   reimplementation; and
3. `experiments/BUILD-RESAMP/slanted_edge.py` — the rendered-output MTF50
   implementation with automatic edge discovery.

M88b and M128 are adapters around M88, not independent SFR estimators.  M128's
committed battery is already 5 PASS / 5 FAIL.  Kernel MTF models and ordinary
ESF-width scripts are inventory items, not slanted-edge instruments.

The only admissible positive disposition is **COMMISSIONED FOR RESOLUTION**:
all mandatory bars below must pass.  Otherwise the disposition is
**REFUSED AS A SOLE RESOLUTION INSTRUMENT**.  A candidate may still be useful
as a target/presentation diagnostic.

## Independent plants

`measure.py` makes neutral, noise-free Gaussian edges without calling any
candidate's synthetic generator.  It uses a Gaussian CDF sampled on a 5-degree
slanted raster.  Processed arms keep the same pixels and geometry:

| arm | fixed plant |
|---|---|
| base | Gaussian sigma 1.50 native px |
| blur | base convolved with an independent sigma 0.75 px Gaussian |
| real improvement | independently sampled sigma 1.20 px edge |
| sharpening challenge | unclipped float USM, radius 1.00 px, amount 0.50 |
| affine null | `1.7*x + 0.13` |
| monotone tone | gamma 3 and a strictly increasing logistic curve |
| noise | 24 fixed seeds, Gaussian sd 0.02 on a 0.60-contrast edge |
| licence challenge | sigma 0.60 px, whose true MTF50 exceeds 0.25 |
| angle | 0.5, 1, 5, and 12 degrees |

The candidate's own synthetic-edge helpers are forbidden.  Candidate geometry
is pinned from the base arm where its API permits that, so processing cannot
win through differential edge fitting.

## Fixed external predicates

`commission.py` imports neither `measure.py` nor candidate code.  It invokes
measurement in a child process and compares only serialized values with these
literal analytic anchors:

| quantity | fixed value |
|---|---:|
| Gaussian constant `sqrt(ln(2)/(2*pi^2))` | 0.1873906251292776 |
| base MTF50 | 0.1249270834195184 cyc/native-px |
| blurred MTF50 | 0.1117381803027320 cyc/native-px |
| blurred/base | 0.8944271909999159 |
| real-improvement MTF50 | 0.1561588542743980 cyc/native-px |
| improvement/base | 1.2500000000000000 |

These numbers are not emitted by the generator and are not read from an
implementation under test.

Mandatory bars:

1. identity changes MTF50 by at most `1e-12`;
2. base, blur and true-improvement MTF50 are each within 5% of the literal
   truth, and both directional ratios are within 5%;
3. post-render USM must be explicitly refused/flagged, or must not improve the
   resolution score by more than 1%;
4. affine, gamma-3 and logistic point transforms must each move MTF50 by at
   most 1%, or nonlinear input must be explicitly refused;
5. all 24 noise arms must remain within 5% of base and their median within 3%;
6. 5 degrees is accepted and recovered within 0.2 degrees; 0.5, 1 and
   12 degrees are refused by the published gate;
7. the sigma-0.60 arm emits only `UNLICENSED_GT_0.25`, never a number; and
8. the code path's RAW/developed/demosaic scope is stated.

The sharpening arm is decisive.  USM is a deterministic post-render filter and
adds no scene information.  Reporting it as a higher cutoff or MTF50 is RED
even if blur calibration passes.

## Checker power

Before judging candidates, `commission.py` must pass a literal all-GREEN
fixture and catch eight one-property sabotages: identity, blur magnitude,
positive-improvement blindness, sharpening, nonlinear tone, noise, angle gate,
and licensing.  A checker that cannot make every sabotage RED is not used.

