# Fixed saved-error scale/phase decomposition

Prospective, read-only; no author execution, fit, new prior or camera RAW access.
Use flat and layered saved pinhole RGB from visibility-1, shot-prior-1 and
cauchy-1 against the same original screen truth. Only the existing supported
whole native square `[16:80,16:80]` is analyzed. The irregular core/ridge boxes
are not silently trimmed, padded or replaced: they are not decomposed here.
Their original quality scores and native views remain the local evidence.

First cast both image and truth to f64, subtract RGB, then form signed R-G and
B-G error, exactly matching the retained chroma score's arithmetic. The pure
`decompose(error)` API accepts finite HxWx2 errors with spatial axes divisible by4.
For each basis origin (x,y)=(0,0),(1,0),(0,1),(1,1), circularly roll by(-y,-x),
then use orthogonal piecewise-constant projections P2/P4 on nested2/4 blocks.
Report per-coordinate mean squares of e-P2(e), P2(e)-P4(e), and P4(e).
Their sum conserves the same total; report the residual and assert within
1e-11*max(1,total). Signed DC is separate; P4's mean-square splits into DC²
and its spatially varying remainder under the same check. No fitted cutoffs.

Every phase retains every one of the same4096 samples. Circular wrap changes
the partition basis, not the image or physics; shifted partitions create
artificial block neighbors at the supported square's boundary. Disclose that
caveat rather than presenting phase differences as independent corroboration.
The four partitions are strongly dependent and carry no probability claim.

Independent controls use literal coordinate-group projections, DC/checker/
4-cell/smooth stimuli, Parseval checks, all four phases, and the frozen scalar
chroma result. A checker or constant must produce different energy partitions,
so a decomposition that reports all energy in one band cannot pass. No new
quality admission follows from any energy ratio. Native-scale chromatic error
alone cannot prove an unobserved CFA mode, and block-common error is not
necessarily uniform colour bias; retain signed DC separately.

All input files are hashed before/after. CLI:
`python colour-error-decomposition.py --out <directory>`. Truth and all three
candidate source roots are fixed inside the existing experiment directory.
Output result.json records the six cases, per-coordinate energies/phases,
original chroma RMS, common-domain support and immutable source bindings.
No image correction or reconstruction is exported.
