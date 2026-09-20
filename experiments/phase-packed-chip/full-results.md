# Complete chip pair: removing the final demosaic

MEASURED: all299 originals completed in both arms at6468x4300 RGB16. The
baseline reproduces every decoded RGB16 sample of the previously displayed
CA-current master. The candidate retains twelve site/colour planes through
the same merge and interleaves RGB without the final MHC pass. Initial MHC,
ordinary optical CA, alignment, green guide, noise, admission and tone remain
fixed. This is the first complete chip observation of this exact consumer;
the prior vitamin-C photographic failure remains unchanged.

Root inspected both whole overviews first, then all seven frozen native
regions using lossless side-by-side concatenations, baseline left. **Root's
bounded photographic finding: no identified meaningful improvement.** Rail
edges and contact interiors change slightly, but the coloured rims, central
blue/magenta stipple and bright contact bloom remain. The periodic arrays do
not reveal an additional resolved feature. Scratches and broad material colour
remain visible. These are observations on the inspected views, not a proof of
pixelwise harmlessness or optical truth. Independent review is separate in
`full-results-review.md`; do not substitute this author's verdict for it.

The unchanged generated screen retains its worst flat-chroma ratio1.078951
under its historical1.25 bar. It does **not** pass a1.05 flat guard. Lower
chroma variation or higher gradient energy alone would be inadmissible quality
evidence: they can reward colour destruction or invented detail respectively.
No default promotion or SOTA claim is supported. Do not tune this unchanged
recipe's interpolation, frequency or threshold after the photographic null.

## Reproduction and integrity

Run from the repository with Python3.12:

```text
python -I -B -X faulthandler experiments/phase-packed-chip/run.py build --out experiments/phase-packed-chip/build-1
python -I -B -X faulthandler experiments/phase-packed-chip/run.py controls --build experiments/phase-packed-chip/build-1 --out experiments/phase-packed-chip/controls-1
python -I -B -X faulthandler experiments/phase-packed-chip/run.py cost --build experiments/phase-packed-chip/build-1 --screen experiments/phase-packed-chip/controls-1 --out experiments/phase-packed-chip/cost-1
python -I -B -X faulthandler experiments/phase-packed-chip/run.py full --build experiments/phase-packed-chip/build-1 --screen experiments/phase-packed-chip/controls-1 --cost experiments/phase-packed-chip/cost-1 --out experiments/phase-packed-chip/full-1
```

Fresh `Compiling strehl-cli` appears in the build log. All four retained
consumer controls pass and all28 screen cases reproduce exactly. Source149's
complete-domain cost checkpoint passes the frozen feasibility gate. Full
execution preserves all299 active-source hashes, metadata and beta values
against CA-current. All twelve pulls pass support preflight; four known
collapsed planes and admission fractions are bit-exact between arms. Source
storage remains u16 with only current-source reconstruction live.

Both outputs use reference149, held map
`ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922`,
quad crop[141,97,3234,2150], fixed tone and the same sRGB ICC.

| Output | TIFF SHA256 | RGB16 little-endian SHA256 |
|---|---|---|
| Baseline | 46692b100544fca30358f2594d5aeeebd3c620f313efc9561b3c2da3f8dcefa2 | 7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db |
| Candidate | 01a05c85cadbbff754e3e435f9608ddfe46e8cd5563d85b1993a2daa6f043e90 | 3154dcd880109cd399284dd5268399c9b7a825707f150528e1c6ddc056fd5a9d |

The single paired process takes256.703s with7,301,345,280bytes peak Job commit.
This is an operational reading, **not** a speed comparison: a small exporter
build and sequential one-source TIFF development overlapped it. Source phase
is254.5814s and finish1.5647s; CPU1325.7344s includes the owned job only.
GPU allocation and total host memory are outside the Job-commit reading.

Complete masters are `full-1/output/baseline.tiff` and `candidate.tiff`.
`full-1/{baseline,candidate}-whole.png` retain every native output pixel;
`{baseline,candidate}-overview.png` show the complete field at quarter scale.
All use common high-byte RGB16 conversion with unchanged ICC. Region images
are secondary inspection aids and cannot replace the complete output pair.
