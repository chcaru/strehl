# Independent generated-output decision

2026-10-26. **ARGUED decision: reject this exact recipe for a full 299-source photographic observation now.** Preserve its substantial cofocused colour-detail result as demonstrated headroom. The strict screen fails for reasons beyond the prospectively allowed green-noise tradeoff: in the different-source adverse, it visibly trades away a recoverable blue structure to strengthen red. No RAW photograph was read or reconstructed by this review, and no photographic improvement is claimed.

## Evidence integrity and viewing

**VERIFIED:** the originally reviewed `screen.json`, executed test executable, all 66 complete camera-RGB float outputs, and seven relevant current Rust sources agree with their recorded SHA256 values. The seven sources are the five insect-colour Rust files plus the retained noise probe and consumer bridge. After resolving the build-job cleanup, root reran the entire generated screen in a fresh independent job: exit 0, `SCREEN_COMPLETE`, strict admission false, direct exit and pipe EOF observed, zero terminal active processes, and no cleanup errors. This post-cleanup job measured 4.344 seconds and peak job commitment 400,412,672 bytes. The replay receipt records all 66 float outputs byte-exact, including the noiseless focused source. The original visual inspection and quality conclusions therefore remain applicable without another inspection. These are one tiny generated job's operational measurements, not photographic throughput.

Command actually run by root, from `invocation.json`:

```text
outputs/raw-quality-2026-10-26/insect-color-post-cleanup-screen-1/cli-tests.exe merge_cmd::insect_color::controls::fixed_shared_snr_actual_consumer_screen --exact --nocapture --test-threads=1
```

Rayon and pyramid workers are both 2. The recorded path enables alignment, full-resolution gather, rounded direct planes, green canonical probe, parallel writeback, GPU gather/device scheduling; defect, fine-support, and CA treatments are off. The original bounded build's Cargo process exited 0 and emitted the completed test artifact; direct exit and EOF were observed. Its wrapper then reached the 900-second bound while draining one remaining owned descendant. Root terminated that remaining job process, reached zero terminal active processes, and recorded no cleanup errors. This was successful compilation with a failed drain bound, not a clean bounded-build completion or a build-time benchmark. A normal cached Cargo exit check subsequently completed with exit 0 in 0.52 seconds and the same executable SHA256. Root then used `execute-color-post-cleanup.py` for the fresh screen described above. The earlier provisional dispatch is retained in its own invocation record rather than misreported as a clean wrapper exit.

`python -B experiments/raw-quality-2026-10-26/insect-color/independent-preview.py` produced the 66 complete 290x250 RGB8 previews in 0.828 seconds, with exit 0. Every preview uses unit gain, the same sRGB transfer/ICC, and no resizing. These are structural previews of generated camera RGB, not calibrated photograph colour. Inspected the complete canonical/joint pairs for all twelve scene/ISO cases, plus the complete noiseless canonical, joint, and identified focused-source-2 outputs. Flat fields were inspected first. Float masters and preview hashes remain in the receipts; there was no crop-only decision or contrast enhancement.

## What succeeds

**MEASURED:** both flat cases pass. Joint RGB error is 0.940/0.935 times canonical at ISO100/400, green 0.875/0.870, and chroma 0.923/0.917. The complete previews show no gross new flat instability. This distinguishes the current recipe from the earlier R/B-own-guide flat failure.

Neutral and all near/far/junction windows pass their frozen guards at both ISOs. The complete neutral stripes and both thin structures remain visible; there is no convincing visual loss there. These plants do not establish real occlusion safety.

The cofocused positive is a real generated gain: joint RGB error is 0.418/0.435 times canonical and chroma 0.320/0.330. Red/blue template recovery rises from approximately 0.42–0.56 to 0.88/0.91, close to the identified focused source's 0.89/0.92. The complete output visibly strengthens the actual vertical red and diagonal blue patterns. Improvement also survives the matched-green reference. The wrong-source guide loses the gain, and diagnostic on/off outputs remain exact. Thus this is neither a dead path nor merely a favourable replacement variance estimator.

## Why this is not just a green-noise exception

| Case | Observed failure | Interpretation |
| --- | --- | --- |
| Cofocused ISO100/400 | Developed-green error 1.396/1.607 times canonical | Strict guard fails despite substantial colour recovery. The noiseless companion below shows the increase is not solely acquisition noise. |
| Weak red ISO100 | Green error 2.070 times canonical; RGB improves to 0.713 | Colour recovery is substantial: 0.878 versus canonical 0.210 and focused source 0.886. This is a real tradeoff, not erased red detail. |
| Weak red ISO400 | Recovery 0.453 versus eligible focused source 0.888, below 90%; green error 1.339 times canonical | Joint improves over canonical's 0.211, so this is incomplete recovery, not a new red-detail regression. It still fails the promised weak-detail guard. |
| Different-source ISO100 | Blue recovery 0.406 versus canonical 0.426 and focused B3 0.879 | Focused-blue retention fails decisively; blue is also slightly reduced versus canonical. |
| Different-source ISO400 | Blue recovery 0.407 versus canonical 0.521 and focused B3 0.879 | A 21.9% loss of already retained blue structure, while red rises from 0.404 to 0.740. Lower aggregate RGB error hides a genuine opposing component loss. |

In the last complete pair the diagonal blue component becomes visibly weaker relative to dominant vertical red. This is the decisive failure. Its independently identified source B3 contains that component, and the canonical output retained more of it. A single shared weight can favour the source that supports one colour when another overlapping colour needs a different focus source. The result is consistent with that conflict; the screen does not establish how often it occurs on the user's insect photographs. It cannot be waived as the anticipated green-noise penalty or described as universal colour-detail improvement.

The adverse RGB error still improves to about 0.877 times canonical. That favourable aggregate is specifically why the independent component check matters. Likewise, stronger-looking vertical structure in the preview is insufficient when the diagonal structure is sacrificed.

## Independent noiseless companion

**MEASURED:** with acquisition noise exactly zero and the declared ISO100 floor unchanged, green RMSE is 0.004582 canonical, 0.007309 joint, and 0.007360 for identified focused source 2. Joint/canonical is 1.595, so the noisy-case green increase cannot be attributed solely to reduced noise averaging.

However, the candidate closely follows the focused source's existing deterministic development residual. Red-template coupling into green is 0.05076 joint versus 0.05085 focused source (canonical 0.03851); blue-template coupling is 0.03789 versus 0.03776 (canonical 0.03848). Joint green RMSE is slightly lower than that focused source. The complete noiseless joint and focused-source previews are also very similar. It would therefore be incorrect to claim a newly invented merge false-green mechanism from this result. Sharper coloured sampling, actual gather/quantization, and final MHC already carry the residual in the focused reference; canonical averaging hides some of it by also attenuating desired colour detail.

The companion's truth/template destroyer passes its commissioning, and its original 1.05 green guard remains false. It supplies attribution, not a replacement pass criterion or proof that the complete photograph would improve.

## Practical recommendation

The exact recipe has demonstrated useful colour-guide headroom and no flat or neutral catastrophe. Its weak ISO400 result is not, by itself, a reason to reject a photograph: it improves on the baseline while missing an ambitious recovery target. The actual blue loss in the different-source case is stronger evidence against spending the next full-stack observation on this fixed shared scalar recipe. It violates the central goal of retaining genuine structures rather than winning an aggregate score.

Current source inspection has not established a specific coloured weevil structure erased by the baseline that this treatment addresses. The full seven-band path is more selective than this four-band screen, and the retained estimator needs sixteen extra gathers per source; full-source cost remains unmeasured. Those uncertainties are additional practical reasons, not claims of demonstrated photographic or timing failure.

Do not launch another threshold, seed, or amplitude campaign to rescue this screen. Retain the positive and adverse evidence, close this exact recipe for the proposed full observation, and return the root allocation to a photograph-supported mechanism. This does not reject all shared colour guides, alternative estimators, or native RAW reconstruction architectures. Root may independently choose an explicitly exploratory complete output, but must retain this strict failure and component-loss warning; this reviewer does not recommend that expenditure now.

## Complete evidence links

- [All full generated previews and hash receipt](independent-previews/receipt.json); [conversion source](independent-preview.py).
- Cofocused ISO400: [complete canonical](independent-previews/cofocused-colour-positive-iso400-canonical.png), [complete joint](independent-previews/cofocused-colour-positive-iso400-joint.png).
- Different-source ISO400: [complete canonical](independent-previews/different-source-colour-adverse-iso400-canonical.png), [complete joint](independent-previews/different-source-colour-adverse-iso400-joint.png).
- Noiseless: [complete canonical](independent-previews/noiseless-cofocused-canonical.png), [complete joint](independent-previews/noiseless-cofocused-joint.png), [complete focused source 2](independent-previews/noiseless-cofocused-focused-source-2.png).
- [Post-cleanup screen and complete float-master paths](../../../outputs/raw-quality-2026-10-26/insect-color-post-cleanup-screen-1/output/screen.json), [invocation](../../../outputs/raw-quality-2026-10-26/insect-color-post-cleanup-screen-1/invocation.json), [completed test process](../../../outputs/raw-quality-2026-10-26/insect-color-post-cleanup-screen-1/process.json), [all-66 replay equivalence](../../../outputs/raw-quality-2026-10-26/insect-color-post-cleanup-screen-1/replay-equivalence.json).
- [Originally inspected float-master paths](../../../outputs/raw-quality-2026-10-26/insect-color-observed-screen-1/output/screen.json), [resolved bounded-build process](../../../outputs/raw-quality-2026-10-26/insect-color-build-1/process.json), [normal cached Cargo exit code](../../../outputs/raw-quality-2026-10-26/insect-color-cargo-exit-check-code.txt), [cached Cargo log](../../../outputs/raw-quality-2026-10-26/insect-color-cargo-exit-check.log).

Post-cleanup screen SHA256 `dc3edb87552677d0e58d89562ebcdbbf42786eec967ea11bdce895a350c2ba8b`; originally reviewed screen `107aedc8b537e7d00ee1de2fffb1d70df9be2df3321c51496c5270649c5b824e`; unchanged executed binary `b122a2c720de6880ceece6ae59eb95e5bdea4b0fc3d3ac269753690540476109`; independent companion source `38da8ee5968e7f0feeb0d8dcd4d06a56cd435090c9c8f658f491e33a04513d23`.
