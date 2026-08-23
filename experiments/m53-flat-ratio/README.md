# M53 — replacing ACCEPTANCE INVARIANT 1's flat-ROI statistic

Invariant 1 was `stacked_sigma / single_sigma`: two **raw spatial** sds over a
"flat" ROI, with the denominator supplied by one arbitrarily chosen frame. It
had two independent defects and a fix for either alone is not a fix.

1. **Structure-dominated** (facts 469, 442, 455). On `109MSDCF`'s flat ROI the
   raw spatial sd is 76.272 DN against a modelled 8.770 DN, so ~99 % of the
   variance is scene. Fact 469 measured the ratio under-reporting a real noise
   explosion by 6.3x.
2. **One privileged denominator frame** (fact 441). Sweeping which frame
   supplies it, merge held fixed, moves the published number over a 1.60x range.

The replacement lives in `crates/strehl-core/src/flat_ratio.rs`: a `9x9` box
high-pass residual sd (`x - box9(x)` on the ROI's valid interior) referenced to
the **distribution over every frame** — median with the full min–max range
printed beside it. Its white-noise gain is `sqrt(1 - 1/81) = 0.993808`
(DERIVED, and tested), so the sd reads against the calibrated noise model.

## Steps

| script | what it establishes |
| --- | --- |
| `src/a1_reconcile.py` | the shipped kernel **is** M41's, the one behind fact 469: reproduces its published 11.770 DN to 0.0038 % |
| `src/a2_kernel_sweep.py` | the box side chosen on evidence, not taste: contamination vs `w` on both real corpora, at M41's gain **and** the shipped post-fact-550 gain |
| `src/a3_dump_rois.py` | dumps the real flat ROIs of `109MSDCF` (ISO 160) and `119MSDCF` (ISO 50) so the control runs on real, structured input |
| `src/a3_negative_control.rs` | **the point of the exercise**: plants a noise explosion of known size and scores both statistics against it, in two arms |

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = 'utf-8'
python src\a1_reconcile.py
python src\a2_kernel_sweep.py
python src\a3_dump_rois.py
cargo run --release --bin a3-negative-control
```

`out/*.f32` (58 MB of decoded ROI) is regenerable and is not committed.

## The control has two arms, and that is because of fact 599

SYNTHESIS fact 599: M40's null plant and M41's `noise_constant_check` each drew
their noise from the gain constant `g` and normalised by a sigma computed from
the **same** `g`. Both were scale-invariant in `g` to ~0.05 % and both passed
confidently through twelve milestones during which that constant was a factor of
two wrong. **A plant that supplies its own noise constant is structurally blind
to that constant being wrong.**

That trap partly applies here and the control says so out loud. What saves it
from being M40's mistake is that **the statistic under test is itself
sigma-free**: `hp(merged) / median_i hp(frame_i)` contains no calibrated
constant. Only the *labelling* of the plant needs one.

### ARM 1 — sigma-free. This is the arm that carries the milestone.

The plant is a size in DN this program picks. The predictions come from the
**measured** un-planted sds plus the **derived** kernel gain, and nothing else.
`109MSDCF`, plant sweeping over 512x:

| plant p DN | hp measured | hp predicted | err | raw measured | raw predicted | err |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 3.9568 | 3.9568 | −0.00 % | 75.0288 | 75.0288 | 0.00 % |
| 20.0 | 20.2637 | 20.2662 | −0.01 % | 77.6452 | 77.6487 | −0.00 % |
| 200.0 | 198.7775 | 198.8010 | −0.01 % | 213.5930 | 213.6102 | −0.01 % |
| 2560.0 | 2543.8538 | 2544.1515 | −0.01 % | 2561.0162 | 2561.0992 | −0.00 % |

**Separation — how many times more explosion NEW reports than OLD. No sigma in it:**

| stack | ISO | predicted `g·raw_mid/hp_med` | measured | apart |
| --- | ---: | ---: | ---: | ---: |
| `109MSDCF` | 160 | 7.8531x | 7.8491x | −0.051 % |
| `119MSDCF` | 50 | 12.0815x | 12.0649x | −0.137 % |

The content is that `hp(planted)/raw(planted) → g` on a **real structured ROI**:
measured 0.993299 and 0.992444 against the derived 0.993808.

### ARM 2 — sigma-scaled. What a reader wants, disclosed as partly circular.

`K` is the true noise multiplier against one unstacked frame, so the plant is
`p = sigma·sqrt(K² − 1/n)` and the calibrated sigma enters. `109MSDCF`:

| K planted | OLD reports | NEW reports | NEW `[lo .. hi]` |
| ---: | ---: | ---: | --- |
| 1.000 | 0.990x | 0.973x | `[0.775 .. 1.051]` |
| 2.000 | 1.010x | 1.842x | `[1.466 .. 1.991]` |
| 5.000 | 1.139x | 4.529x | `[3.606 .. 4.896]` |
| 10.000 | **1.513x** | **9.036x** | `[7.195 .. 9.768]` |
| 22.767 | 2.796x | 20.559x | `[16.371 .. 22.224]` |
| 144.391 | 16.631x | 130.368x | `[103.810 .. 140.925]` |

A **10x** noise explosion reads **1.5x** on the old statistic.

**The "under-reports by" columns are an algebraic identity, not a test.** Since
`p ∝ sigma`, as `K` grows `K/OLD → raw_mid/sigma` and `K/NEW → hp_med/(g·sigma)`
— the same expressions the "prediction" is computed from. An earlier version of
this README claimed the prediction was "met to three decimal places". That was
arithmetic and the claim is withdrawn. Their **ratio**, 7.8531x, is arm 1's
separation with sigma cancelled out, and that one is real.

## Why two stacks

`109MSDCF` is ISO 160, a true gain step untouched by fact 550. `119MSDCF` is
ISO 50, an extended ISO whose gain that fact doubled. **Arm 1 behaves identically
on both** (quadrature within 0.02 %, separation within 0.14 %). **Arm 2 does
not** — `K/OLD` reads 8.6969x on one and 13.4699x on the other. That is the
pairing M47 used to save facts 461/479, and it shows directly which columns rest
on the constant.

## The unplanted finding

On the shipped pipeline, real frames, no plant at all
(`out/a5_stack.log`, `out/a4_after.log`):

| operator | LEGACY raw ratio | NEW hp ratio |
| --- | --- | --- |
| `strehl stack`, unregularised argmax | 0.985x | **1.208x** `[0.962 .. 1.306]` |
| `strehl merge --gate 2.0`, regularised | 0.997x | **0.980x** `[0.780 .. 1.059]` |

The legacy statistic ranks unregularised argmax as the **better** of the two and
calls a 21 % noise increase a pass. The replacement separates them by 23 % and
in the right direction.
