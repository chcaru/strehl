"""Fold M109's standby disciplines: armed harnesses, one-tree A/B, parameterise-don't-duplicate."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

DISCIPLINES = [
    (740,
     "**A harness built to measure a patch must refuse to run when the patch is absent.** M109's "
     "`measure_stack.ps1` exits **2** with *\"`merge_cmd.rs` does not contain the section 6 patch yet\"* "
     "rather than measuring and reporting. Without that guard the harness runs happily against the "
     "**unpatched** path and reports the resulting null as a finding -- *\"the fix made no "
     "difference\"* -- which is indistinguishable from a real negative result and far more damaging, "
     "because it is the kind of negative that gets believed and closes a line of work. **The guard "
     "belongs in the harness, not in the operator's memory**, because the operator running it is often "
     "not the one who wrote it and is frequently running it hours later. Same family as discipline 738: "
     "an instrument that cannot detect its own inapplicability will report confidently on nothing."),
    (741,
     "**In a tree that other agents are editing, build both A/B arms from one tree at one moment, "
     "toggling only a file you own.** The intuitive \"before\" -- a binary built earlier and kept -- is "
     "**confounded**, because a rebuild for the \"after\" also picks up every other agent's edits in the "
     "interval. M109 measured the exact exposure: at its moment of measurement `optics.rs` was **+73** "
     "lines and `robust.rs` **+12** from other agents, so a stored-binary comparison would have "
     "attributed their work to its own patch. Its solution is the right general one: **one tree, one "
     "moment, one toggle, in a file you own** -- here flipping `color.rs`'s ceiling to `+inf`, which is "
     "the negative-control mechanism reused as an A/B arm. **This is the general form of M110's P10 "
     "finding that an archived render has a shelf life of minutes in a shared tree**; the shelf life "
     "applies to binaries and to every artefact derived from them, and concurrency is what creates it. "
     "Restore via `$env:TEMP` and never `git checkout -- <path>`."),
    (742,
     "**Parameterise an existing measurement script for a second arm; never copy it.** A duplicated "
     "script is **a second opportunity to choose a flattering ROI, threshold or crop**, and the "
     "divergence is invisible in the report because both arms cite \"the same\" method. M109 "
     "parameterised `montage.py` and then **proved the refactor byte-neutral** -- defaults reproduce "
     "`575045B5...` and `C38167BD...` exactly -- which is what makes the claim of sameness checkable "
     "rather than asserted. **A refactor of an instrument is itself a change requiring a null**, and "
     "PNG output through `cv2.imwrite` is run-to-run reproducible, so that null costs nothing to run."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^739\. ", l))

    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded disciplines 740-742")


if __name__ == "__main__":
    main()
