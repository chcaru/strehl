# Fixed source field: rejected before photographic replay

2026-09-19. Root executed the independently authored controls against the
frozen implementation. Both test functions completed, but the explicit
photographic admission is **false**. No complete RAW pair was run and there
is no new photograph or product promotion from this experiment.

Commands actually run, from the repository root (Python 3.12):

```
python -I -B experiments/shared-source-field/run.py build --out experiments/shared-source-field/build-1
python -I -B -X faulthandler experiments/shared-source-field/run.py controls --build experiments/shared-source-field/build-1 --out experiments/shared-source-field/controls-1
```

MEASURED: the fresh build compiled both strehl-core and strehl-cli and took
131.219 seconds. The control job completed in 1.906 seconds, with peak job
committed memory 393,920,512 bytes. These are operational costs, not speed
benchmarks. Source bindings remained unchanged. The full adapter was separately
source-reviewed but never executed.

MEASURED candidate/baseline linear RGB truth-RMSE ratios:

| Region | ISO 100 | ISO 400 |
| --- | ---: | ---: |
| Glint fan | 1.108485 | 1.019284 |
| Glint core | 1.860667 | 1.751951 |
| Different-depth boundary | 0.992826 | 0.994778 |
| Nearby real texture | 0.998071 | 0.998297 |
| Genuine coloured radial detail | 0.985230 | 0.996728 |
| Thin far feature | 1.087190 | 1.049864 |
| Thin near feature | 1.112555 | 1.066107 |

Lower truth error is better, but smoothing can lower it; the independent
screen therefore pairs it with truth-template recovery and chroma error.
Recovery can reward excess contrast or correlated wrong structure, so it is
not quality evidence by itself. The core retains roughly 1.03–1.05 times
truth-template amplitude: its increased error does **not** demonstrate core
erasure. The thin near feature likewise increases amplitude while its ISO100
RGB error exceeds the 1.10 guard. No new optical cause is isolated by these
ratios.

The ISO100 glint fixture is fully exercised and already decisively rejects
the rule: the required fan benefit is absent and core error rises substantially.
ISO400 additionally fails the preregistered fan-versus-flat separation, so its
fan value is not a second clean fan-specific rejection. The separate core and
detail values remain observed outputs, with that qualification.

MEASURED: five-source flat outputs are exactly baseline in the score; the
70-source flat RGB/chroma ratios are 1.00000236 and 1.00000359. The latter is
practically unchanged, not literally identical: 35 quads have nonzero
activation. Constant and constant-green/colour-only placebos take the exact
baseline fallback. The noisy Off arm is exact and the forced wrong source
exercises the destroyer. Mechanical categorical paths, high-SNR ratios,
label permutations, replay/base/hull arithmetic and source immutability pass.

Screen SHA256:
`460ed3045c650ac1a8bf3a9819ccc8999b2b1a2e9bcee1ad7fd4abb2ea053d0f`.
See `controls-1/output/screen.json`, its executable/source bindings, and the
independent `results-review.md`. The controls print their mechanical receipt
to the retained process log; there is no separate mechanical.json file.

**Decision:** close these fixed costs, spatial penalties and full-AC replay.
Do not tune the penalty, change the windows, weaken admission or spend a full
70-source render on it. Source consistency alone has not earned an image gain.
The manual donor result and previous complete-wavelet colour gains remain
separate evidence; neither rescues this candidate.
