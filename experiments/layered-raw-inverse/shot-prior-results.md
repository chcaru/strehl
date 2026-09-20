# Shot-noise-scaled radiance prior: mixed, rejected

MEASURED on the generated original-CFA flat/layered cases, with supplied true
visibility. This is not a photographic improvement or a SOTA result. The fixed
combined screen fails. Preserve this run; do not tune its coefficient.

Command run from the repository:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-shot-noise-prior.py --out experiments/layered-raw-inverse/shot-prior-1
```

The wrapper commissions the operator first, performs exactly two fits, then
runs the independent scorer. Recorded wall times are 2.000, 20.766 and 2.406s;
peak fitting job committed memory is 2,771,189,760 bytes. These are execution
receipts, not speed benchmarks. Scored-result SHA256:
`b90831f884314111c2ede55132987f4e9a5cc0c8bc264c7b5935f95cb56336a2`.
All bound inputs and original results remain unchanged.

Only the radiance sheet prior changes. Its cancellation-safe square-root
coordinate differences use the injected gain/read variance, with the denominator
derivative retained. It matches the original small-gradient scale at2048DN.
Same original160 starting sheets, same fixed truth alpha, original likelihood,
CFA, 64-ray optics, censoring, seven training frames, held frames2/6, remaining
penalties and optimizer settings. Reference is the retained visibility-1 result.

| Returned image / prediction | Original prior | Shot-noise prior | Meaning |
|---|---:|---:|---|
| Flat RGB truth RMSE, DN | 5.672017 | 6.338638 | Fails both mean and paired bars |
| Flat chroma truth RMSE, DN | 7.925566 | 9.126434 | Fails both mean and paired bars |
| Layered interior RGB RMSE, DN | 150.971384 | 149.691452 | Small reduction, not uniform colour improvement |
| Layered core RGB RMSE, DN | 731.456906 | 728.592381 | Small reduction |
| Layered core chroma RMSE, DN | 260.393167 | 274.173108 | Worsens; not guarded by paired RGB alone |
| Layered ridge RGB RMSE, DN | 312.403505 | 310.605421 | Small reduction |
| Held bright41-sample RMS, injected-noise units | 2.147807 | 1.468595 | Passes fixed1.75 bar |

The mean flat reference remains6.018455RGB/8.367617chroma; the allowed factor
is1.05. Mean signed flat errors are only[0.1174,-0.2438,-0.0393]DN, close to
the original prior. The returned flat failure is therefore not explained by
the commissioned common-brightness bias risk. Wider error tails, particularly
R/G, accompany the higher RMSE. These are spatial truth errors, not estimates
of temporal sensor noise.

Layered glint component recoveries are[0.98519,0.96849,0.98546], against
[0.96153,0.95335,0.96398] before. Ridge-detail recoveries are
[0.95692,0.99168,0.98969]. They remain below unity, so these increases do not
reward amplitude overshoot. All existing absolute and paired layered bars and
all held predictions pass. Component scores can still conceal shape/colour
errors: the core chroma increase is the concrete counterexample here. Global
held RMS alone would have concealed the previous bright-stratum failure.

Commissioning compares the actual helper with independently evaluated literal
transformed coordinates and finite differences. The reference-scale ratio is
0.99997584. A1000DN common offset reduces the commissioned textured-field prior
from7.42100 to5.16457; its live brightness derivative is-0.001482924, matching
independent finite differences. This is a property of the image penalty alone,
not a claim about the total objective or observed final brightness.

Neither fit meets the raw-parameter gradient threshold1e-6. Flat returns after
116 iterations/128 actual evaluations at max8.9188e-6; layered after500/507 at
1.9679e-4. The returned-state observations remain useful, but do not establish
converged optima. Cross-prior total-objective values are not a quality ranking.

Independent interpretation: independent-shot-noise-prior-results.md. Source
and review bindings are in shot-prior-1/sources.json. No default changed, no
truth-alpha estimator exists, and the continuum-pupil adequacy failure remains.
