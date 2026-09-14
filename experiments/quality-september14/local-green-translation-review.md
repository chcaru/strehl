# Independent registrar review

VERIFIED by reading `local-green-translation.py` at SHA256 `5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196` and its executed `local-green-translation-1/result.json`; the verifier did not rerun the registrar.

No blocking implementation issue was found. The guide consumes measured green sites using actual source-origin CFA parity. The existing reference-to-source similarity maps native coordinates with `2*b_plane`, then adds the fitted displacement in source-native pixels. Image guides remain f32; fitting coordinates and profiled gain/bias are f64. Finite differences use an absolute .02-native step. Left and right raw support are disjoint after allowing Gaussian radius6, search4, finite-difference .02 and interpolation1; the smallest resulting separation is 3.853 native pixels.

Both delta-zero and shifted arms fit their own gain/bias on the left, and apply those unchanged to the right. Thus improvement is not merely from giving only the shifted arm photometric nuisance parameters. All reported gains are positive.

The continuous-field controls use a nonidentity similarity map and deliberately unrelated R/B sites. Measured displacement error is .000777 native pixel with equal focus and .000459 with mild additional blur; the blur-only case invents a .000438-native displacement. Wrong-sign controls worsen right-side prediction. These discharge the fixed .05-native recovery bars. The blur attenuation is defined in reference/world coordinates; effective source-native sigma is `abs(a)*.45`, not exactly .45.

All eight nonreference real-frame corrections reduce right-side guide RMSE, to .493–.702 of each arm's own nuisance-adjusted uncorrected reading. Displacements vary coherently across the nine-frame window. Frame145 reaches the y=-4 source-native search boundary; no optimum beyond that bound was established. Reference149's identity check is arithmetic, not independent geometric evidence.

These results justify one reconstruction with only the source-coordinate deltas changed. Original CFA values and injected noise should remain untouched. In the inverse observation coordinates consumed by reconstruction, the change is `-delta_source/a` in native reference149 coordinates. This tests whether the measured local prediction improvement produces better photographs.

The remaining right-side guide RMSE is about .015–.060. Mild-blur controls cannot establish equal PSFs on real frames, and lower low-pass guide error is not a sharp-detail verdict. Differential blur, local scene changes and other model mismatch remain possible explanations for residuals. The proposed second discriminator in `joint-photographic-verdict.md` remains unexecuted.
