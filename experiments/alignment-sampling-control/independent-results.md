# Independent interpretation: instrument repaired, local blur route refused

MEASURED by root's two bounded runs, independently read after completion:

```
python -I -B -X faulthandler experiments/alignment-sampling-control/run.py --out experiments/alignment-sampling-control/run-1
python -I -B -X faulthandler experiments/alignment-sampling-control/run.py --out experiments/alignment-sampling-control/saved-photo-1 --qualified-from experiments/alignment-sampling-control/run-1
```

The unchanged original no-blur stimulus reproduced its refusal. The fitted
bilinear beta was -0.0911119785 source-native pixel squared. In the fixed-motion
unit, exact evaluation stayed at numerical zero; half/half bilinear produced
-0.1283167165. Integer bilinear also stayed at numerical zero. The independently
commissioned compact Catmull-Rom substitution gave -0.0015020001 on the original
guided no-blur case and passed **all** unchanged original generated controls,
not only the first case. The 0.03 beta gate was not relaxed.

This establishes a real numerical defect in that diagnostic sampler. It does
not establish that interpolation caused the user's stacking artifacts, nor
that a scalar Laplacian identifies photographic defocus.

The separately qualified replay read the same nine cached photographic patches
and no RAW files. The overlay changed only the sampler and its support-radius
check. It required successful generated results/process, unchanged bound
sources and the old photographic measurement path. Result:
`STOP_LOCAL_BLUR_NOT_IDENTIFIED`.

All measured phase/support shift spreads were below 0.25 native pixels in the
reference149 gauge, but frame153 reached 0.2496719293, near that fixed bar.
This alone cannot admit the model: eligible frame146's beta changed from
+0.1908/+0.2170 on left/right supports to -0.1782/-0.1007 on top/bottom supports.
No eligible frame achieved the required 5% held-out error reduction across all
four phase/support choices. Frame145 retained its historical translation-bound
refusal, and reference149 remained an identity control excluded from admission.

The independent decision is to close this local scalar-blur intervention.
Keep the sampler correction as a commissioned diagnostic lesson; do not infer
a new geometric correction, physical PSF, deconvolution or photographic gain.
No threshold relaxation, patch selection, phase search or further kernel sweep
follows this negative transfer result.
