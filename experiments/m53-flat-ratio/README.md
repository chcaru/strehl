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
| `src/a2_kernel_sweep.py` | the box side chosen on evidence, not taste: contamination vs `w` on both real corpora |
| `src/a3_dump_rois.py` | dumps the 22 real `109MSDCF` flat ROIs so the control runs on real, structured input |
| `src/a3_negative_control.rs` | **the point of the exercise**: plants a noise explosion of known size and scores both statistics against it |

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = 'utf-8'
python src\a1_reconcile.py
python src\a2_kernel_sweep.py
python src\a3_dump_rois.py
cargo run --release --bin a3-negative-control
```

`out/*.f32` (24 MB of decoded ROI) is regenerable and is not committed.

## Result (`out/a3_negative_control.log`)

Truth `K` is the planted noise multiplier, solved from the **calibrated noise
model** — `p = sigma * sqrt(K^2 - 1/n)` — so it comes from neither statistic
under test (rule 35).

| K planted | OLD reports | OLD under-reports by | NEW reports | NEW under-reports by |
| --- | --- | --- | --- | --- |
| 1.000 | 0.990x | 1.010x | 0.973x | 1.028x |
| 2.000 | 1.010x | 1.980x | 1.842x | 1.086x |
| 5.000 | 1.139x | 4.390x | 4.529x | 1.104x |
| 10.000 | 1.513x | 6.610x | 9.036x | 1.107x |
| 22.767 | 2.796x | 8.142x | 20.559x | 1.107x |
| 144.391 | 16.631x | 8.682x | 130.368x | 1.108x |

A **10x** noise explosion reads **1.5x** on the old statistic. The DERIVED
prediction — that each statistic's asymptotic under-report is its own structure
floor, 8.6969x and 1.1074x — is met to 3 decimal places, which is what makes
this a test rather than a description.

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
