# Free visibility still fails the fixed image requirements

MEASURED, generated data only. The matrix prior passes every prescribed
same-budget comparison with free-alpha Huber and passes the far-only case,
but does not retain its known-visibility quality. Flat and layered requirements
fail. The method is not admitted for photographic use.

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-free-visibility.py --out experiments/layered-raw-inverse/free-visibility-1
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/display-free-visibility.py --source experiments/layered-raw-inverse/free-visibility-1/output --out experiments/layered-raw-inverse/display-free-visibility-1
```

Commission/eight fits/scoring took2.157/223.359/3.110s. Fit-process peak job
committed memory was2,785,828,864bytes, not RSS or a workflow benchmark.
Score SHA256:
`e7f0815720f33d308cb98bf3cbb69f65dd0b806a1af8eb57328dfaea32db16d4`.
All inputs and output hashes passed the immutable-source checks.

| In-focus output, RGB / chroma RMSE in DN | Free Huber | Free matrix |
| --- | ---: | ---: |
| Flat whole support | 16.679542 / 25.169358 | 16.895946 / 25.650109 |
| Layered whole support | 74.140300 / 64.308410 | 62.622611 / 44.582965 |
| Layered highlight core | 311.654337 / 162.008812 | 275.781630 / 112.210448 |
| Layered filament ridge | 144.861078 / 108.280938 | 123.017598 / 73.088384 |
| Far-only whole support | 74.443591 / 33.602490 | 53.724057 / 11.624160 |

Flat fails both observed-mean6.018455/8.367617 and fixed-alpha
visibility5.020268/7.016450 comparisons. Its held-RAW normalized RMS still
passes at1.00203/1.02165. Thus prediction success alone does not protect the
delivered colour image. These are spatial errors against known truth, not
temporal sensor-noise measurements. No causal attribution to opacity or CFA
aliasing follows from this comparison alone.

Layered matrix passes its matched free-Huber comparisons, all component
guards and held-RAW checks, including bright-stratum1.21829 versus Huber2.45262.
It fails the stricter retained fixed-alpha reference for core RGB, ridge RGB
and ridge chroma (reference251.45335,110.20852,63.06626 respectively). The
successful known-alpha matrix result therefore has not transferred to free
visibility. RGB error can reward blur and component projection can hide
correlated error; both were protected by the previously commissioned detail
destroyers and separate colour guards, not by likelihood alone.

Far-only matrix passes the specified image, component and held bars using
the correct historical single-depth comparator; bright held RMS is1.25543
versus free-Huber2.98373. This rejects neither all free-visibility inference
nor the entire matrix family. Angular mismatch retains bright failure2.62609
even though global RMS passes. Since matched cases also fail qualification,
this is not a selective adequacy gate and no automatic gate is implemented.

All eight fits reach1000 iterations and remain nonstationary. This is the
result of the fixed continuation recipe, not a global optimum or impossibility
claim. Root inspected all four complete generated scenes. Original pinhole
verdicts, unresolved64/1024 pupil accuracy, known depths/optics and the exact
visibility/radiance gauge remain. No duration, coefficient or parameterization
rescue follows from this run. The separately commissioned joint-pupil GPU
kernel addresses the known integration error; it does not itself solve this
free-visibility failure. Independent review: independent-free-visibility-results.md.
