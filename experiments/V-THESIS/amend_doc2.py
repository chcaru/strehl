import pathlib
p = pathlib.Path("docs/research/V-THESIS.md")
t = p.read_text(encoding="utf8")
ADD = """## Which backend actually ran: the banners, verbatim

The flag-inference trap (naming an estimator-only flag without `--merge` selects
the estimator) did **not** catch BUILD-THESIS. Line 1 of every headline subject's
`merge.err`:

| subject | banner line 1 | banner line 2 |
| --- | --- | --- |
| `bee-3-cpl` | `merge backend   : pyramid (default)` | `LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)` |
| `bee-1-cpl` | `merge backend   : pyramid (default)` | same |
| `leaf-2-cpl` | `merge backend   : pyramid (default)` | same |
| `flowers-cpl` | `merge backend   : pyramid (default)` | same |
| `tweezers-cpl` | `merge backend   : pyramid (default)` | same |
| `flat-on-ruler-cpl` | `merge backend   : pyramid (default)` | same |

Corroborated three ways. The argv of all six merge arms is bare -- `stack <dir>
--out <file>` -- carrying **none** of the eight trap flags, so there was nothing
to infer from. `bee-3-cpl/merge.err:37` says outright *"Those are the --merge
estimator path's stages; this arm is the merge only."* And `n_eff` appears **0
times** in a pyramid run log against 2 in an estimator one.

**The headline is about the shipping backend.** The README's negative stands as
a statement about `strehl stack`'s default.

### Where the 86.07% came from, and why it does not belong where it sits

It is real and correctly sourced: `EST-flat-on-ruler-cpl/merge.err:71`, a gate
calibration table under the banner `merge backend   : estimator (--merge)` --
`gate 4.00, mean n_eff 1.142, n_eff=1 86.07%`. BUILD-THESIS rendered three
subjects with the estimator on purpose and the REPORT calls it "the estimator
arm".

But it is offered under the heading *"Why the merge does not win where it was
expected to"*, as reason 2, explaining the tie of arms that were the **pyramid**.
The pyramid has no `n_eff` and does not degenerate to selection that way. **The
mechanism is inapplicable to the arms it is used to explain** -- a true fact
about one backend used to explain another backend's result.

**A provenance defect worth fixing:** the `EST-*` directories' sidecars are stale
copies of the pyramid run's (`EST-flat-on-ruler-cpl/merge.provenance.json`
mtime 9:16:25, its `merge.tif` 10:09:38), and their argv shows neither `--merge
estimator` nor the EST output path. Only the banner is truthful. The banner's
`wrote` line confirms each EST run wrote to its own directory, so no pyramid
render was ever clobbered.

## Is the null backend-invariant? Measured, not argued

The estimator renders survive for three subjects, from the same pinned binary,
with identical frame count, reference frame and field-of-view scale to their
pyramid twins -- so P and E sit on one grid and need no registration. Same
sites, same gates, same statistic as the headline above.

Commissioned first in this same-grid configuration: planted 0.00 / 0.20 / 0.50 /
1.00 px read back **+0.000 / +0.198 / +0.497 / +0.998**, and a pure-noise plant
reads **+0.053**.

| subject | pyramid vs argmax | estimator vs argmax | pyramid vs estimator |
| --- | ---: | ---: | ---: |
| `bee-3-cpl` | +0.203 (p 0.38) | +0.180 (p 0.38) | **+0.131** (p 0.007) |
| `leaf-2-cpl` | -0.258 (p 0.50) | -0.189 (p 0.82) | **-0.169** (p 0.012) |
| `flat-on-ruler-cpl` | -0.329 (p 0.011) | -0.158 (p 0.011) | **-0.247** (23/23, p < 0.0001) |
| pooled, n = 64 | -0.180 [-0.315, +0.146] | -0.147 [-0.201, +0.153] | -0.124 [-0.197, -0.089] |

**The tie is backend-invariant.** Neither backend resolves finer than the
selector on any of the three subjects, and the two backends' margins against
argmax agree closely. Relabelling the arms would not have changed the
conclusion, and there is no hidden pyramid win.

The backends do differ from each other, significantly but small and
subject-dependent: the pyramid is finer on `bee-3-cpl` by 0.131 px and softer on
the other two. **On `flat-on-ruler-cpl` the shipping pyramid is the softest of
all three arms**, losing to the estimator on 23 of 23 sites -- which is also the
one subject where selection wins outright, and is worth a look on its own.

"""
t = t.replace("## The arms are comparable; the confounds the brief flagged are absent",
              ADD + "## The arms are comparable; the confounds the brief flagged are absent")
p.write_bytes(t.encode("utf8").replace(b"\r\n", b"\n"))
print("updated", p.stat().st_size, "bytes")
