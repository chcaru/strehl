# Complete flat reconstruction observation: no useful photographic gain

2026-10-27. **VERIFIED photographic refusal.** Root and [independent photographic review](independent-results.md) inspected both complete images first and then all eight frozen native384 pairs. The output remains very close to baseline: soft QR/dot/star shoulders, unresolved finest bar groups, pale merged radial center and existing colored edges persist. No conspicuous new regression was observed, but no substantial useful improvement was demonstrated. Do not promote or automatically transfer this recipe to the weevil. This is not a claim that all inverse reconstruction fails.

Complete outputs: [baseline](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-views-1/baseline/complete-stack.jpg), [diagnostic](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-views-1/candidate/complete-stack.jpg). Full6932x4620 masters: [baseline RGB16](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/baseline-master.tiff), [candidate RGB16](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/candidate-master.tiff), [baseline float](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/baseline-linear.tiff), [candidate float](../../../outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output/candidate-linear.tiff). Both whole images and RGB16 links were shown to the user. Native crops supplement them and use identical fixed development.

**MEASURED actual commands**, from repository root:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py build 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py build 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py screen 2 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py cost 2 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py full 2 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run-prepare-views.py --input outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output --out outputs/raw-quality-2026-10-27/reconstruction-photo-views-1
```

Build1 exited101 on oversized receipt-macro expansion before any numerical run. Its exact source is retained. Build2 freshly compiled after a receipt-assembly-only repair, independently checked to preserve all44 key/value expressions and numerical code. Executable SHA256 `ab776fe4b3b29c8756374f45fb7058e107e0d7723fd8a6c5cdc54bc4d857cdb8`. Frozen operator SHA256 `2ef0ef4237be81ad3febc06140cd36e1469a9d73f3beee567f2f336fdf790a0b`; final adapter SHA256 `3a7387c3d9240aac1266f004dddec02079c54798557718dcb73edab248f52cb0`.

All subsequent commands exited0. The unchanged five-test screen exactly reproduced its earlier reports, including generated quality failures. Source30 checkpoint13.657s/3,251,228,672B proved exact gathered CFA, sensor, RGB16, float and ordinary-writer parity. Complete60 run53.547s/3,574,009,856B used four workers and GPU gather with all sources, one actual gather each, fixed map/CA/profile and baseline development. Export4.813s/991,936,512B read saved files only. These are measured operational costs, not controlled performance rankings; complete processing excludes earlier alignment. Process/environment/source receipts retain host context.

All four complete-flat solves actually converged under unchanged0.02DN/32step criteria: iterations4/5/5/5, bounds0.0132556/0.0043251/0.0045710/0.00282446DN. No restart was needed. This does not alter the old full-chip G1/G2 refusal or the known generated glint/far-detail harms. Admission and quality flags remain false. [Independent full audit](full-independent-review.md) verifies complete masters, CFA fields, coefficients, actual hull, baseline pixel/material goldens, all32 coefficient segments and source/build bindings. Observer extraction/solve leaves canonical weights/state/finish unchanged. No fallback plane or altered solver criterion was used.

The existing complete Helicon B8/C and source30 remain context comparisons. B/source30 show more compact existing QR/dot/wedge boundaries with stronger color fringe; C retains broad shoulders. Native CA-on reconstruction versus CA-off predeveloped vendor inputs and vendor geometry are confounds. No merge-only, optical-ceiling or new resolution claim follows. Root-owned scope and complete-image failure boundary are satisfied; no production change and no SYNTHESIS fold.
