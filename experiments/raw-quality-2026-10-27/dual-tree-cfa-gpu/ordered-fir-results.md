# Ordered forward FIR: fixed generated qualification passes

2026-10-27. **VERIFIED from retained screen2, worker and manifest evidence.** The ordered forward-FIR correction passes the original GPU-port mechanics without changing the controls or tolerances. The two generated quality failures remain. This qualifies the bounded full-size cost observation, not a full photograph, practical299-source cost or quality promotion.

Root ran `outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-build-2/cli-tests.exe merge_cmd::dual_tree_cfa_gpu::independent_controls::generated_controls --ignored --exact --nocapture --test-threads=1`, exit0 after86.438s, four CPU workers, peak job commitment2,718,703,616bytes. [Invocation](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-2/invocation.json), [process](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-2/process.json), [completion](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-2/completion.json), [screen](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-screen-2/output/screen.json). Screen SHA256 is `44627a41fc04b1e7362f13c087790da2c3b1a27609e9638cb543a9a3ec974c09`.

## Runtime change and identity

Build2 is explicitly a **runtime-only rebind**, not a fresh Rust compilation. Both executables hash to `84b8a52c6027179fd7808f70ceceed721437d26ec3e670146e2beacc9b7ae8a7`. I compared all1413 Rust/TOML/lock manifest entries: no differences. Current controls remain `e7d5d236…026785`, and the numerical plan remains `6d30967c…9f1c5a`.

The new server is `b40bead68adb6359ddf103b5cbba53bac97b9c4a9c4fc364b82dc61147dd1a4f`; its pinned helper is `16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce`. The [saved diff](ordered-fir-server.diff) replaces only forward horizontal/vertical grouped convolutions with explicit ordered multiply/add kernels, plus their loading/receipt bindings. The published bank, inverse, weighting and accumulation remain held. Worker metadata records ascending taps, separate round-to-nearest multiply/add, no FMA/FTZ/fast-math and disabled TF32/autocast/f16. CUDA source hash is `b7f5894a6db5164d126a11d86a1b218b74ae237e059684b8e858cbd99b601036`.

I independently hash-checked all32 report/worker/runtime files referenced by completion; all match. All14 worker and bridge pairs completed normally. Their helper/CUDA-source identities agree, helper dependency bindings are unchanged, and the source/probe totals are47/752, including the deliberate five-source wrong-floor run. Maximum reported Torch allocation/reservation is14,907,904/33,554,432bytes. Module/JIT storage is separately disclosed and is not part of the Torch allocator figure.

## Unchanged numerical and quality decisions

| Check | Saved result |
| --- | --- |
| Fourteen forward transform calls | Zero recorded coefficient max/RMS difference, including both signed/high-DN fixtures and all six angular cases. |
| Eight supplied-coefficient inverse calls | All pass the original comparison. |
| Forty-two actual source-stage checks | All pass; recorded energy and floor differences are zero. |
| Actual raw weights | Largest log1p max/RMS differences3.9232e−6/8.3094e−7, inside unchanged0.02/0.002. |
| Ten complete consumer comparisons | Pre-hull, delivered and uniform agreement pass; worst pre-hull max/RMS0.003418/0.001223DN, inside unchanged0.10/0.02. |
| Each backend's reconstruction nulls | Original0.05/0.01DN bounds pass; positive selected coefficients and constant fallback remain exercised. |
| Adverse numerical foils | Altered bank, wrong floor and inherited one-sided phase/direction/scale foils are rejected. |

The previous coarse coefficient/energy discrepancy is eliminated on these tested inputs by changing forward arithmetic order while holding the reference and thresholds. This supports that specific implementation correction; it does not prove identical arithmetic on every full-size input. Inverse reduction and device log/exp differences remain disclosed and bounded by complete-output checks.

Historical canonical/candidate references and all eight quality flags are retained. Independent-color green error and glint error still fail, leaving six passes/two failures and `quality_pass=false`. The canonical two-level versus candidate seven-level confound, weak-green projection limit, simplified curved coverage and unsaturated-glint scope all remain. The earlier failed run is preserved in [first-run-results.md](first-run-results.md).

This review launches no jobs and makes no fresh visual or photographic claim. Full-size execution must still satisfy the original null, source/probe, memory and projected-time contracts. Any subsequently released full299 candidate still requires complete images/masters, all ten fixed witnesses and independent photographic review before a quality conclusion.
