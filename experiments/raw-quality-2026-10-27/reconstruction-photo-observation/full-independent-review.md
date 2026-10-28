# Independent full60 receipt review

2026-10-27. VERIFIED: `outputs/raw-quality-2026-10-27/reconstruction-photo-full-1` is a complete, mechanically valid photographic diagnostic. This review reads receipts, hashes files and inspects TIFF headers; it performs no RAW decode, pixel-array computation, build or reconstruction. Photographic quality is a separate complete-image review.

Root ran the saved build2 executable with:

```powershell
& 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\reconstruction-photo-build-2\cli-tests.exe' merge_cmd::reconstruction_restart::photo_observation::flat60_complete_observation --ignored --exact --nocapture --test-threads=1
```

The invocation records four workers, rounded GPU gathering, green probes, the held CA-on profile and isolated map. Executable SHA256 is `ab776fe4b3b29c8756374f45fb7058e107e0d7723fd8a6c5cdc54bc4d857cdb8`. MEASURED by root: exit0, one completed test,53.547seconds wall,3,574,009,856bytes peak job memory and clean terminal accounting. These observations are not a competitive speed ranking.

## Identity and complete artifacts

All11 completion-listed JSON hashes/lengths independently match. Streaming hashes verify both complete RGB16 masters, both floatRGB masters and both signed CFA fields, plus coefficient and input-hull caches. The32 coefficient segments cover four planes and eight levels without gaps; every segment hash and the170,825,856byte total match. All1404 build-bound source files and the executable still match. No large image array was decoded for this audit.

The receipt contains exactly source indices0–59 in order, reference30, the original15/15/15/15 chunk association and cropquad[25,17,3466,2310]. Original-source preservation is enforced by the audited actual run's before/after file hashes/stats and decoded-source checks; this reviewer did not reread the RAW corpus. The held map and order hashes were independently rechecked.

Both delivered arms have one complete6932x4620 RGB16 image, one same-size RGB32 float image and a128,103,360byte CFA field. TIFF dimensions, sample types, material tags, ImageDescription and ICC match between arms and the held baseline. The baseline float TIFF is byte-identical to the held float master. The frozen run's RGB16/float pixel-golden assertions pass. Software provenance is separately disclosed: this test build says `unknown`, while the held RGB16 master identifies `4813e46bdc9a-dirty`; it is not mistaken for a color or tone difference.

Canonical accumulator, weights, target and hull checks pass, with actual finish equality before/after extraction and solve. The actual InputRange hull is applied to all four candidate planes; there is no partial-plane result or baseline substitution. Standalone solver records exactly equal the copies in the final receipt and solver-results file.

## Numerical result and scope

This flat photograph actually satisfies the unchanged solver criterion on every plane:

| Plane | Iterations | Reported RMS bound, DN | Refusal |
|---|---:|---:|---|
| R | 4 | 0.013256 | none |
| G1 | 5 | 0.004325 | none |
| G2 | 5 | 0.004571 | none |
| B | 5 | 0.002824 | none |

All final objectives are below their initial values. No restart was needed before convergence; the32-step cap, restart-after8 rule and0.02DN bar are unchanged. The bound retains its exact-linear/f32-commissioning qualification, not an interval guarantee for arbitrary floating-point error. The earlier chip green-plane refusal remains an independent historical result.

Research admission and quality claims remain false. Numerical convergence here does not reverse the generated glint/far-detail regressions, establish visible benefit or authorize a weevil transfer. Complete images and the frozen eight native witnesses must determine the photographic verdict; both full masters remain available even if that verdict is negative.
