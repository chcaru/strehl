# Even-power phase registration for insect detail

Root allocation2026-10-27. Experimental, default off. No quality gain established.
The consumer is each source's placement at the actual merge, in anchor149's
3516x2344 guide gauge (two native sensor pixels per guide pixel). The target is
the complete299-source glitter-weevil107 photograph, preserving the native
CA-off baseline, fixed development, full6896x4596 crop and HeliconB4/B8 context.
Bug2 and flat60 remain transfer requirements before any generalization.

## Changed question and prior art

The exact change is the squared normalized cross-spectrum (p2), compared with
ordinary normalized cross-spectrum (p1) using identical windows, noise weights,
frequency support and physical CFA samples. Ojansivu and Heikkila's2007
[primary paper](https://www.eurasip.org/Proceedings/Eusipco/Eusipco2007/Papers/c5p-j01.pdf)
shows why an even phase power removes the sign of a real, centrally symmetric
blur transfer. The shift is doubled and ambiguous modulo half the patch period.
This does not guarantee robustness to noise, a finite window, multiple depths,
asymmetric blur, visibility changes, clipping, or geometric differences within
the patch. It is not a new invention or generic defocus-invariant alignment.

Root ran unified and mechanical searches for phase correlation (both exit0).
M78 tested Gaussian cross-blur/NCC and phase-shifted samples, not p2.
BUILD-CHROMA/M116 use ordinary phase correlation; M-PHASE0-XSPEC uses a weighted
first-order phase ramp and reports poor repeatability/NOT ROBUST. Its negative
expectation remains relevant. Current insect-field-stability rejects the fixed
six-scalar per-step residual field, not a changed direct pair reader. The
current map is usable but not certified truth. Read the three concise source
audits in ../insect-fidelity-next/ and the M103 amendment to ledger rule6.

## Scope and ownership

Cfa-residual owns `phase.py` and implementation notes: one fixed f32/complex64
reader on separate unresampled physical G1/G2 planes from original u16 CFA.
No MHC, RGB input, source-frame interpolation, inferred PSF, or aligned volume.
Use the one injected ISO100 shot/read model; do not fit a private floor.
Return all raw diagnostics and explicit refusals. A small residual search about
a declared integer seed resolves only the local doubled-shift branch. Preserve
ordinary p1 as a causal mechanism comparison. No parameter sweep.

Integration-review independently owns `controls.py` and control protocol,
challenging signal support, reference choice, shared assumptions and refusal.
Root owns wrapper, scheduling, actual-reader/graph/render release and decisions.
Photo-review owns independent complete-image acceptance if a render is released.
Only source implementation and the bounded controls below are currently released;
no actual-data numerical job, global solve, build or render is yet released.

## First screen and stopping rule

Run flat/noise cases first. Commission sign, half-shift units, peak branch,
rank-deficient periodic texture and insufficient/noise-only frequency refusal.
Use independently rendered continuous Fourier scenes with symmetric disk-OTF
sign reversals (not merely positive Gaussian blur), an ordinary no-reversal
case, fractional translations and a curved source track carrying measured
curvature. Exercise displaced windows, scale/rotation across a patch,
asymmetric PSF and two-depth/visibility alternatives. Shared G1/G2 agreement,
reverse consistency or lower fitted residual never establishes physical truth.
Truth controls score per-frame placement in a stated gauge; an endpoint alone
cannot pass. A deliberately wrong sign or factor-of-two must fail that scorer.
Refusal is valid for unsupported ambiguity; it cannot be hidden by dropping
failed populations. Report p1 and p2 on the complete fixed populations.

Root permits one controls job after independent source review, bounded300s wall,
1200CPU seconds,8GiB committed host,4GiB GPU; fourCPU workers, one GPU job.
Preserve executed sources, exact command/environment and terminal Job evidence.
Do not retune after outcome. A failed control can justify a narrowly diagnosed
implementation repair with archived prior bytes, not an empirical threshold
search. Stop this recipe if it cannot pass its stated mechanical and useful
signal controls. No synthetic score is a photographic gain.

If this screen passes, root may release one direct actual-reader campaign and
one complete paired photographic discriminator without a new ROI/threshold
search. Keep all original pair/tile statuses, including long-span failures and
short load-bearing edges. Fit direct pairs globally in the anchor's connected
component with the existing solve, report every unplaced frame and cycle rank,
and preserve the original gauge/resampler. Any actual physical placement claim
needs independent per-frame evidence; photographs alone cannot supply it. The
old/new complete output under identical development determines usefulness.
No continuing geometry investigation is authorized by a crop or metric gain.

Every final photographic claim must include whole images and full-resolution
masters. Preserve weak colors, hairs at distinct depths, contour identity,
glints and the flat background; increased contrast/noise is not recovery.
The currently usable renderer still has a legacy per-source-MHC/remosaic path;
this geometry experiment is native-compatible but does not repair that separate
contract violation or itself establish the requested final native architecture.

Independent photographic dissent is retained: photographic-next.md favors the
existing non-native fusion-order boundary diagnostic and finds no demonstrated
missing topology or identified geometry cause. Root selects the distinct p2
screen because the native-compatible sign-inversion mechanism is untested, not
because that photographic uncertainty has been resolved. Photo-review also
owns `full-render-plan.md`, a source-only reuse plan while controls are prepared.
