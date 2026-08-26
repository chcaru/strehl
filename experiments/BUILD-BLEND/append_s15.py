"""Append section 15 to docs/research/BUILD-BLEND.md (idempotent)."""

import io
import os

DOC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "research", "BUILD-BLEND.md")
DOC = os.path.normpath(DOC)
MARK = "## 15. The clamp acceptance test, run in the product"

NOTE = """

## 15. The clamp acceptance test, run in the product, and a divergence I withdraw

### 15.1 Status on the wiring gate: wired, and the dispute has a second fingerprint

ORCH's fifth report says `merge_cmd.rs` has zero `pyramid` references and adds a
new datum: *"merge_cmd.rs is 5579 lines."* That is a stronger fingerprint than
the reference count, because it is a number they measured themselves.

Live tree, checked at the moment of writing rather than from the earlier census:

| | |
|---|---|
| repo | `C:\\dev\\blog\\death-of-software\\projects\\strehl` |
| HEAD | `ac8b7022` -> `d56540eb` (other lanes committing during this check) |
| `merge_cmd.rs` | **7619 lines**, mtime 11:21:29, **100 `pyramid`** |
| `DEFAULT_MERGE_BACKEND` | `MergeBackend::Pyramid`, line 389 |
| callers of `pyramid::` | `merge_cmd.rs`, `main.rs`, `blend-truth.rs`, `blend-render.rs` |

Searching every copy on disk for one of **exactly 5579 lines** returns **eleven**,
every one with **zero** `pyramid`, and **not one of them is the repository**:

    tree-ca-6a51e43   tree-d4b8644   tree-lin-0d9fd28   pin-1cacb61   pin-elect
    V-CHROMA\\pin-new  VERIFY-WIRE\\t-parent   vtone-after   vtone-before
    vtone-tree        strehl-pin-ce2c793

Three of those eleven are mine, so I helped build the maze I am complaining
about. The decisive detail is that `git -C <dir> rev-parse --short HEAD` returns
**nothing** for all eleven: they are plain directory copies with no `.git`, so
there is no check an agent can run *inside* one that reveals it is stale. That
fully explains a careful agent reading a real file and being repeatedly wrong
about the product, and it is why four rounds of "89 references at HEAD" changed
nothing.

Runtime proof, from a hashed binary built out of the live tree:

    SHA256 A2A6077B8C97FF20198717572AA4BC32C2A837EF74945FF7288DBE4C6FC6363B
    $ strehl stack D:\\personal\\macro\\coffee-bubbles --out banner.tiff
    merge backend   : pyramid (default)
    strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)
    bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19
    base band       : plain mean across frames

No flags. That is the product command with its defaults.

### 15.2 The acceptance test, run with one binary instead of two

ORCH's design pins two executables -- `strehl.exe` for BEFORE and
`blend-render.exe` for AFTER. That confounds the merge backend with every other
difference between two binaries built at different commits. Since the backend is
now selectable at runtime, a strictly better design is available: **one binary,
one flag apart**, `--merge estimator` against the default `--merge pyramid`, with
every other flag identical by construction.

`--demosaic`, ORCH's own configuration, scored by ORCH's own metric
(`experiments/BUILD-BLEND/zerocount.py`):

| subject | ch | BEFORE @0 | AFTER @0 | delta pt |
|---|---|---:|---:|---:|
| dry-erase-marker-head-cpl | R | 0.0001 | **0.0000** | **-0.0001** |
| dry-erase-marker-head-cpl | G | 0.0000 | **0.0000** | **-0.0000** |
| dry-erase-marker-head-cpl | B | 0.0005 | **0.0000** | **-0.0005** |
| couch-fibers-cpl *(placebo)* | all | 0.0000 | 0.0000 | 0.0000 |

Per-channel minima tell it more directly. The **estimator** arm bottoms out at
`0 / 0 / 0`; the **pyramid** arm bottoms out at `582 / 292 / 89`. The pyramid
merge emits no exact zeros at all on the subject ORCH measured at **+2.36 pt**,
and the sign of the difference is negative in every channel -- it is the arm that
*does not* clip. Both subjects pass, and the placebo does not regress.

### 15.3 A divergence I claimed and now withdraw

Between measurements I reported that `blend-render.rs:611` carries a
`.max(0.0)` the product lacks:

    blend-render.rs:611   let norm = |v, gain| v.max(0.0) * gain * eg / range;
    merge_cmd.rs:5971     let norm = |v, gain| v * gain * eg / range;

**That was wrong, and I withdraw it.** The product clamps the pyramid planes one
call upstream, in `Merged::value` at `merge_cmd.rs:4091`:

    Self::Bands { planes, .. } => planes[band_slot(p)][i].max(0.0),

Different site, same clamp. I compared one file's `norm` against the other's and
concluded from the mismatch without checking whether the clamp had simply moved.
The doc contract on `write_frame` -- *"every line of arithmetic here is copied
from `merge_cmd::write_merged`"* -- is intact. Nothing needs fixing, and the
"real divergence, and it's my bug" I announced does not exist.

### 15.4 So why were ORCH's zeros real?

They were, and section 13 already has the mechanism: their AFTER binary predates
`275fbd17`, the commit that made `Hull::InputRange` the default. Without the hull
clamp the reconstruction goes negative; the `.max(0.0)` -- which is present on
*both* arms and always has been -- pins those negatives to exactly zero, which is
the spike-at-zero-with-no-ramp signature ORCH correctly identified. With the hull
clamp on, the reconstruction is confined to `[min_k, max_k]`, every frame is
already non-negative, so nothing reaches the clamp and no zeros appear. That is
exactly what 15.2 measures.

**ORCH's item B is not a request; it is a description of what shipped.** *"A merge
that estimates a pixel from N frames should not be able to return a value outside
the range those frames span at that pixel"* is `Hull::InputRange`, landed 08-25
23:05. Their instinct and the implemented fix are the same object.

### 15.5 The instrument caught its own bug first

`zerocount.py` returned `+0.0000` on every channel, every subject, every
threshold. A frozen probe and a genuine pass are the same glyph, so it was
commissioned before being believed. The first positive control **failed**:

    planted 12345 exact zeros, counter reports 0
    POSITIVE CONTROL FAILED: counter cannot see planted zeros

The fault was in the control, not the counter: `img[:, :, 2].ravel()` returns a
*copy* for a non-contiguous slice, so the plant never landed in the array being
counted. Writing through `np.unravel_index` instead gives `12345 / 12345` exact.

It also surfaced that the **default (binned) render never approaches zero at all**
-- floor `447-739 DN` -- so the first `+0.0000` was partly "not measurable in this
configuration" rather than "not present". Re-rendering in ORCH's `--demosaic`
configuration is what made the metric live: the estimator arm's minima drop to 0
there. Without the floor check, a pass would have been reported from a render in
which the statistic could not have moved.

*Renders, instruments and controls are committed and re-runnable:
`experiments/BUILD-BLEND/acceptance.ps1`, `zerocount.py`, `zerocommission.py`.*
"""


def main():
    src = io.open(DOC, encoding="utf-8").read()
    if MARK in src:
        print("section 15 already present; nothing to do")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
    print(f"appended section 15 to {DOC}")
    print(f"now {len(io.open(DOC, encoding='utf-8').read().splitlines())} lines")


if __name__ == "__main__":
    main()
