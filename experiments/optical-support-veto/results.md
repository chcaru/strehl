# Optical-support veto: generated screen unexercised, no photographic admission

MEASURED September25 by root; pipeline_audit authored the adapter and fixture,
mineral_diagnosis authored independent support checks and scoring. The actual
native consumer and all mechanical controls execute successfully. The proposed
quality intervention earns no admission.

Independent continuous-pupil surface ownership agrees with the prepared support
flags, including the shared ray for foreground visibility and background light.
Shifted support is rejected. The fresh build compiles both strehl-core and
strehl-cli. Both actual Rust tests pass. Actual rounded GPU gather equals the
known original CFA sites; the injected ISO100 profile supplies noise. Independent
clamped-index calculations match the exported reduce/expand support matrices
including odd sizes and borders, and match every resulting Q mask.

Current, all-one Q and the all-no-clean fallback have identical complete CFA
and linear RGB outputs. Flat and transparent scenes remain byte-identical under
the oracle and permuted masks too. The unchanged mean base, unweighted fallback,
input bounds and per-source data are explicitly checked. These are operator and
null controls, not a new sensor calibration or photographic-quality result.

The registered bright-spill positive is absent. Fourteen coefficients in the
outside window have both contaminated positive source weight and a clean positive
alternative, but Current's mean luma error there is **negative**-0.00143947045.
The required positive excess was twice the flat residual RMS,0.00189020170.
The status is therefore **UNEXERCISED**, not successful removal of a bright veil.
No window, contrast, geometry, threshold or source ordering is retuned.

Secondary recorded damage also argues against a photographic trial of this exact
hard veto. Outside RGB RMS rises0.00478355819→0.02359497361; chroma RMS
rises0.00462656794→0.01764753833. The near region is unchanged and passes;
the far-region protection fails. The fixed source-permuted control also fails
far-region protection while preserving the near region. These are normalized linear camera-RGB
truth errors on the fixed generated scene, not real-photo improvements. They
cannot establish that all visibility-aware reconstruction is futile.

The protection metric first accepts Current compared with itself, then rejects
the blurred, grey and overcontrast destroyers. It can reject loss/exaggeration
of the supplied component patterns; on photographs without truth it would not
establish genuine detail. Both near/far amplitudes are jointly fit, and are
reported uncapped alongside RGB/chroma errors. Complete generated images and
linear arrays are retained, but no generated image substitutes for the user's
required complete photographic stack output.

Actual commands, with the retained Python312 interpreter and -I -B
-X faulthandler:

```
experiments/optical-support-veto/run.py prepare --out experiments/optical-support-veto/prepare-1
experiments/optical-support-veto/run.py build --out experiments/optical-support-veto/build-1
experiments/optical-support-veto/run.py consume --prepare experiments/optical-support-veto/prepare-1 --build experiments/optical-support-veto/build-1 --out experiments/optical-support-veto/consume-1
experiments/optical-support-veto/independent-controls.py --prepared experiments/optical-support-veto/prepare-1/output --consumed experiments/optical-support-veto/consume-1/output --out experiments/optical-support-veto/score-1.json
```

Retained commands, source/input/executable bindings, limits and terminal job
accounting accompany each phase. Preparation takes8.922s, fresh compilation
202.485s and actual consumer1.250s; these overlap unrelated work and are
operational observations, not comparative speed claims. Zero photographic RAW
files are decoded. Only the fixed96x96 generated inputs and complete64x64
outputs are used, giving two AC bands rather than the seven-band real stack.

Decision: no photographic replay, visibility detector, strength sweep or default
change follows. The missing positive and measured harm remain recorded. The
mean-base garnet counterfactual is separately closed in
`../base-band-transfer/independent-results.md`; neither experiment attributes the
remaining real broad haze to a single established cause.
