"""Fold M106-freeze's attribution. The largest corpus-scoping fold of the night.
Facts 1379-1384, disciplines 687-689.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1379, "**THE BYTE-FREEZE BREAK THAT COMMISSIONED M106 NEVER HAPPENED; ONE OMITTED FLAG PRODUCED IT.** "
           "MEASURED by an independent verifier over 1.9 h. M100's baseline `54A5E20F44255BB526C61D4397D239D6"
           "F1D26A06D54A8A56FBC944B91B37E7A2` **reproduces bit-for-bit at HEAD** and at all 8 commits from "
           "`885e9f7` onward. The reported `CF266004...` came from adding `--gate 2` to a baseline rendered at "
           "`DEFAULT_GATE = 4.0` (`merge.rs:297`); M100's B1 command (`verify3.ps1:32`) passes **no `--gate`**. "
           "M100's own preserved binary yields `CF266004...` with the flag and `54A5E20F...` without it, on "
           "demand. The dispatch's premise was wrong twice over: its three candidate commits are all "
           "**ancestors of** the baseline, and two of its named candidates touch no `crates/` file at all.",
     "**The orchestrator commissioned a 1.9-hour regression hunt into a regression that did not exist, by "
     "splicing one milestone's flag onto another milestone's command.** The error is not carelessness about a "
     "flag; it is that **no freeze in this project recorded the invocation that produced it**, so there was no "
     "way to notice the splice. Every ingredient of the false alarm was available in advance and none of it was "
     "written down next to the hash. Note the shape: the fabricated comparison was **internally consistent** -- "
     "same binary, same stack, same frame count, a clean-looking hash mismatch -- and nothing about it "
     "announced that the two sides had been rendered under different gates.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED, 6764 s); `docs/research/M106-freeze-attribution.md`"),

    (1380, "**THE ALIGNMENT WATERSHED: `885e9f7` (M86c, `2026-08-24 03:15:23`) MOVES EVERY PIXEL OF THE DEFAULT "
           "RENDER, AND IS THE ONLY COMMIT IN RANGE THAT DOES.** MEASURED: M85's frozen `41974F2AA2187C63CE3031"
           "813BD51F7D1A0B6EB4972EDF1F7F1684E2D429F699` at 49 449 626 bytes reproduces **exactly** at `c24e347` "
           "(pre-M86c) and renders `D1D5C51726762015D76F0C3DE75F44C9CB679974B9DA4D5BEA67B31CD4CF1256` at HEAD. "
           "Magnitude: max **36 107 DN**, RMS **3594.7581**, and **8 241 501 of 8 241 504 pixels** differ. The "
           "log gains `alignment : ON (solved), reference frame 149, 299 placed / 0 refused`. M87 `52c6a52`, "
           "M97 `79dc8b3`, M95 `56bd846` and the exposure patch `925d03d` are each **hash-inert**, confirmed "
           "independently.",
     "**The single most important scoping fact in the corpus: any quality number measured before "
     "`2026-08-24 03:15:23` describes an UNALIGNED merge, and anything after describes an aligned one.** Every "
     "cross-milestone comparison must check which side of that line its baseline came from. The break is "
     "**intended and correct and must not be reverted** -- wiring alignment in is the quality improvement the "
     "project exists to make. The line sits **before** M100's baseline, so the recent milestones are mutually "
     "consistent. **Recorded precisely rather than as a round number:** the verifier reported "
     "`100.0000%` of pixels differing, but the underlying counts are 8 241 501 of 8 241 504 -- **three pixels "
     "did not move**, which rounding hides. Per discipline 600 the raw counts are the record; a rare-path "
     "residue of exactly three pixels is the kind of detail a percentage destroys.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED); raw counts preserved by ORCH"),

    (1381, "**THE SOURCE CODE CITES A PROOF THAT NO LONGER REPRODUCES.** MEASURED: `merge_cmd.rs:2958-2971` "
           "states that `docs/research/M85-output-correctness.md` *\"carries the SHA-256 proof that it still "
           "emits the identical bytes.\"* That proof (`M85-output-correctness.md:172-178`) is the "
           "`41974F2A...F699` hash which stopped reproducing at `885e9f7`. **NOT FIXED** -- `merge_cmd.rs` is "
           "held by another agent.",
     "**A comment whose textual claim is true and whose artifact claim is false, which is the hardest kind to "
     "notice.** The verifier was careful here and the nuance is worth preserving: the **encode closure itself "
     "is textually unchanged** across `c24e347..519203f`, so the comment's assertion about the encoder is "
     "accurate; M86c changed the merge's **input**, not its arithmetic. What broke is the *evidence* the "
     "comment points at, not the property it asserts. **A citation to an artifact is a dependency, and nothing "
     "in the build knows about it** -- which is precisely the gap M108-freeze-test was commissioned to close. "
     "M85's own P12 (*\"the corpus's ~1138 facts remain valid\"*) was true when written and is now stale by the "
     "same mechanism.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED); fix deferred on file contention"),

    (1382, "**THREE MILESTONES FROZE THREE DIFFERENT INVOCATIONS AND NONE RECORDED THE COMMAND BESIDE THE "
           "HASH.** MEASURED inventory: M85 `bee-3-cpl` / 299 frames / `--gate 2` -> `41974F2A`; M100 "
           "`--limit 60` / **no gate** -> `54A5E20F`; M95 `coffee-bean --limit 20 --gate 2.0` -> `D99F5D82`. "
           "Three hashes, three pipelines, no cross-reference between them anywhere in the corpus.",
     "**This ambiguity is the direct and sufficient cause of fact 1379's false alarm**, and it will recur until "
     "the registry is data rather than prose scattered across three reports. The deeper point is that a hash "
     "without its invocation is **not a weak record, it is not a record at all** -- it cannot be reproduced, "
     "cannot be falsified, and cannot be distinguished from a different pipeline's hash. Freezing everything is "
     "equivalent to freezing nothing; the corpus needs a small number of deliberately chosen invocations, each "
     "carrying stack, limit, gate, alignment mode, byte count, and **the commit and reason for its last "
     "re-baseline** -- that last column being the one that would have prevented tonight's investigation.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED); commissioned as M108-freeze-test"),

    (1383, "**`StackIdentity::from_paths` DIGESTS FILENAME AND FILE LENGTH ONLY, NEVER CONTENT** "
           "(`warpmap.rs:238`), while `load_or_solve` (`align_cmd.rs:894-953`) both reads and **writes** "
           "`warpmap.txt` into the capture directory. The verifier observed that file's contents change three "
           "times within one session.",
     "**Sharpens fact 1367 from a race into a validation gap.** Two different solves of the same bracket "
     "produce identical filenames and identical file lengths, so the identity check passes on a sidecar that "
     "came from a different reference frame, a different subset, or a different resampler. Combined with the "
     "cache-back write, a 'frozen' render can silently change without any command, any commit, or any flag "
     "changing. **A digest that ignores content is a checksum of the directory listing, not of the data.**",
     "M106-freeze verifier `a7cf3e3e` (MEASURED source read plus observed mutation)"),

    (1384, "**ELEVEN STRAY SIDECARS WERE SITTING INSIDE THE READ-ONLY CAPTURE LIBRARY; QUARANTINED.** MEASURED "
           "at `bdfd12c`: `D:\\personal\\macro` contained `warpmap.txt` in 11 stack directories, sizes 1 560 B "
           "to 40 830 B, timestamps spanning `03:12` to `09:38`. **`bee-3-cpl\\warpmap.txt` was 1 560 B and "
           "held a 40-frame solve for a 299-frame bracket.** All 11 moved to "
           "`C:\\dev\\strehl-out\\ORCH-quarantine-sidecars\\`; verified afterwards that 0 sidecars remain, "
           "`bee-3-cpl` retains its 299 ARWs and all 24 stack directories are intact.",
     "**The hazard of fact 1367 was not hypothetical and its worst instance was on the flagship stack.** Any "
     "`stack` run on `bee-3-cpl` that picked up that file merged **40 frames while reporting a 299-frame "
     "bracket**, and the corpus has no way to identify retrospectively which runs those were. Quarantined "
     "rather than deleted so the forensic record survives. **Nothing was restored to the library and nothing "
     "should be** -- a re-solve is slower and correct, a stale sidecar is fast and wrong.",
     "ORCH (MEASURED at `bdfd12c`; broadcast to all 7 live agents)"),
]

DISCIPLINES = [
    (687, "**Record the entire invocation beside every frozen hash -- directory, limit, and every flag "
          "INCLUDING the ones left at their default.** \"We used the default\" is not a record, because "
          "defaults move and because the next reader cannot tell a default from an omission. One absent "
          "`--gate` on a `DEFAULT_GATE = 4.0` pipeline manufactured a hash mismatch that was internally "
          "consistent in every other respect and cost a 1.9-hour investigation. Facts 1379, 1382."),
    (688, "**An untested freeze is an unverified freeze.** Every byte-freeze in this project was enforced by "
          "prose in a report; one of them went stale for weeks while being cited *in the source code* as live "
          "proof. A citation to an artifact is a dependency and nothing in the build knows about it. The test "
          "must make intended change **visible and deliberate**, not prevented -- most moves here are "
          "improvements, and a golden test that only says \"assertion failed\" gets silenced by the third "
          "person who hits it. Facts 1381, 1382."),
    (689, "**When a freeze breaks, verify the command before investigating the code.** Re-render the baseline "
          "with its own recorded invocation first; only then diff commits. The corpus's one instance ran the "
          "search in the opposite order and spent 1.9 h bisecting eight commits, three of which were ancestors "
          "of the baseline and two of which touched no `crates/` file. Fact 1379."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1378 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^686\. ", l))
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
    print(f"folded facts 1379-1384 after line {fact_idx}, disciplines 687-689 after line {disc_idx}")


if __name__ == "__main__":
    main()
