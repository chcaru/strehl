# Plan Q1 and Q2: restoration on every A7CR stack, never below the system

Ledger row `shd-q-restore-2026-11-23`. Plan: [subject, highlights and detail](../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md),
section 3. Branch `studio2/shd-restore`.

## Setup

- Stacks (A7CR, FE 100mm F2.8 Macro GM OSS + 2X Teleconverter, f/5.6, four-shot):
  scarab `stack-1795300522964-6430`, harlequin `stack-1795371396674-6430`, lanternfly
  `stack-1795433406862-8651`, weevil `stack-1795460665629-8651`, all under `D:/StrehlCaptures`.
- `render.py`: the desktop's arguments and environment (`crates/strehl-ui/src/jobs.rs`),
  private `STREHL_CACHE_DIR` under `C:/w/shd-restore-out/cache`, capture folders checked
  unchanged after every render. Release builds of `strehl` (default features, GPU fold auto),
  32 logical CPUs, another agent possibly building on the same machine.
- Arms: `base` (e09d0593f code; binary reports cb2c67faa961), `q1c` (bb27b1ab0, Q1 only),
  `q2` (Q1 and Q2), `off` (Q2 binary, `STREHL_OPTICAL_RESTORE=off`). The base arm repeated
  on the scarab gave identical master and photograph bytes (VERIFIED).

## Q1: the weevil's cutoff

Cause tests on the per-tile spectra the dump now records (`fit-cause.py`, `fit-cause.txt`;
MEASURED). The Python port of the joint fit reproduces the render's spectra to 1e-15 and its
fit (weevil 0.900, lanternfly 0.776).

- Low signal-to-noise is not the cause. The weevil's reference frames have a higher
  signal-to-noise power than the lanternfly's, which fits: green 8.5 against 1.6 at 0.3-0.4
  cycles/px, 3.3 against 0.44 at 0.4-0.49.
- Subtracting the measured noise spectrum makes the weevil converge (0.596 at the full
  noise, 0.836 at half) but drives the lanternfly to the grid's floor (0.400 and 0.436). The
  reference signal is a cross-spectrum, with no temporal noise in it in expectation, so the
  arm is unprincipled. Rejected.
- Leaving out tiles with near-pinned samples does not help at any threshold: the reference
  peak at or below 0.95, 0.80, 0.50, 0.30 or 0.20 of the range (88 to 25 tiles), or the merged
  peak likewise. All stay at the ceiling. Rejected.
- The fit stays at the ceiling over 0.20-0.40 alone (`fit-shape.py`, `fit-shape.txt`), so
  the band near Nyquist is not the cause. The green spectrum's local slope minus a
  diffraction model at 0.776 stays near -2.3 to -2.9 from 0.23 to 0.44 cycles/px. On the
  lanternfly it steepens from -3.6 to -4.7. So the weevil's reference rolls off less steeply
  than diffraction at any cutoff the grid allows, under a single power-law object (DERIVED).
  An object spectrum that flattens toward fine scales (point-like glints and dense scale
  texture beside a smooth body) would do that. UNVERIFIED.
- 64 of the 90 tiles fit at the ceiling one by one. The 26 that do not give 0.784 together,
  but the same selection reads 0.664 on the lanternfly against its 0.776: a biased choice,
  not a remedy.

Neither named candidate fixes the fit, so the fix is the fallback alone:

- Every measured joint fit is stored in `optical-cutoffs.json` in the engine's cache folder
  (`%LOCALAPPDATA%\strehl\warpmaps`, or `$STREHL_CACHE_DIR`), one record per capture. A record
  is keyed by body, `LensType3` (the composed path, converter included), f-number and system
  model, with the capture's median planned focus position. The four fits read from the
  owner's render logs are built in as seeds: the three above plus the close tile
  (0.588 at 61,812).
- A fit at the ceiling takes the nearest stored fit for the same gear within 16,000 focus
  units. That limit is ARGUED from these four fits. The log names the fit:
  `cutoffs R/G/B 0.692/0.776/0.893: STORED fit of stack-1795433406862-8651 (focus 31239, this
  stack 25175; ...), because ... ran to its ceiling`. The desktop gets
  `STREHL_UI_PROGRESS event=optical-restore state=stored cutoff=0.776
  from=stack-1795433406862-8651 from_focus=31239 focus=25175 fitted=0.900`, and the Stack
  station's checks show it as "Optical restoration". A stack with no stand-in is still
  written unrestored, saying why, with `state=off`.

Gate (`compare.py base q1c`, `q1-gate.txt`; VERIFIED):

- The weevil renders restored with no environment variable set.
- Scarab, harlequin and lanternfly: masters byte-identical, photographs pixel-identical.
  Each photograph's TIFF Software tag carries the build id, so the file bytes differ only
  there.

## Q2: never below the system

`strehl_core::optical_restore::design_response` is the one place the target is chosen:
`max(T S/(S+N), H)`, so the gain is at least one below the taper. Flooring the target alone,
`max(T, H) S/(S+N)`, still lowers a band by the Wiener factor. On the scarab's green at 0.4
cycles/px that factor is 0.90, which would deliver 0.24 against a system 0.27 and fail the
gate (DERIVED from the log). D2 picks `sigma_t` within this function.

Log figures, green, system -> restored at 0.3 / 0.4 cycles/px (`q2-gate.txt`; MEASURED):

| Stack | Before (Q1 build) | After (Q2) |
| --- | --- | --- |
| Scarab | 0.43->0.40 / 0.27->0.19 | 0.43->0.43 / 0.27->0.27 |
| Harlequin | 0.44->0.41 / 0.28->0.21 | 0.44->0.44 / 0.28->0.28 |
| Lanternfly | 0.44->0.37 / 0.28->0.15 | 0.44->0.44 / 0.28->0.28 |
| Weevil (stored fit) | 0.45->0.41 / 0.29->0.21 | 0.45->0.45 / 0.29->0.29 |

Red and blue behave the same way: after Q2, restored is at or above system at 0.3 and 0.4 in
every case (the weevil's red at 0.3 reads 0.40->0.41). Before Q2, blue on the lanternfly read 0.49->0.33 and 0.34->0.11. At 0.2 cycles/px the
values are unchanged, because the target asks for more than the lens gives there.

Delivered amplitude over the unrestored render, on the linear masters (`band-gain.py`,
`band-gain.txt`; luminance, the brightest half of 256 px tiles, signal and noise together;
MEASURED). Bands are 0.1-0.2 / 0.2-0.3 / 0.3-0.4 / 0.4-0.5 cycles/px:

| Stack | Before | After |
| --- | --- | --- |
| Scarab | 1.017 / 1.004 / 0.898 / 0.880 | 1.018 / 1.011 / 0.996 / 0.998 |
| Harlequin | 1.095 / 1.031 / 0.881 / 0.705 | 1.097 / 1.036 / 0.993 / 0.992 |
| Lanternfly | 1.089 / 0.988 / 0.777 / 0.513 | 1.093 / 1.015 / 0.996 / 0.992 |
| Weevil | 1.056 / 1.008 / 0.912 / 0.801 | 1.057 / 1.020 / 1.003 / 1.000 |

The residual 0.992-0.998 is the kernel's delivered fraction and the highlight guard, not
the design. With Q2 alone the top bands are left as they are: nothing is lost and nothing is
gained. The lift is D2's (a smaller target sigma within a noise budget).

## Not done

- The weevil's fit failure is not fixed at its cause. The diagnosis above is DERIVED; the
  two-component object model was not tried.
- The scarab's own fit (0.740, residual 0.0278, 50 to 90 times the others') sits on a
  spectral bump at 0.29-0.32 cycles/px (`fit-shape.txt`). Its 0.740 is stored like any
  other fit.
- The desktop check was exercised by a unit test of the parser only. The Stack station was
  not opened.
- The weevil's photograph changes in 159 samples by more than 30,000 of 65,535 with
  restoration on. Those samples sit in red-channel 0/65535 speckle at glints, which the
  unrestored photograph already has. The cause was not investigated.
