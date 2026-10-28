# Native pixel fusion: generated general replacement fails

**MEASURED / independently reviewed:** the fixed screen completed, but its general quality result is negative: `strict_no_harm_all=false`, `severe_generated_loss=true`. It concentrates on near/fine detail while losing the simultaneously present far/coarse structure. The complete generated pictures show that loss; it is not merely an unfavorable scalar score. Flat/noise and identity controls pass. They do not license a general replacement, default change or automatic weevil run.

Root separately authorized source30 commissioning and a complete60 flat **diagnostic**, as the brief permits. That answers whether this fixed change retains known source-supported structure on the near-planar chart. A favorable flat result cannot cancel the depth/color failures below. No real photographic improvement is established by this report.

## Fixed results

| Control | Observed result |
| --- | --- |
| Near/fine versus far/coarse, ISO100/400 | Near coefficients rise from0.536–0.570 to0.832–0.915. Far coefficients fall from0.765–0.784 to0.2157–0.2165. Both components were live in canonical. RGB truth error rises about2.45–2.46x. Candidate coefficients nearly equal the fixed source0 foil; its far-component loss is correctly rejected. |
| Flat/noise | Both small ISO cases and the larger finest-exponent8 case pass the fixed strict guards. Candidate RGB error is approximately1.005–1.006x canonical in the small cases and0.99996x in the large case. It remains roughly11–15% above the uniform mean: noise gating is not a mean-variance guarantee. |
| Bright/dark thin depths | Both lines and their separate depth regions remain visible. Candidate coefficients become modestly overcontrast, approximately1.01–1.08; RGB error rises about7–10% in the protected regions. Strict guards fail; the prospective severe-erasure guard does not. |
| Different-source color | Blue recovery falls0.426→0.306 while red rises0.571→0.627. RGB/chroma errors rise11.1%/9.2%. Blue misses the severe flag because canonical recovery was below its0.5 eligibility threshold; `severe=false` must not be described as no meaningful loss. |
| Cofocused color / neutral / colored rays | Fixed strict guards pass, but color-only recovery remains weak; the candidate does not repair the guide's missing color evidence. Radial structures remain visible. No new photographic detail follows. |
| Clipped glint | Outside-core RGB/chroma error rises22.1%/11.7%, failing strict guards. Both complete outputs retain colored streaks, with candidate spill somewhat stronger. Genuine adjacent texture is broadly stable. No recovered clipped-core value is claimed. |
| Arithmetic / provenance | Mixed shared denominators, all-source zero-evidence fallback, exact equal/single tuples, source0 witness and unchanged original arrays pass. Unequal60000/64000-DN tuples with finite `exp(80)`/`exp(79.5)` weights yield61510.164DN versus61510.162655 from the independent f64 oracle. Nonfinite accumulated denominator cannot escape through the equal-tuple shortcut. |

The small structured cases have four effective AC bands and finest exponent5.488. The root-approved larger flat has six bands with capped finest exponent8, matching the full photograph's finest value. The larger flat does not test structured seven-band behavior. The supplied analytic noise/blur fixtures commission the operator, not Sony calibration or an optical inverse.

The constant0.27 zero-evidence case has tiny numerical centered variance, reported truth SD around1.6e-7. Its printed template coefficients are uninterpretable and excluded by the frozen1e-4 eligibility rule. Exact fallback agreement across18,125 unsupported pixels supplies its valid evidence; no retention claim uses those coefficients.

## Complete generated evidence

The reviewer inspected complete290x250 truth/canonical/candidate/forced views for the decisive near/far case, complete color-adverse and glint truth/pairs, and complete bright/dark-thin, flat and radial pairs. No searched crop, contrast fit or retone was used. The candidate's fine stripes replace much of the broad colored modulation and visually resemble the wrong-source foil.

| Decisive full generated image | View |
| --- | --- |
| Near/far truth | [Complete view](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1-views/near-fine-far-coarse-iso100-truth.png) |
| Canonical | [Complete view](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1-views/near-fine-far-coarse-iso100-canonical.png) |
| Candidate | [Complete view](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1-views/near-fine-far-coarse-iso100-native-pixel.png) |
| Fixed source0 foil | [Complete view](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1-views/near-fine-far-coarse-iso100-forced-source0.png) |

The [view receipt](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1-views/receipt.json) binds83 complete previews and their original float arrays. Fixed display is component-wise sRGB transfer, gain1, clipping0..1 and8-bit rounding; no color matrix was fitted. Core display clipping is recorded and limits glint-core interpretation. Preview export alone was run by this reviewer:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-pixel-fusion/prepare-generated-views.py
```

Exit0,1.567s helper time; all array and receipt hashes unchanged. No model, reconstruction, RAW or Rust job was run by this reviewer.

## Executed screen identity

Root's actual command was:

```text
outputs/raw-quality-2026-10-27/native-pixel-build-1/cli-tests.exe merge_cmd::native_pixel_fusion::independent_controls::fixed_native_pixel_screen --ignored --exact --nocapture --test-threads=1
```

Executable SHA256 `2dad4b2ef2a6a5a03781f2fcfeccd2ef1cc42c1102002893ceafadcbf223b403`; [invocation](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1/invocation.json) records four workers, actual rounded GPU gather and green probe with competing treatments off. [Process receipt](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1/process.json): exit0,2.281s,525,123,584-byte peak job commitment, terminal accounting and no cleanup error. This is bounded screen cost, not a production speed comparison. [Screen](../../../outputs/raw-quality-2026-10-27/native-pixel-screen-1/output/screen.json) SHA256 `bbfbb6c6e258ea6b4edfe9b56ec601cb51692671497ee87f592c9d87a45daf88`; source bindings unchanged. Passing execution preserves the negative quality verdict. No thresholds, windows or recipe were changed after results.
