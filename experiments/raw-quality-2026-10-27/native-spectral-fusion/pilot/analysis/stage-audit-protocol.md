# Fixed saved-array stage accounting

Root-only command,60s/4GiB host, one numerical-library thread:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-spectral-fusion/pilot/analysis/stage-audit.py --out outputs/raw-quality-2026-10-27/native-spectral-stage-audit-1/output
```

Input is only the pinned controls5 receipt, its saved original u16 arrays,
final signed CFA and actual final-MHC normalized camera fields. No producer,
renderer, Torch, FFT, RAW decoder or new fixture is imported/executed. Every
opened array/receipt is hash/size/metadata bound before and after. All10 cases
and both20 delivered arms are retained, including all six inherited quality
failures. All outputs are descriptive JSON, no replacement images or quality
admission.

Use exactly the declared64x64 output at native origin256,256. Describe R,G1,G2,B
separately and the combined green quincunx, with each basis evaluated at its real
physical coordinates and the declared unit-cell sinc factor. For original
source arrays, use the fixed physical source rectangle256,256,64,64 and evaluate
its known shift/blur plant in source coordinates; do not align/interpolate it
or call that window an equal target footprint. For fused CFA use the ideal
unblurred component amplitudes. The final camera field is returned to DN using
the exact recorded WB/range bits, as in the frozen headline scorer.

Report the same components on final camera known-color sites, inferred-color
sites, and the complete camera grid. Known-site camera-minus-max0(CFA) is a
descriptive max/RMS readback quantity, without a new pass bar. Reproduce all
existing complete-camera component amplitudes to1e-7DN as a mechanical audit.
All component fits include a constant. SVD rank uses singular value >1e-10 of
the largest. A rank-deficient physical sample basis yields no individual
component estimates: retain singular values, rank, truth-wave error and
orthogonal residual only. In particular red0.20/0.30 aliases cannot be assigned
unique physical-phase amplitudes. A full-rank dense camera regression does not
create independent original sampling or reverse that limitation.

If error increases at inferred camera sites while known sites preserve the
incoming CFA, that locates its producing stage. It does not prove that final
MHC alone is physically responsible: the fused phase fields may already be
mutually inconsistent. Conversely error already present in CFA cannot be
assigned solely to final demosaic. This is a bounded discriminator using
retained data, not a new inverse fit, PSF measurement or recipe selection.

Success schema: receipt.json status COMPLETE_NATIVE_SPECTRAL_STAGE_AUDIT,
complete:true, inputs_unchanged:true,20 delivered arms, quality_claim:false,
photographic_admission:false. Mechanical read/binding/score mismatch preserves
an incomplete receipt and exits nonzero. Author performed source/AST checks only;
root schedules execution after the current numerical job is terminal.
