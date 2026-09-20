# Original-scale Cauchy radiance prior: colour failure

MEASURED / independently reviewed. The fixed known-visibility experiment fails.
The new core/ridge colour guards catch a substantial regression that pooled
RGB error, near-unit component recovery and held-out RAW prediction all miss.
No real photograph, default change or pass-gated stress test is admitted.

Command run:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-cauchy-prior.py --out experiments/layered-raw-inverse/cauchy-1
```

Commissioning/fitting/scoring take2.000/35.656/2.360s; peak fitting job committed
memory is2,772,217,856 bytes. These receipts are not speed benchmarks. Scored
result SHA256 is
`2ea54d4ce819a1a5cb9af23d4a3463d28f1ddc0db4a1579d784896f5ce8450c8`.
All source/reference/checkpoint/alpha bindings remain unchanged. Both fits use
the exact original160 sheets and supplied visibility as visibility-1; original
likelihood, optics, noise, CFA, censoring, other penalties and solver are fixed.

The only change is the vector sheet-gradient loss:
`rho(s)=2*log1p(s²/4)`, at the original fixed2048DN noise-derived scale.
Commissioned zero curvature is0.99999988 for both Cauchy and original Huber.
Finite edges are not equivalent. An isolated strong RGB impulse has only
0.1230769 of Huber's restoring force, explicitly commissioning the risk that
false structure can persist. Brightness translation leaves this image term
unchanged; this does not apply to the separate radiance L2 penalty.

| Fixed measurement | Original Huber, visibility-1 | Cauchy | Decision |
|---|---:|---:|---|
| Flat RGB/chroma RMSE, DN | 5.672017 / 7.925566 | 5.734541 / 8.011089 | Both fixed allowances pass |
| Layered interior RGB/chroma RMSE, DN | 150.971384 / 67.309896 | 121.755868 / 131.312300 | Less RGB error, much more colour error |
| Core RGB/chroma RMSE, DN | 731.456906 / 260.393167 | 566.931016 / 558.193564 | Chroma guard fails |
| Ridge RGB/chroma RMSE, DN | 312.403505 / 120.163530 | 246.086762 / 252.519871 | Chroma guard fails |
| Held bright41-sample RMS, supplied-noise units | 2.147807 | 1.158371 | Fixed1.75 bar passes |

Flat also beats the retained mean6.018455RGB/8.367617chroma, but is slightly
worse than visibility-1. Its mean signed errors remain small. These spatial
truth errors are not temporal sensor-noise measurements.

Glint projections are[0.993789,1.001343,0.996124]; filament projections are
[1.019187,1.013063,1.018573]. Protection uses truth-capped recovery, so values
above one earn no extra-detail credit. A nearly correct projection can conceal
spatial error orthogonal to its template. Here the RGB colour differences are
much less accurate despite those projections and noise-like held predictions.
No spatial cause or CFA alias mechanism is established by this screen alone.

Flat returns after170 iterations/184 actual evaluations at max parameter
gradient6.85e-6. Layered reaches1000/1047 at0.02446 with continuing late changes.
Neither meets1e-6. This rejects the prescribed returned output, not a proved
global optimum of the prior family. No longer continuation or coefficient
rescue is commissioned. Unknown visibility and continuum-pupil adequacy remain.

Independent interpretation: independent-cauchy-prior-results.md. The separate
visibility-update-design.md records an algebraic opacity/radiance ambiguity,
independently checked against the forward: it preserves the pinhole image and
does not itself explain the failed composite output. The priors are not
invariant to that ambiguity.

Full generated-scene inspection, not a photographic comparison:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/display-priors.py --out experiments/layered-raw-inverse/display-priors-1
```

The contact sheet shows all96x96 pixels under one fixed asinh display, with
the supported scoring domain marked. It is retained for inspection; the
numerical colour rejection is not waived by its modest display appearance.
