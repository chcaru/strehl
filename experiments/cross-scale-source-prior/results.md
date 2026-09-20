# General replacement rejected by the fixed screen

MEASURED: the fresh CLI/core build completes in191.171s and the two independent
tests complete in2.907s. All12 case receipts exist and source bindings survive.
The explicit photographic qualification is **false** at both ISO100 and400.
Passing Rust tests here means the measuring code ran, not image-quality success.

```text
python -I -B -X faulthandler experiments/cross-scale-source-prior/run.py build --out experiments/cross-scale-source-prior/build-1
python -I -B -X faulthandler experiments/cross-scale-source-prior/run.py controls --build experiments/cross-scale-source-prior/build-1 --out experiments/cross-scale-source-prior/controls-1
```

MEASURED: flat RGB/chroma truth errors remain at1.0000x current. Actual Off and
Neutral outputs are exact; source data, replay, finest weights, finest/base
accumulators, fallback sums and hull bounds remain exact. The literal mixed-
support/odd-geometry oracle, invalid-input refusals and live wrong-donor control
pass. None of that prevents loss in the reconstructed image.

The independently exercised two-depth superposition decisively rejects the
rule as a general replacement. Whole RGB error rises2.4510x/2.4408x and chroma
error2.3691x/2.3703x at ISO100/400. Far/coarse component recovery drops from
roughly0.765–0.784 to0.218–0.220, while near/fine recovery increases from
roughly0.536–0.570 to0.827–0.914. These separate uncapped components expose
real detail loss that an overall sharpness or near-component score would hide.
The rule imposes one source mixture on detail that truly belongs to two depths.

The glint controls also reject: extension RGB error rises1.1301–1.2299x across
the four ISO/colour cells; core RGB or chroma guards fail as well. Genuine thin
coloured rays pass. Thus this is not merely an unexercised positive fixture.

The broad-contact positive is separately **UNEXERCISED as bright outside spill**.
Its baseline outside RMS exceeds twice the flat RMS, and the late source has
strong outside spill, but baseline signed mean excess is only0.000485772/
0.000585745 versus flat RMS0.001109891/0.002220783. That required brightness
condition fails. Outside RGB ratios0.9925/0.9886 also miss the fixed0.95 bar;
the candidate outside mean becomes negative. Do not relabel its residual error
as demonstrated bright-spill cleanup. Contact interior RGB ratios0.3503/0.4029
and edge ratios0.6341/0.6682 improve in this generated scene, with retained
components, but they do not replace the registered positive or erase damage
elsewhere.

Lower RMS can reward smoothing and a component score can reward excess
contrast; the screen pairs both with chroma and separate-component controls.
Its noise constants are injected into both stimulus and consumer, so this is
an operator test, not new camera calibration. No real photograph was processed
by these commands. No promotion, full-render admission or SOTA claim follows.
No parameter, window or threshold rescue of this failed global qualification.

Screen SHA256:
`a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144`.
See `controls-1/output/screen.json`, its immutable executable/source bindings,
and the independently authored `results-review.md` for interpretation limits.
