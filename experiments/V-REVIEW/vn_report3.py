import io
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-noise-verification.md"
T = """

## 13. Provenance of the four published cells

Asked whether any published cell depends on build `066A87AB`, which reproduces
neither shipping corpus.

**It does not.** Established three independent ways, none relying on the others.

**First, my code cannot have used any binary.** MEASURED, by scanning all
eleven `vn_*.py` scripts for `subprocess`, `Popen`, `os.system`, `.exe` and
`vr_lib`: **no binary invocation in any of them.** The only file matching is the
audit script itself, which contains those strings as search patterns. The
verification consumed existing renders and re-derived the estimator in Python.

**Second, the inputs are not in my lane.** The four cells were computed from six
files and one tile census, none under `C:\\dev\\strehl-out\\V-REVIEW\\`:

| role | file |
|---|---|
| strehl, denominator of all four cells | `V-H2H2\\lin\\113-A-g1.tiff`, `113-B-g1.tiff` |
| `enfuse`, cells one and two | `V-LINEAR2\\out\\coh-enfuse-A.tif`, `-B.tif` |
| `focus-stack`, cells three and four | `V-LINEAR2\\out\\coh-fs15-A.tif`, `-B.tif` |
| tile selection only | `V-NOISE\\census.npz` |

**Third, the binary that made the strehl arm is named and its hash checks out.**
`experiments/V-HEADTOHEAD2/render_linear.ps1` carries a Rule 47 record naming
pin `740e7056` at
`C:\\dev\\strehl-out\\acceptance-pins\\740e7056\\target\\release\\strehl.exe`.
MEASURED rather than believed:

| check | result |
|---|---|
| hash of the named binary | `15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0` |
| equals the hash the harness claims | yes |
| equals the SHIP-V3 corpus seal | **yes** |
| equals the SHIP-V4 corpus seal | no |
| equals `066A87AB` | **no** |

Flags recorded with it: `stack --merge pyramid --pyramid-gate 4.5 --linear-srgb
--demosaic`, with `STREHL_FULLRES_GATHER=1`, a pinned warpmap, and eleven
`STREHL_*` variables cleared by name. `experiments/V-LINEAR2/run_free.ps1`
carries the matching record for the comparator side, including
`align_image_stack.exe` version `2025.0.1.9609d5726ad8` and the linear input
frames both comparators were developed from.

### The scope statement that should be published beside the cells

`740e7056` is a **shipping** pin, but it is the **previous** one. It rendered
SHIP-V3; the 26 masters the owner is looking at are SHIP-V4, rendered by
`9b05d0b7`. So the four cells are a measurement of a build that shipped, on a
linear measurement render rather than a master render, and **not** of the exact
binary behind the current masters.

That is a much weaker caveat than the one that sank the aura entry, where the
build had shipped nothing at all. It is not nothing, and the honest wording is:
*measured on the SHIP-V3 pin.* Whether SHIP-V4 changed merge noise behaviour is
**unmeasured here**.

The `--linear-srgb` render is correct method rather than a defect: this
project's standing rule is that quality is never judged through a transfer
curve, and the harness quotes that rule as its reason. A master render would be
the wrong arm to measure noise on.

### A defect in my own first probe, disclosed

My opening provenance probe searched for `.ok` and `.provenance.txt` sidecars
beside each input and found **zero**, against a positive control proving the
pattern can match, which found 26 under SHIP-V4. I was one step from reporting
*the provenance is not recorded*.

**It is recorded. It is not shaped like a seal.** Both harnesses carry Rule 47
comment blocks naming the binary, its hash and the full switch state, and one
even names the resolved input paths of the other lane. A seal-shaped query
cannot see a comment-shaped record, and an empty result from it means only that
this project keeps provenance in more than one form.

This is the same lesson as the earlier missing-binary episode in
`docs/research/V-REVIEW-aura-ship.md`, in different clothes: **an empty search
is a statement about the query.** There it was a filename pattern too narrow by
one wildcard; here it was a provenance *format* assumed to be the only one. The
positive control proved my pattern worked and still did not save me, because a
control proves the query can match things of the kind it looks for -- it cannot
tell you that you are looking for the wrong kind.

### What `066A87AB` is

`C:\\dev\\strehl-out\\V-REVIEW\\bin\\strehl-pinned.exe`, 9,716,736 bytes, hash
beginning `066A87AB`. MEASURED: it is the only copy on this machine and it
produced exactly eight images in my lane, four under `geom` and four under
`halo2`, carrying **no seals**. Those are the renders whose seals I declined to
backfill, and no number in this document or in the four published cells derives
from them. The aura measurement that ORCH acted on used `9b05d0b7`, derived from
the SHIP-V4 seal, and its pyramid arm was byte-identical to the shipped master.
"""
io.open(P, "a", encoding="utf-8", newline="\n").write(T)
print("appended")
