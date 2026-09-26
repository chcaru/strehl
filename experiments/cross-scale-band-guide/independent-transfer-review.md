# Independent revision-2 transfer decision

2026-09-26. **ARGUED: diagnose training preservation before the proposed full70
photographic observation.** The selected model has useful fresh gains, but its
losses exceed the previously allowed narrowly failed conjunction exception.
No threshold, window, checkpoint, or historical decision changes here. No new
fit or photographic run is authorized by this review.

**MEASURED by root, independently interpreted here:** selected model
`882532f9d735e1955d75f28679715b4ba4b0dc4829e2d8dba7ed36bb4767a705`.
Exact executed commands are preserved in `transfer-check-1/invocation.json` and
`developer-check-2/invocation.json`. Their screen SHA256s are respectively
`8d4d8d7db3bbc90f8dbb00ac3ca9a30b6891bddad71d8151516820b847c91097` and
`a9d1a528ca3032b96a5f373fa49d72a73baa7d0a99a473059bba144fe9c9e2a7`.
All10 fresh model-to-weight/full-image replays and separate saved-weight
reconstructions are exact. All11 required protections and both positives were
qualified before this model was scored. These failures therefore represent
exercised preservation evidence, not missing support or a dead checker.

## Gains and every failed component

Fresh positive RGB error/current is0.90479 for forked geometry and0.76065 for
thin near/far structure. Thin green recoveries improve0.9031/0.9312 to
1.0065/0.9527; overshoot receives no extra credit. Weak-colour-region RGB is
0.65054 current, with red/blue recovery0.7770/0.7875 to0.8911/0.9047. Genuine
glint-core RGB is0.71693 current and green recovery0.9396 to1.0059. All three
flat tests pass; RGB/uniform is1.00497,0.99975,1.00182. This is approximately
uniform averaging on flats, not evidence of superior denoising.

All14 failing component comparisons are shown below. A coefficient1 represents
the truth template's amplitude. Triples are R/G/B. The quoted raw reduction is
descriptive; the unchanged acceptance calculation caps current credit at1.

| Region and failing channels | Current recovery -> candidate | Actual loss |
| --- | --- | --- |
| Unclipped glint interior, G-near | 1.01664 ->0.89005 | 12.45% raw; capped retention89.00% |
| Unclipped glint adjacent, RGB-near | (0.90982,0.99821,0.86377) ->(0.70748,0.71568,0.65245) | 22.24%,28.30%,24.47% |
| Carrier0, wavelength4 native pixels, RGB | (0.95760,1.06019,0.89117) ->(0.71745,0.79215,0.66695) | 25.08%,25.28%,25.16% |
| Carrier1, wavelength8, B only | 1.00668 ->0.899963 | Capped retention89.9963%; borderline by itself |
| Carrier2, wavelength16, RGB | (0.99475,1.01694,0.98645) ->(0.85319,0.86435,0.83549) | 14.23%,15.00%,15.30% |
| Carrier3, wavelength32, RGB | (0.92917,0.94399,0.92898) ->(0.81997,0.82904,0.81642) | 11.75%,12.18%,12.12% |

Unclipped-adjacent RGB rises0.00656867 ->0.00710287 (+8.13%) and green+6.21%,
despite chroma falling35.28%. Clipped-adjacent RGB rises0.00419727 ->0.00454809
(+8.36%) and green+9.77%; its component reductions are only2.13–4.55%, so those
pass retention. Both spread regions improve. Carriers0–2 reduce RGB error while
losing amplitude; carrier3 RGB rises1.72%. Carriers4–7 pass all fixed guards.
These are final-image frequency protections, not seven distinct depth tests.

## Known regressions and interpretation

All seven old cases remain developer-visible. Six pass the prospective screen;
curved chroma still fails both windows:1.10288/1.13932 current, versus
1.09541/1.13113 after stage1. Its positive RGB improves21.42%, but chroma rises
0.00486400 ->0.00554168. Raising the chroma multiplier did not resolve that
known tradeoff; this comparison cannot attribute causation to the multiplier
because expanded training changed simultaneously. The historical old conjunction
still rejects curved, genuine glint and clipped glint; retain those decisions.

**ARGUED mechanism:** a lower image-error objective can trade real contrast for
noise/colour reduction. The independent projections expose that familiar failure
here, including an easy separated-carrier scene with in-focus source support.
Their failure direction is ringing/correlated false structure inflating a
projection; joint absolute-error checks reduce but do not eliminate that risk.
One draw per fixture provides no uncertainty estimate or camera/lens calibration.

The relevant families already exist in training: `train-multiscale-gabor-v0-n5-b7`,
both new glint cases, and the old curved case. Thus a bounded training-only
preservation diagnosis is available without adding these fresh cases to training
or inventing a held-result-specific objective. The102-step fit ended at its
budget, with its best saved score at the endpoint; no convergence or model-family
ceiling follows. Do not select another checkpoint using these fresh results.

A full70 image would show appearance, but without photographic truth it could
make this smoothing look attractive while leaving the cause unresolved. The
25–28% supported-detail losses are too large to waive as a tiny synthetic
threshold miss. Preserve the reusable full-image bridge; first decide from the
existing training correspondences whether preservation can be improved within
the remaining declared budget. Any subsequent independently justified photo
observation still needs complete matched outputs and native preservation review.
