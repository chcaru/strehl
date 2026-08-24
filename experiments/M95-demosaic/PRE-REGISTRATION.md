# M95 arm 6 — pre-registration: is the demosaic ladder measuring detail or artifact?

Written before any arm-6 result was computed. Committed alongside the results so
the bars cannot be moved after the fact (rule 12).

## 1. The claim under test

The orchestrator decoded one ARW with six LibRaw demosaics, held tiles and
normalisation fixed, and measured top-octave power spanning **0.3518 dex**:

```
LINEAR  -3.2552      AHD   -3.0058
VNG     -3.0523      DHT   -2.9438
PPG     -3.0457      AAHD  -2.9033
```

From that they infer strehl's Malvar-He-Cutler sits near the VNG/PPG rung,
~0.05 dex below AHD, and that moving to an RCD/AAHD-class demosaic is
**worth up to ~0.15 dex** of sharpness.

That inference rests on a premise the ladder does not test:

> **more top-octave power = better demosaic.**

A demosaic is an interpolator. The orchestrator has already proved, on the
binning question, that an interpolator can *inject* top-octave energy rather
than recover it: `np.kron` block replication produced *more* power near Nyquist
than the full-resolution frame it was built from, which is what made three
successive "binned" anchors cross instead of bracket. Zipper, maze and
false-colour artifacts are top-octave energy that is not in the scene. Whether
the 0.3518 dex is recovered detail or injected artifact is **not determined by
the ladder as measured**.

## 2. Instrument

Ground-truth round trip: build a full-colour image `T`, mosaic it to RGGB,
demosaic it, compare against `T`.

Because `T` is known, the emitted band power decomposes exactly. For
band-limited `D` and `T`, let

```
alpha = <D,T> / <T,T>          D = alpha*T + eps,   <eps,T> = 0
|D|^2 = alpha^2 |T|^2 + |eps|^2
```

- `signal   = alpha^2 |T|^2`  — power correlated with true scene detail
- `artifact = |eps|^2`        — power that is not in the scene at all

Reported in log10-power (dex) relative to truth:

| quantity | definition |
| --- | --- |
| `power` | `log10(P_D / P_T)` — the orchestrator's metric |
| `signal` | `log10(alpha^2)` |
| `artifact` | `log10(P_eps / P_T)` |
| `artifact_share` | `P_eps / P_D` |

A perfect demosaic scores `alpha = 1`, `artifact = 0`, `power = 0`. **No
demosaic can exceed `P_T` in signal.** That ceiling is what the orchestrator's
ladder lacks, and it is the whole reason this arm can separate the two things
their ladder sums together.

### Ground truth `T`

From `DSC00150.ARW` — frame 149, the merge's own reference frame, the same file
the orchestrator measured.

1. rawpy/LibRaw decode at full resolution 7032 x 4688, linear output
   (gamma 1,1), no auto-bright, 16-bit.
2. 2x box-downsample to 3516 x 2344. Demosaic error lives at the top octave of
   the original; averaging over a 2x2 quad suppresses it. The result is
   genuinely three-channel at every pixel with no CFA hole to fill.
3. Mosaic `T` to RGGB at *its own* resolution and run the ladder there, so the
   analysis band is directly comparable to the orchestrator's.

`T` is not perfect — it inherits some of its decoder's error. **K5 is the
control that decides whether that matters.**

## 3. Bars, pre-registered

**B1 — is top-octave power monotone in demosaic quality?**
Run MHC, BILINEAR and NEAREST (deliberately artifact-heavy: replicate each CFA
sample across its quad, the same operation that broke the orchestrator's binned
anchor).

- If **NEAREST reads higher `power` than MHC while reading lower `signal`**,
  then top-octave power is demonstrably non-monotone in demosaic quality and
  the six-algorithm ladder **cannot be read as a quality ranking**. The
  "worth up to ~0.15 dex" inference is unsupported by that evidence.
- If NEAREST reads lower `power` than MHC, the ladder's premise survives this
  test and I say so.

**B2 — how much detail is the shipped MHC actually losing?**

- `signal` deficit vs the ceiling **> 0.10 dex** → real headroom, a demosaic
  upgrade is worth a milestone.
- `signal` deficit **< 0.03 dex** → negligible headroom, the upgrade is not
  worth it and I will say so plainly.
- Between the two → report the number, make no recommendation.

**B3 — weak consistency check (not a decision bar).**
Arm 4/5 measured strehl MHC vs rawpy AHD on the *real* render at
**-0.0332 dex**. Arm 6 measures a *synthetic* quantity, so these are not the
same number and I will not treat agreement as confirmation. If they disagree by
more than 0.10 dex I will say that one of them is suspect rather than quietly
prefer the newer one.

**B4 — admissibility.** If K1 reads `artifact != 0` beyond float epsilon, or K3
is non-monotone, or K6 fails, the instrument is inadmissible and this arm
reports **nothing quantitative**.

## 4. Controls, pre-registered

| id | kind | what it does | pass condition |
| --- | --- | --- | --- |
| K1 | NULL | feed `T` itself in as `D` | `alpha = 1`, `artifact` at float epsilon, `power = 0.0000` |
| K2 | NULL | run the same algorithm twice | bitwise identical |
| K3 | POSITIVE (dose) | blur `T` by sigma in {0, 0.5, 1.0, 2.0} px before mosaicking | `signal` falls monotonically |
| K4 | POSITIVE (dose) | add a checkerboard zipper of amplitude {0, 0.002, 0.005, 0.01} to a demosaic output | `artifact` rises monotonically, `signal` ~flat |
| K5 | SPECIFICITY | rebuild `T` from VNG and from LINEAR decodes | arm *ranking* preserved; MHC deficit moves less than the effect it measures |
| K6 | CERTIFICATION | Python MHC vs `strehl_core::demosaic` via `m95-demosaic.exe` | agreement to float epsilon |
| K7 | BAND | analysis band vs `T`'s Nyquist | band strictly below 0.5 cyc/px |

**K4 is the control the whole arm rests on.** It is the one that shows the
instrument can say "this power is not scene detail". Without it, B1 is an
assertion.

**K6 is what makes a Python measurement admissible evidence about Rust.**
A reimplementation says nothing about the shipped demosaic until it is shown to
agree with the shipped demosaic.

**K7 is the arm-5 lesson.** `x10c` was withdrawn because its band sat above the
plane Nyquist and it was measuring aliasing while all its other controls passed.

## 5. What would falsify the conclusion

- If NEAREST reads both lower power and lower signal, B1 fails and the
  orchestrator's ladder reading stands.
- If K5 flips the ranking, `T` is contaminated by its own decoder and every
  number here is withdrawn.
- If K6 fails, the Python arm describes something other than what strehl ships.
- If MHC's deficit is large *and* mostly signal, then the demosaic upgrade is
  real and I should say so even though it is more work than reporting a null.

## 6. Scope declared in advance

This arm measures a **synthetic** round trip on one frame's worth of scene
content. It does not measure the real merge output, it does not measure any
algorithm strehl does not ship (no AAHD, DHT, RCD or DDFAPD implementation is
written or read here — `AGENTS.md` bars the GPL sources and none were opened),
and it cannot say what an unimplemented demosaic would score. What it *can* do
is bound the ceiling: no demosaic, however good, can recover more than `T`.
