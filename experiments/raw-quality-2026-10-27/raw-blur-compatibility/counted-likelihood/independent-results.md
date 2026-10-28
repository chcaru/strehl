# Counted likelihood: useful tradeoff, fixed image still rejected

2026-10-27. **VERIFIED mixed generated result; no admission.** Counting one image prior against accumulated observation likelihood improves genuine fine/color recovery and held prediction relative to the prior fixed-work output. It also raises flat noise, and the structured image still fails the unchanged guards. This is not photographic progress, a calibrated optical result, or rejection of original-CFA reconstruction in general.

Root executed:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/counted-likelihood/controls.py --out outputs/raw-quality-2026-10-27/raw-blur-counted-1/output
```

Exit0 in11.312s, peak job3,583,225,856bytes; no error/cleanup failure and terminal accounting complete. All three prescribed fits ran. Source model SHA`e66ce20112592f8c0913ac01265d538b3fc073661247b94f972accd9e661befd` differs only by the declared count-weighted objective and receipt fields. The original generator, observations, noise, geometry, initializer, optimizer budget, displays and image guards remain fixed. These are diagnostic costs, not a full-workflow benchmark.

The actual producing-path partition test passes:4096original source2sensels split512/3584 give exactly the same objective and gradient L2 difference5.96e-7 (allowed4.63e-5). The independent literal likelihood-plus-parent-prior calculation agrees. The wrong equal-group-mean foil fails, with objective difference.00840 and gradient difference.008874. Prior count is one, calibration count zero, no records duplicated. This validates the implemented bookkeeping property, not the prior's physical appropriateness.

## Complete outputs and retained tradeoffs

I viewed complete unresized96x96 [truth](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/compatible/truth-complete.png), [counted reconstruction](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/compatible/fit-complete.png), [previous reconstruction](../../../../outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/compatible/fit-complete.png) and initialization at the same fixed display. The counted pattern is firmer and less washed out, but its finest colored modulation remains weaker than truth. Complete flat comparisons were also inspected; their noise difference is subtle at the fixed display and clearer in the retained linear errors. Full float masters remain available for [compatible](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/compatible/fit/fields.npz), [neutral flat](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/flat-neutral/fit/fields.npz), and [coloured flat](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/flat-colour/fit/fields.npz).

| Genuine component | Previous recovery | Counted recovery |
| --- | --- | --- |
| Near fine | .837 | .907 |
| Blue diagonal | .871 | .947 |
| Weak-green crossing | .829 | .918 |
| Red-line second harmonic | .850 | .930 |
| Red-line third harmonic | .724 | .858 |

Coarse neutral/far components remain. Both structured held views now pass, RMS1.15904/1.04628sigma versus1.33036/1.13422 previously. Nevertheless RGB/chroma RMSE52.5561/58.3049DN exceeds45.8054/37.8277bars. The third red harmonic still fails recovery and channel-amplitude preservation; the near-fine blue-channel amplitude error22.4604DN also exceeds its21DNbar. Thus held prediction success does not discharge image preservation.

Neutral-flat RGB/chroma error rises3.9766/5.5439→7.7927/10.7065DN; coloured flat rises4.1176/5.7862→7.9665/11.0238DN. Both still pass the original same-data mean bars and held predictions. This approximately doubled error is a real cost relative to the previous fits, not a failed flat gate or an asserted visible photographic artifact. No unsupported flags occur, so the narrow known-flat calibration-ceiling exception is unused in this run. Flat blur remains unidentified.

All fits remain nonconverged at64iterations. Compatible uses72evaluations and ends at maxgradient.0222183 versus1e-6. Its variance estimates move closer to the supplied values, but a nonstationary result does not identify optical blur or isolate the cause of remaining detail loss. The objective change is a deliberate statistical choice, not correction of an implementation typo.

I verified source bindings, saved float-master hashes and original-u16 identities against receipts. No RAW, model rerun or additional pixel analysis was performed. `all_pass`, `image_only_all_pass`, photographic admission and full-design qualification remain false. Adverse-model selectivity, spatial anchor ordering, native comparison, full-size cost and complete photographs remain untested. Close this one fixed count comparison without parameter rescue; preserve both its stronger genuine detail and its unresolved color/noise costs.
