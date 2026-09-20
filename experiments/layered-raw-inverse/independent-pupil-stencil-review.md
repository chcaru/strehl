# Independent pupil-stencil source review

VERIFIED by source inspection only; no kernel loading, compilation, numerical execution, fit or RAW read by this reviewer. The fixed numerical commission is ready. This is not photographic admission.

The joint table accumulates bilinear near/far products **within each supplied ray**, then groups common integer address pairs. Its near marginal is derived from the stored joint weights. The forward retains `alpha*N` before interpolation and `1-alpha` at the corresponding near address before multiplying the far sample. Replacing this joint distribution by independent near/far averages is genuinely different; the crossing destroyer must demonstrate a live difference.

The atomic-free gather adjoint has the required offsets: near uses incoming derivative at `z-p`; far uses it at `z-q` with coverage at `z+p-q`; coverage uses incoming derivative at `z-p` and far at `z+q-p`, summed across RGB with a negative transmission term. Zero extension applies separately to each sampled field. Out-of-array near coverage is zero, so far transmission remains one. The literal boundary test's incoming derivative is **one only on the first output column and zero elsewhere**, not on the entire image; its zero near/coverage gradients are correct for that restricted witness.

Controls re-choose the implementation through a direct CPU ray/tent enumeration, full-array frozen Torch comparison, nonconstant RGB adjoints at three focus positions, independent finite differences and a doubled-gradient destroyer. Endpoints, an impulse and actual image boundaries are exercised. The added nondefault-stream boundary test creates its inputs within that stream and synchronizes before returning. This tests stream selection without confusing producer ordering with allocator lifetime. Invalid dtype/device/strides/values and unsupported double backward have explicit refusal checks. These controls do not establish context-switch or graph-capture execution behavior; those refusal branches are source-reviewed only.

The ctypes ABI, typed kernel-argument storage and current-context launch agree with the public [NVRTC API](https://docs.nvidia.com/cuda/archive/12.8.0/nvrtc/index.html) and [driver execution API](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__EXEC.html). Module/DLL handles persist; autograd retains input/table tensors; each launch records tensor stream use. As the [Torch documentation](https://docs.pytorch.org/docs/2.11/generated/torch.Tensor.record_stream.html) specifies, recording stream use protects storage lifetime, not cross-stream producer ordering. Finite-result checks synchronize; there is no speed claim.

Density is a separate fixed question. The preselected 16384-point pupil must first agree with the unchanged operator using the **same points** within 0.1 DN. Both the different-resolution 4096 reference and independently rotated 16384 reference must then satisfy the original 0.75-sigma bar in both regions at all five focus positions. Their noise denominator uses the injected model and reference CFA signal. The old 64/1024 discrepancies stay visible. Agreement would be a finite-quadrature consistency result under supplied optics, not continuum truth or calibrated camera validity; it does not repair the earlier inverse-image failures.

The wrapper's `--out` matches the controls. It binds the prior source chain, new source/plans/review and installed runtime DLL hashes, disables the external CUDA cache, and enforces a 240-second / 8-GiB Windows job committed-memory limit. The controls' 60/60/120-second checks are post-stage checks, while the job supplies the hard overall watchdog. CUDA allocated peak has its separate 8-GiB cap; reserved memory is reported, not silently equated with allocated or process memory. Wrapper `instrument_completed` and exit zero are **not** numerical admission: read `output/result.json.passed`, including resource refusal. No parameter, density, tolerance or focus-subset selection is authorized after results.

Reviewed SHA256 bindings:

| File | SHA256 |
| --- | --- |
| pupil-stencil.py | `2be60901ed7a3ee8eb007c8611a4d690fe1ecc859ecaf6e375cb5cd0603e14d6` |
| pupil-stencil-plan.md | `5ec18e2b442f2c8e5092480c44ec455ae918656e2b8ece9047e9b2350bef7ebf` |
| pupil-stencil-controls.py | `4393af7a18d875bea4bcc050dbc28b938908707e52e2b289cf0321afd6113e93` |
| pupil-stencil-independent-plan.md | `222f4369ef400d42ce235d8abd3d7106128446724a114a1f1e0a905afe90d2c5` |
| run-pupil-stencil.py | `a3bb642bbee6890db58dc517b172e6ff66c93f2e6af01498547a16f56e4343ab` |
