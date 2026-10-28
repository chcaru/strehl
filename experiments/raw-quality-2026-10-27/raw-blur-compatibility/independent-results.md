# Independent first-screen result

2026-10-27. **MEASURED numerical noncompletion after the first flat fit; physical-model selectivity remains untested. No photographic release.** The returned flat image and held predictions pass their diagnostic guards. The fixed optimizer criterion fails. Do not turn that distinction into either a quality success or a rejection of original-CFA blur reconstruction as a family.

Run1 exited1 after7.45s while serializing a NumPy float32 to JSON, before any fit. Its empty commission file and exact failed source remain. The [serialization-only patch](serialization-only.patch) converts NumPy scalars with `.item()`; it changes no stimulus, operator, prior, optimizer, gate or display. Root reran in a fresh directory.

**VERIFIED run2**: exit0,8.172s, peak host-job commitment3,536,044,032bytes; direct exit/EOF observed, no active owned process, error, cleanup failure or termination. Torch2.11.0+cu128/CUDA12.8, RTX5090, one CPU worker, TF32 off. Torch peaks555,328,512allocated/727,711,744reserved bytes exclude driver/runtime memory. Host samples show0–5.3% CPU and48.5–47.1GB available RAM. These are tiny diagnostic costs, not full-workflow speed evidence.

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/independent-controls.py --out outputs/raw-quality-2026-10-27/raw-blur-controls-2/output
```

## Operator evidence

The independent continuous forward tests pass. At variance0/.35/2.3 their RMS errors are.0680/.1141/.0220sigma; the zero-optical-blur wrong-reference-footprint foil gives.1773sigma. This demonstrates sensitivity to the tested original-source footprint difference, not exact Gaussian optics. Known output integration has1.1664DN RGB error (.06475sigma). Flat-forward maximum error.001953DN passes its conservative f32 allowance. Literal phase rejection,2px wrong-map, all-phase directional derivative, biased prediction, erased-far and overcontrast destroyers pass. None is an unknown-latent compatible-positive fit.

## Returned flat and reason for stopping

The first unknown fit reaches64L-BFGS iterations and71complete evaluations. Final parameter-gradient maximum is0.0005203545 versus the predeclared1e-6criterion, so `FIT_ITERATION_LIMIT` correctly prevents admission. That parameter-space criterion is an optimizer requirement, not a calibrated physical-mismatch test or an image-error bound. The objective falls4.09017→3.36270, but that alone cannot establish convergence or image quality.

The returned flat's RGB/chroma RMSE is3.97661/5.54393DN versus7.73711/10.24490DN for the explicitly labelled same-data2x2 CFA mean. This diagnostic noise reduction passes the fixed flat bars. Both held views also pass global, phase and cell guards: RMS.98899/1.00815sigma, maximum cell RMS1.1831/1.2716. These outcomes do not support rejecting the physical model on the flat.

I inspected the complete unresized96x96 [truth](../../../outputs/raw-quality-2026-10-27/raw-blur-controls-2/output/flat-neutral/truth-complete.png), [returned output](../../../outputs/raw-quality-2026-10-27/raw-blur-controls-2/output/flat-neutral/fit-complete.png), [initialization](../../../outputs/raw-quality-2026-10-27/raw-blur-controls-2/output/flat-neutral/initial-complete.png), and [same-data mean](../../../outputs/raw-quality-2026-10-27/raw-blur-controls-2/output/flat-neutral/same-data-flat-mean-complete.png), under the identical fixed display. They look broadly uniform; no conspicuous lattice or colored contour is visible. This flat has no real detail to preserve. [Full float fields](../../../outputs/raw-quality-2026-10-27/raw-blur-controls-2/output/flat-neutral/fit/fields.npz) retain240x240latent and96x96delivered/initial RGB; none is a photograph.

Flat blur remains unidentifiable: fitted calibration variances54.98/109.17 are not optical measurements. View5's selected parameter is outside its final search interval; view6's is localized, which still does not identify blur on constant truth. These statuses remain explicit.

## Scope retained

The coloured flat, compatible unknown reconstruction, mixed depths, annular blur, changing glint, chromatic/asymmetric blur and sharper-than-anchor cases were **not fitted**. Their complete generated truth/input panels exist, but no reconstruction or selective mismatch-refusal result exists. The spatial-cell anchor-order guard was already explicitly deferred. No refuse-all-resistant compatible positive has yet passed; no actual native baseline ran.

I independently verified active source/model hashes, both saved-field hashes and all seven saved original-u16 identities against receipts. Observation SHA256 is `3c043a5d68fb1a27d2ee841b46a838f6e6b96b82644b6410c161f719d5143053`; model remains `659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc`. The large free apron and direct-support mask do not certify identifiability. No further solver, decode, retone or numerical experiment was executed by this reviewer. Preserve this fixed-screen stop without extending caps or relaxing tolerances; the photographic objective remains unresolved.
