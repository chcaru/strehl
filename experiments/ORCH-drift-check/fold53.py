"""Correct facts 1324 and 1341 in place, and fold the measurement that overturns
both. Facts 1344-1345, discipline 667.

Twice tonight I reasoned about "what the owner saw" from the gallery renders,
and reached opposite wrong conclusions -- first that the binning fix was
irrelevant, then that exposure was the dominant cause. Both rest on the same
false premise. The session record is authoritative and I consulted it third.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

# (unique anchor, replacement) -- each must land exactly once or the run aborts.
AMENDMENTS = [
    ("ORCH (MEASURED, tifffile on the 7 emitted files); near-miss disclosed",
     "ORCH (MEASURED, tifffile on the 7 emitted files); near-miss disclosed -- **BUT THE CONCLUSION IS "
     "OVERTURNED BY FACT 1344**: the gallery is not what the owner judged, so the premise of this row is false "
     "even though its measurement is sound"),
    ("ORCH (OBSERVED, visual inspection of 7 renders; no metric attached)",
     "ORCH (OBSERVED, visual inspection of 7 renders; no metric attached) -- **the attribution of the owner's "
     "verdict to exposure is OVERCLAIMED, corrected by fact 1344**; the observation that the halo dominates the "
     "*current* gallery stands"),
]

FACTS = [
    (1344, "**THE RENDERS THE OWNER JUDGED WERE NOT THE GALLERY, AND THEY CARRIED FIVE DEFECTS AT ONCE.** The "
           "session record settles it: the verdict *\"those stacks don't look too good yet\"* answered a turn in "
           "which the owner was pointed at `C:\\dev\\strehl-out\\*.png`, written **2026-08-23 23:37-23:39**, hours "
           "before `ORCH-gallery` existed. Those files measure **8.24 MP** (`bee3-full.tif` at 3516x2344, exactly "
           "half of 7032x4688 in each direction), and the same turn described them in writing as *binned to half "
           "linear resolution* with *no colour management (hence the grey cast)* and *no alignment*. Direct "
           "inspection confirms a grey cast, dull tone, and **a bright halo tracing every leg, claw and antenna**.",
     "**So the owner's verdict was against binning AND missing colour management AND flat tone AND no alignment "
     "AND the halo, simultaneously** -- five defects, of which M95's binning fix has since removed one and M105 is "
     "now on a second. **This overturns fact 1324**, which argued the binning fix could not explain the complaint "
     "because `gallery.py` passes `--demosaic`: true of the gallery, irrelevant to the images actually judged. It "
     "also **overclaims in fact 1341** the other way. Both rows reasoned from the gallery; neither checked which "
     "artefact the owner was shown.",
     "ORCH (MEASURED: session store turn 13-14 + tifffile on the three emitted TIFs); corrects 1324 and 1341"),

    (1345, "**THE SAME UNVERIFIED PREMISE PRODUCED TWO OPPOSITE WRONG CONCLUSIONS EIGHT HOURS APART.** Fact 1324 "
           "used the gallery to argue the resolution fix was **irrelevant** to the owner's complaint; fact 1341 used "
           "the same gallery to argue the complaint was **substantially exposure**. Both are orchestrator rows, "
           "both were folded and committed, and both are wrong for the identical reason -- neither established "
           "which images the owner had in front of him.",
     "**A premise shared by two conclusions is not corroborated by their disagreement; it is load-bearing under "
     "both.** The disagreement should itself have been the alarm, and was not. The authoritative record -- the "
     "session transcript naming the exact paths and the files' own timestamps and dimensions -- cost one query and "
     "one `tifffile` call, and was consulted only on the third pass, after the wrong conclusion had been committed "
     "twice. This is the fourth instance tonight of a mechanism confirmed in general and never checked against the "
     "artefact in hand, after facts 1297, 1304 and 1324.",
     "ORCH (self-disclosed); the class of facts 1297, 1304, 1324, 1341"),
]

DISCIPLINES = [
    (667, "**Before reasoning about what the owner saw, establish which file he was shown.** The orchestrator twice "
          "folded a conclusion about the owner's verdict from the gallery renders, reaching opposite answers, when "
          "the images he had actually been given were a different set written hours earlier -- binned to 8.24 MP, "
          "uncoloured, unaligned, and haloed. **The transcript names the path and the file carries its own "
          "timestamp and dimensions; both are cheap and both are authoritative.** Owner feedback is evidence about "
          "a specific artefact, and it is worthless as evidence about any other. Facts 1344, 1345."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    for anchor, repl in AMENDMENTS:
        n = text.count(anchor)
        if n != 1:
            raise SystemExit(f"AMENDMENT TARGET NOT UNIQUE ({n}): {anchor[:70]!r}")
        text = text.replace(anchor, repl, 1)

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1343 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^666\. ", l))
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
    print(f"amended 2 rows in place; folded facts 1344-1345 after line {fact_idx}, "
          f"discipline 667 after line {disc_idx}")


if __name__ == "__main__":
    main()
