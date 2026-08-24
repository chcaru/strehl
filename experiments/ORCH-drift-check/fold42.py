"""Fold M97's alignment verification and the corpus-pollution defect.

Facts 1295-1296, discipline 636.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1295, "**THE ALIGNMENT SOLVE APPLIES ONLY 54.3% OF THE DRIFT THAT IS PRESENT, AND THE SIGN IS CORRECT.** M97, "
           "against the orchestrator's independent ground truth: true scale span **0.85714**, sidecar span "
           "**0.92241** (54.3% of it), predicted residual 0.92924 from the sidecar alone, **measured residual "
           "0.92887** = **150.2 plane px** -- two independent routes agreeing to **4e-4**. Sign confirmed by gathering, "
           "not by argument: SELF 0.99997, RAW 0.85714, AS-IS 0.92887, and an **inverted plant moves away to 0.78811 "
           "(1.48x raw drift)**, so the test can see a sign error and there is not one. `T_usable` is 4.0 px.",
     "**`E*` = 11.56 px cannot detect this**: a held-out *pairwise* residual is blind to a common multiplicative gain "
     "error, which is why the shortfall survived every previous check. M86's own P8 called the direction and "
     "estimated 12-16%; measured, it is **46%**. M97 withdrew its own DERIVED \"the merge is already robust to smooth "
     "drift\" mechanism when this killed it, and separately disqualified its own detail metric after a plant showed "
     "misregistration *raises* it. **Reconciles with fact 1279's ~1 px of smear reaching the photograph**: the frames "
     "that win a given pixel cluster in index, so the render is smeared by the displacement spread *within the "
     "competitive set*, not by the stack's end-to-end drift. 150 px is the right number for the solve; 1 px is the "
     "right number for the picture. **M86 §4.2's prose contradicts M86's own sidecar** -- a documentation error, not a "
     "code error.",
     "M97 (MEASURED, sign resolved by rendering; ORCH ground truth independent); "
     "`docs/research/M97-warped-merge.md`, `experiments/ORCH-drift-check/drift2.py`"),

    (1296, "**STREHL WROTE 11 CACHE FILES INTO THE OWNER'S READ-ONLY PHOTO LIBRARY, AND THE WRITE IS NOT ATOMIC.** "
           "Rendering a bracket caches its solve as `warpmap.txt` *inside the capture directory*. Inventory of "
           "`D:\\personal\\macro`: `bee-2-cpl`, `bee-3-cpl`, `coffee-bean`, `flat-on-ruler-cpl`, "
           "`flower-bud-alone-cpl`, `flowers-cpl`, `foam`, `lavendar-cpl`, `lead-1-cpl`, `leaf-2-cpl`, "
           "`tweezers-cpl` -- all dated today, 03:12 to 06:03. Every other non-RAW file there is the owner's own and "
           "predates the project. M97 observed a **torn read** at 04:53:20, getting `reference 30` with no frame 298 "
           "while a sibling rewrote the same file.",
     "Two defects, not one. The **location** is the real one: derived data must never land beside someone's RAW "
     "files, and temp-plus-rename alone would only make the pollution atomic rather than absent. The "
     "**non-atomicity** is the acute one, because `WarpMap::load`'s behaviour on a truncated file is **not "
     "verified**, so a torn read may have silently fed a wrong registration into some render tonight. Deletion is "
     "deliberately deferred until the tree is quiet -- removing a sidecar under a live render would make another "
     "milestone re-solve mid-flight or read a half-deleted file -- and must then be done by those 11 exact paths, "
     "never by a recursive pattern.",
     "M97 (escalated), ORCH (MEASURED inventory); `docs/research/M97-warped-merge.md` §11"),
]

DISCIPLINES = [
    (636, "**Never cache derived data in the directory you read the inputs from, and treat a read-only corpus as an "
          "invariant the code enforces rather than one the operator remembers.** Every agent tonight was told "
          "`D:\\personal\\macro` is read-only; eleven cache files landed there anyway, because the *program* wrote "
          "them and no one had told the program. The failure is structural, not one of discipline: an instruction "
          "given to agents cannot bind a binary they invoke. Two consequences worth carrying: derived state belongs "
          "in a location derived from the *output* path, never the input path; and any file multiple processes may "
          "write must be temp-plus-renamed, because with enough concurrency a torn read is not a race you might lose "
          "but the steady state. Fact 1296."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1294 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^635\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1295-1296 after line {fact_idx}, discipline 636 after line {disc_idx}")


if __name__ == "__main__":
    main()
