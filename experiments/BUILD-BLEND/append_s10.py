"""Append section 10 (the CLI wiring gate, answered at runtime) to the report."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "10. The CLI wiring gate"

NOTE = """
### 10. The CLI wiring gate, answered at runtime

ORCH reported: *"`crates/strehl-cli/src/merge_cmd.rs` contains **no reference to
it**... The owner cannot get any of this from `strehl stack`."* Treated as the
highest-priority item and checked before anything else.

**The wiring is present and the pyramid is already the default.** Not from a
grep -- from the binary, built at HEAD, running the exact command quoted:

```
strehl stack "D:\\personal\\macro\\coffee-bubbles" --out gate.tiff --srgb --demosaic

merge backend   : pyramid (default)
strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)
bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19
base band       : plain mean across frames
```

Supporting code state: `merge_cmd.rs` holds **89** pyramid references;
`main.rs:858` calls `choose_merge_backend` and `main.rs:893` constructs
`strehl_core::pyramid::MergeConfig`; `DEFAULT_MERGE_BACKEND` is
`MergeBackend::Pyramid`. The escape hatch is the opt-**out** ORCH asked for
(`--merge estimator`), and cross-family flags are refused rather than ignored.

**Why the check disagreed, precisely.** ORCH grepped their pinned tree
`tree-ca-6a51e43`. That pin is commit `6a51e43`, dated **08-25 16:12**. The flip
is `5142ace`, dated **08-26 05:05** -- thirteen hours later. At `6a51e43`,
`merge_cmd.rs` contains **0** occurrences of `pyramid`, exactly as reported.

    git merge-base --is-ancestor 5142ace 6a51e43   ->  NO, the pin predates the flip

So the grep was correct about the tree it was run on, and the tree was stale.
This is worth recording as a method note beyond this instance: a repo-state claim
carries the commit it was read at, or it is not checkable. The same pin produced
the images judged in that message, which is why the *pictures* were current while
the *grep* was not -- `blend-render.exe` was built from it, and the example
carried the algorithm before the CLI did.

**The prescribed base-band fix is also already in place**, and the banner above
is the runtime confirmation rather than another reading of the source: `base band
: plain mean across frames`. `BaseBand::Mean` has been the shipped default since
the module landed; sections 1-2 measured the base band at 100.0% averaged
*before* any change of mine. The remedy cannot be applied because it is already
the state of the code. The bowl lives one level up, in the coarsest *Laplacian*
bands, which is what `mean_coarse` addresses and what the section 4 ladder swept.

**One thing ORCH should take back.** They asked to own `scripts/check-defaults.py`
and record the new switch's provenance themselves. I had already added the
`STREHL_PYRAMID_MEAN_COARSE` entry in `5ce0fd7`, committed hunk-wise so as not to
disturb another lane's 31 staged lines in that file. It is there now; it should
be re-checked or rewritten by its owner rather than trusted from me.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 10;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
