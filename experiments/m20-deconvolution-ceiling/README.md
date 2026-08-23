# M20 — deconvolution ceiling: scripts

Run order. Python 3 + numpy/scipy/rawpy/exifread.

| script | produces |
| --- | --- |
| optgate.py   | the gate: reproduces facts 12 / 27 / 28 from the optics model |
| wiener2.py   | estimator algebra, three independent routes + positive control |
| wiener3.py   | multi-frame gain across frequency; first (superseded) aperture model |
| wiener6.py   | depth-model comparison (ramp / slabs / single plane), guarded variant |
| wiener7.py   | guard-constant sweep, prior sensitivity, noise-immune detail metric |
| wiener8.py   | data-estimated priors — the implementable case |
| contrast2.py | real 109MSDCF best-frame local SNR distribution (reads ARW, read-only) |
| robust.py    | crossover-calibration robustness sweep (needs contrast2.py's .npy) |

wiener3.py section 5 is SUPERSEDED by wiener6/§7 of the report: it scaled blur-per-step with
aperture, which is wrong. Blur-per-step in pixels is aperture-invariant. Kept for the record.

Verifiers: re-derive, do not re-run. These are the author's own scripts and share the author's
assumptions.
