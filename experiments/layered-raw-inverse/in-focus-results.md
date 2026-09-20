# Matrix prior passes a separate known-optics in-focus output test

MEASURED, generated data only. This is the prospectively specified alternate
consumer `B(alpha*N + (1-alpha)*F)`, retaining the fixture's supplied in-focus
PSF. It does not reverse any pinhole rejection. Matrix is the only tested arm
passing all fixed image and retained held-RAW checks in both flat and layered
cases. Visibility is still supplied; this is not photographic admission.

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-in-focus-consumer.py --out experiments/layered-raw-inverse/in-focus-2
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/display-in-focus.py --source experiments/layered-raw-inverse/in-focus-2/delivered --out experiments/layered-raw-inverse/display-in-focus-2
```

Commission/delivery/scoring took2.187/1.968/1.969s; no refitting occurred.
Scored receipt SHA256:
`f7df361bcdc2a25a4c1c96118d4b26110ffcdc804adeee4df6477a37da62b873`.
The earlier serialization-only failure is preserved at6f24e3c2; the rerun uses
the existing recursive NumPy-scalar serializer without numerical changes.

| Fixed region, RGB / chroma RMSE in DN | Original Huber | Matrix prior |
| --- | ---: | ---: |
| Flat | 5.020268 / 7.016450 | 5.079854 / 7.095954 |
| Layered whole support | 56.343891 / 44.167648 | 22.787171 / 34.236890 |
| Layered highlight core | 251.453348 / 114.650906 | 65.561851 / 94.199417 |
| Layered filament ridge | 110.208520 / 63.066258 | 34.074979 / 49.659743 |

Flat is slightly worse than Huber but passes both fixed1.05 comparisons.
Layered core/ridge pass strict1.02 paired RGB and chroma comparisons, alongside
absolute observed-mean/far-only and colour-component guards. Matrix glint
projections are[1.001560,1.001411,1.003117], ridge[1.010681,1.001215,1.011988].
Values above one receive no extra credit; projection alone can hide spatial
or colour error, hence the separate error guards. RMSE can reward smoothing,
so the fixed extra-PSF destroyer was commissioned first: glint recovery
falls to0.8967-0.9044 and ridge to0.9224-0.9329, both rejected by0.98. Each
single-colour half-component and the wrong-colour control also reject.

The other arms remain informative failures: original Huber passes the new
image target but retains its bright held-out failure; shot prior fails flat
paired RGB/chroma and layered core chroma; scalar Cauchy fails layered
core/ridge chroma. No best-arm pooling hides these outcomes.

All16 delivered files were independently checked. Full96 arrays are filtered
before the fixed64 support; observed mean and retained donor files are byte
identical to their originals, with no added blur. Donor projections are newly
measured in the optical target domain, but its old pinhole-based source choices
remain fixed and are not an optimal new-target bound. Maximum independent
operator discrepancy is0.00390625DN. Source/output hashes remain unchanged.
Root inspected both complete generated scenes under one fixed display.

The original matrix pinhole colour failure, nonstationary final state, and
failed64-versus1024 pupil adequacy remain. The successful held-out predictions
are unchanged saved predictions, not a new camera validation. The next paired
test removes supplied alpha using the original free-alpha initial states and
the same continuation driver for Huber and matrix. Its delivered consumer is
declared as this in-focus target before fitting; no further output filter is
being proposed for the production stacker's already developed photographs.

Independent interpretation: independent-in-focus-results.md. No default,
real RAW output or SOTA claim changed.
