# Independent paired-prior source review

2026-09-19. **Ready for the fixed commissioning and paired run.** This is a
read-only source/choice review; no commissioning, optimization, scoring or RAW
execution by this reviewer or the numerical author. Root owns execution. The
first screen and both continuation outcomes remain recorded, and the separate
physical-quadrature failure still prevents real-photo admission.

The implementation changes exactly the proposed image term. Original calls
the frozen `state.prior()`; composite replaces its mean of two sheet Hubers
with the same vector-Huber of alpha-weighted pinhole radiance. The fixed DN
scale, coefficient and directional normalization remain, as do alpha TV,
double-well and sheet L2. The matte stays in the differentiation path. This
changes what is penalized rather than merely adding regularization, but does
not preserve the effective strength in every latent direction: removing sheet
smoothness permits hidden-sheet compensation even as opacity-induced output
texture becomes penalized. The experiment tests that tradeoff; it does not
assume that the earlier flat failure has already been attributed to alpha.

The independent controls exercise opposing cases. Unequal constant sheets
with textured alpha have a zero old image term and a live new term with a
positive alpha-amplitude derivative; a deliberately alpha-blind composite
fails. Compensating sheets with constant delivered RGB reverse that ordering.
An independent f32 NumPy Huber checks values, and the difference of total
priors checks preservation of the other terms. The one-layer route returns
the frozen prior literally and requires exact value and live radiance-gradient
identity. Equal two-sheet values are correctly not mistaken for equal
independent sheet gradients at arbitrary alpha. These controls establish
operator behavior, not calibration, optical adequacy or image quality.

Every one of the four cases restores the same original160-step two-layer state
for each paired arm, with exact parameter and reconstruction checks. The
far-only scene also uses two-layer fits here; this differs explicitly from the
one-layer convergence diagnostic. Both objectives receive the same fixed
1000-iteration/1400-nominal-evaluation budget and1800 actual cap, with the same
likelihood, optics, noise, censoring, support and training-only facade. Storage
conversion preserves logical gradients. Actual returned-state evaluation,
accepted-state checks, gradient threshold1e-6 and refusal handling are retained.
Matched budgets do not imply matched or attained convergence; nonstationary
results cannot identify an objective's optimum. No truth-selected iterate or
held-out-dependent stopping is present.

The scorer preserves all original absolute image and prediction bars, and
adds the specified paired protections: flat RGB/chroma <=1.05 original,
structured core/ridge RGB <=1.02 original, and every colour's glint/real-ridge
component >=.98 of truth-capped original recovery. Requiring live original
components >=.5 prevents vacuous retention. Capping the reference at1 avoids
punishing removal of original overshoot; absolute RGB errors still guard
against manufactured contrast. The original mean/oracle/far-only references
remain frozen. Bright and CFA prediction strata cannot be replaced by a global
average. Angular mismatch stays descriptive, and numerical completeness and
stationarity are separate from image checks. Neither outcome changes the
earlier failed results or licenses real RAW work.

The root wrapper's actual CLI sequence is positional `commission`, then the
paired fitter, then positional `score`. It binds scripts, plans, this review
and prior frozen sources, checks them after every subprocess, requires a passing
commission before any fit, and caps the fit at600seconds. Its paths agree with
both scripts. Commission and scorer are independent of the numerical author;
all three subprocesses are executed by root.

Reviewed SHA256 bindings:

| File | SHA256 |
| --- | --- |
| composite-prior.py | `856003f26de6ec841a5b4e6ff1dd06ac35bdc3a95baec1683e5fa91889038a6d` |
| composite-prior-plan.md | `cdda538d94c1237b51177797141444e940567d43e395b18bdb40877e1885d870` |
| independent-composite-score.py | `3ceb0517da70155a85f8248ae417b1391a7481f058005e42db66da9c0afed1e2` |
| independent-composite-plan.md | `fb3c474d9b6080d45494e18105a07164f63b9e7226131a79248375e7dcfb4b69` |
| run-composite.py | `aa8a68a7bf0c8eb9438db973de0fd6b87af51cd968347f1d0180d9ec6498f392` |
