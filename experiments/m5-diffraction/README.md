# m5-diffraction — measuring the diffraction cutoff from raw CFA sublattices

Measures the frequency `f_c` at which the optical transfer function of the
reference rig reaches its hard zero, and from it the bellows factor

    B = (1 + m/p) = pitch / (lambda * f_c * N_marked)

Everything runs on **single-colour CFA sublattices** taken straight out of the
raw Bayer array. Nothing here is demosaiced; demosaicing both invents and
destroys the high-frequency content this experiment lives on.

Read `docs/research/M5-diffraction-measured.md` for the result. This file is
only about running the code.

## Files

| File | What it is |
| --- | --- |
| `m5_lib.py` | The estimator. Sensor geometry, lattice extraction, Welch periodogram, radial averaging, the knee rules, the noise model. Everything else is a driver. |
| `m5_selftest.py` | Unit-level proofs: the frequency axis, the periodogram normalisation, the false-alarm rate. Run this first. |
| `m5_synthetic.py` | **C1** and **C1b**, the positive controls. Recovers a cutoff that was planted by hand. |
| `m5_measure.py` | The primary measurement plus **C2** (null), **C3**, **C4**, **C5** and the H4 noise cross-check. |

## Run it in this order

Nothing downstream is worth reading until the step above it passes.

```powershell
cd experiments\m5-diffraction

# 0. Does the estimator's arithmetic hold up at all?
python m5_selftest.py

# 1. C1 — can it recover a cutoff we planted ourselves? (~110 s)
python m5_synthetic.py

#    C1b — the same on real texture with a planted extra cutoff (~45 s).
#    --quick shortens the synthetic sweep that runs ahead of it.
python m5_synthetic.py --quick --real-crop C:\dev\macro\test\109MSDCF\DSC00018.ARW
python m5_synthetic.py --quick --real-crop C:\dev\macro\test\109MSDCF\DSC00009.ARW

# 2. C2 — the null control. Pure noise must not produce a cutoff. (~5 min)
python m5_measure.py null D:\macro-dark-frames --tile 128

# 3. The measurement itself. One command per aperture.
python m5_measure.py measure C:\dev\macro\test\109MSDCF   --n 11.0 --tile 128 --dark D:\macro-dark-frames\123MSDCF
python m5_measure.py measure C:\dev\macro\test\coffee-bean --n 8.0 --tile 128 --dark D:\macro-dark-frames\122MSDCF
python m5_measure.py measure C:\dev\macro\test\119MSDCF   --n 5.6 --tile 128 --dark D:\macro-dark-frames\122MSDCF
```

`--dark` supplies a matched-ISO dark folder so the fixed-pattern-noise
contamination of the knee can be measured and subtracted (C2b). ISO 50 stacks
take `122MSDCF`; the ISO 160 stack takes `123MSDCF` (ISO 200, the nearest
available above it — deliberately the conservative direction).

Useful extras:

```powershell
# audit every EXIF tag across a stack, per-value counts
python m5_measure.py exif C:\dev\macro\test\coffee-bean

# print the actual radial spectrum, so the shape can be looked at rather than
# trusted through a fitted number. This is how the f/8 "no reachable floor"
# finding was established.
python m5_measure.py dump C:\dev\macro\test\coffee-bean --at centre --lattice GQ --tile 128
```

Options: `--roi` (ROI edge in lattice samples, default 512), `--tile` (Welch
tile, default 256; the measurement uses 128), `--sector` (`iso` or `hv15`),
`--windows` (comma separated, from `hann,kaiser8,none`), `--limit` (first N
frames, for smoke tests only — a truncated focus bracket has no sharp frame).

## The three lattices

`G1` and `G2` are the two green sublattices, `raw[0::2, 1::2]` and
`raw[1::2, 0::2]`. Each has pitch `2 x 5.12 = 10.24 um`, so each reaches only
**0.25 sensor cyc/px** — half the sensor's own Nyquist. Carrying that factor of
2 correctly is the single easiest way to be confidently wrong by exactly the
amount that separates the two candidate answers, so `m5_selftest.py` plants a
sinusoid at a known *sensor* frequency and asserts that all three lattices put
it in the same radial bin.

`GQ` is an **extension beyond the prescribed method**: both greens on their true
quincunx lattice, re-indexed onto a 45-degree-rotated square grid by
`B[u,v] = A[u+v, u-v+1]`. Pitch `sqrt(2) x 5.12 = 7.2408 um`, reach **0.3536
sensor cyc/px**. It uses exactly the same photosites and interpolates nothing.
It exists because all three of the brief's `p=1` predictions lie above 0.25, so
G1 and G2 alone could only ever have returned bounds.

## Things the code deliberately does not do

- It never averages pixel values across frames. Periodograms from different
  frames are averaged, which is a different and legitimate operation.
- It never uses a boxcar window for a result. `--windows none` exists only to
  reproduce the Trap 2 control, which shows a boxcar inventing a
  cutoff-independent fake knee.
- It never reports a model-fit cutoff that the fit placed above the lattice
  reach; those are extrapolations outside the data and are suppressed.
- It does not tune anything per stack. `Z_DETECT`, `RUN_LEN`, `DYN_GATE`,
  `F_LO_ABS` and the ROI positions are fixed in the source and identical for
  the synthetic control, the dark frames and all three stacks.
