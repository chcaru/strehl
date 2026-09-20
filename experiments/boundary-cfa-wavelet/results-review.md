# Independent decision after the boundary/rounded-gather screen

**VERIFIED from root's retained run: frozen promotion rule fails. This does
not show that the candidate is generally worse than the baseline.** No test,
render or RAW decode was executed by this reviewer. Reviewed bound source,
process records and all12 cases in controls-1/output/screen.json,
SHA2567519410caf5ec14f87357160a0be401edc75ab78d6bf1c6cf4a8f255ebe1adf5.
Build2 compiled after two plumbing-only corrections: local QuadSource import
and bytewise hash formatting. Final controls hash is
0bc076751d0caca7cbda2c15514094c71509fdb9762d57493903d9f94de8631f;
bridge7bc766e727270ed2f2fec947117d1b629dc6c932a7098e545025d8184ca27b45.
Root ran build-2/cli-tests.exe with the independent_controls filter; both
mechanical tests passed, while screen.json correctly records admission=false.

| Fixed case | Identity candidate/baseline RGB RMSE | Fractional candidate/baseline RGB RMSE |
| --- | --- | --- |
| Flat |0.83766–0.83781|1.00914–1.01246|
| Weak red |0.91738–0.91769|0.97159–0.97209|
| Coarse corner/edge |0.93905–0.94641|0.97838–0.98238|

All six identity cases pass. The fractional weak-red source2 recovers
0.53835–0.53844 of true amplitude; candidate recovers0.47765–0.47777,
or88.726–88.733% of that source, below the frozen90% bar. The miss is about
1.27 percentage points. Yet the baseline recovers only0.18517–0.18531:
candidate recovery is about2.58 times baseline. Every baseline RGB,
boundary-strip and corner non-regression guard passes; coarse true amplitude
is0.846–0.850 and its new deep bands are active. Fractional flat and weak-red
RMSE gains do not meet the separate5% benefit rule. Do not relabel either
failure as a pass. Fractional coarse chroma RMSE rises1.052–1.119 times
baseline despite lower RGB error; no separate structured-chroma bar was
preregistered, so preserve that observation rather than inventing one now.

The floor and addressing checks retain useful implementation evidence.
Literal four-state covariance, active-origin/CFA routing, reflection/complete
packing and actual known4 gather checks passed. The actual8-pair pooled floor
is1.00477/1.00530 of the independent64-realization reference for
identity/fractional. Individual deep-band uncertainty remains large: this
does not certify every coefficient floor. Diagnostic on/off baseline and
candidate RGB hashes and all eight collapsed planes are exact. The known
three-band baseline versus seven-level candidate distinction remains explicit.

## Next choice

**ARGUED: retain this exact algorithm for one separately authorized,
resource-capped observational full photographic pair before modifying its
weights around this single46/256 carrier.** The absolute source-retention bar
usefully exposes loss that a poor baseline hides; it should continue to block
promotion. It is not a theorem forbidding observation of another stimulus.
Such a run would be a new exploratory scope, with the failed screen intact,
not a passed gate or permission to ship. Require a whole-image baseline pair,
fixed native targets and independent inspection of detail/chroma/background.
First establish cost and bounded memory: full vitamin-C padding becomes
4096x4096, each four-plane complex field is0.5GiB, and the method requires
16 additional gather/transform evaluations per source. The small timings
cannot justify extrapolating a practical full-stack runtime.

WB-weighted noise dilution is possible, but not established as this failure's
cause. With per-plane smoothed E,V and WB gains g, the current E/V equals
sum(g²V*(E/V))/sum(g²V): it is a variance-weighted average of channel evidence.
A high-noise constant blue channel can therefore pull useful red evidence
toward the noise value. WB scaling is internally consistent; this is a choice
of shared evidence, not proof of double-WB or a calibration error. The saved
screen lacks the necessary per-plane source-weight attribution to convict it.

If a later algorithm change is warranted, one bounded alternative is
sum_c smooth(E_c)/smooth(V_c), with floor4 times the existing gate, the same
single shared tuple weight and all other settings fixed. This equalizes
per-plane noise units without picking the strongest colour. It is not full
covariance whitening. Reciprocal estimated floors can amplify eight-pair
Monte Carlo error and false selection; unchanged flat and weak-colour bars
must be able to reject it. No floor epsilon, gate change, extra probes or
WB adjustment is licensed by this review. This alternative is deferred;
the current evidence favors a different stimulus before another weight tweak.
