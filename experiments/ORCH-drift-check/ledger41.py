"""Rule 41: record the milestone allocations I dispatched without recording."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\AGENTS.md"

ROWS = {
    "M107": (
        "**THE FRINGING IS OPTICAL, NOT ALGORITHMIC, AND THE CORRECTION IS BUILT AND CONNECTED TO "
        "NOTHING.** Lateral chromatic aberration measured at **−704.5 ppm** with `R^2 = 0.9969` (fact "
        "1414) lives in `optics.rs` alongside the owner's own gear profile "
        "`A7C2_FE100GM_2XTC_X4CPL` -- and `unwired.py` established that **every reference to any of it "
        "is inside `optics.rs` itself** (fact 1449). Commissioned to wire it into the render behind "
        "`STREHL_FIX_CA=1` rather than stall on whether the coefficient transfers across "
        "configurations. **Upgraded mid-flight** once fact 1452 composed three findings: the shipped "
        "`catmull-rom` kernel has been suppressing this fringing *with blur*, so CA correction is a "
        "**prerequisite** for the sharper kernel rather than an independent corner tidy-up. Owns "
        "`optics.rs` and `color.rs`.",
        "`crates/strehl-core/src/optics.rs`, `docs/research/M107-chroma.md`",
        "dispatched, running (`7a67196e`, `claude-opus-5`); independently verified by `M107b` "
        "(`69c2cc86`), whose cache-key contamination audit came back **not contaminated** (`d63f187`). "
        "**Asked late in the night whether its radial coefficient has the support to justify itself**: "
        "M109 measured that the `marker` frame's outer field is empty of both clipped highlights and "
        "bright edges (fact 1458), and a radial term is most load-bearing exactly where a macro subject "
        "usually has nothing in frame. Question put as a question -- I have not measured its fit.",
    ),
    "M108": (
        "**HOLD THE BYTE-FREEZE HONEST WHILE SIX AGENTS EDIT THE RENDER PATH.** Companion to M106's "
        "attribution work: the frozen no-flag render is the substrate every quality number in the "
        "corpus is measured against, and it is being edited concurrently by agents who each believe "
        "their own change is inert.",
        "`crates/strehl-cli/tests/byte-freezes.tsv`, `docs/research/M108-freeze-test.md`",
        "dispatched, running (`7a5cb475`, `claude-opus-5`). The registry is **append-only**: add a row, "
        "never modify one.",
    ),
    "M109": (
        "**THE SHIPPED DEFAULT RENDERS BLOWN HIGHLIGHTS MAGENTA.** Fact 1432: `strehl stack` puts "
        "**2.002 %** of the frame into magenta with green pinned **0.10** below red and blue, where a "
        "blown highlight must be neutral -- grossly visible, and part of what the owner was reacting to "
        "when he said his stacks did not look good. Viewing-path only: the byte-frozen measurement "
        "output must not move, and an unsaturated stack must be byte-identical afterwards.",
        "`crates/strehl-core/src/color.rs`, `docs/research/M109-highlights.md`, "
        "`experiments/M109-highlights/`, `C:\\dev\\strehl-out\\M109\\`",
        "**complete (`dfe3917b`, `claude-opus-5`), folded as facts 1455-1458 and disciplines 738-744.** "
        "Located the mechanism -- **the only clamp is *after* the colour matrix**, by which point a "
        "known-wrong green has already been mixed into red and blue -- and fixed it pre-matrix at "
        "`K0 = 1.0689`, conditional so the null is an identity by construction. **0.3378 % to 0.0944 %** "
        "on `argmax-baseline`, byte-identical null, negative control shown red, freezes 5/5, workspace "
        "394/0. **Then could not land it, because `merge_cmd.rs` belongs to M97** -- routed by me as a "
        "priority insert. Left a failed bar failed rather than retro-fitting it; **corrected my causal "
        "claim by measurement** (auto-exposure *amplifies* the defect **2.8x**, it does not cause it); "
        "**declined to ship the better-looking aggressive variant because the corpus cannot falsify "
        "it**, which is registered as captures section 25. Its radial null returned **+1.0000 on "
        "uniform-random data** and caught a tautology that would otherwise have entered the corpus as a "
        "measured result.",
    ),
    "M110": (
        "**REGULARISE THE ALIGNMENT PLACEMENT TRACK**, then -- re-tasked -- **land the Lanczos-3 "
        "resampler variant that fact 1420 said was blocked on file ownership.**",
        "`crates/strehl-core/src/align.rs`, `experiments/M110-sheet/`, `docs/research/M110-*.md`",
        "**complete on its own lane (`08e474c9`, `claude-opus-5`), folded as facts 1453-1454 and "
        "disciplines 736-737, 741.** Reported **\"nothing to land\"** and was right: M95 had already "
        "landed the variant at `843f6e1`, an ancestor of `HEAD`, with the default correctly unmoved at "
        "`catmull-rom`. **Fact 1420 was stale and I dispatched an agent to do work already in `HEAD`.** "
        "It also **refuted my clippy attribution** -- I had told the whole fleet the workspace failure "
        "was its uncommitted `align.rs` work, when the errors are in `robust.rs` and `optics.rs`, "
        "**inside the lanes of two agents I had told to ignore them.** Its P10 finding that *an "
        "archived render has a shelf life of minutes in a shared tree* generalised into discipline 741. "
        "Re-tasked to build a **self-dating 1:1 comparison-sheet harness** so the owner has images to "
        "judge that carry the commit and binary hash that produced them.",
    ),
    "M112": (
        "**STOP THE +7.35 % OUTPUT ENLARGEMENT AND SEE IF THE PIXELS COME BACK.** `fit_to_cover` "
        "enlarges every output pixel to cover the warped frame set, and facts 1287/1289/1400 priced "
        "that rescale as the majority of the merge's sharpness deficit. Phase 0 go/no-go with a "
        "pre-registered stopping rule before phases 1 and 2 could be built.",
        "`docs/research/M112-real-pixels.md`, `experiments/M112-real-pixels/`",
        "**complete (`ceb90aa7`, `claude-opus-5`), folded as facts 1459-1461 and disciplines 745-746. "
        "NO-GO, and `crates/` was never touched.** The crop recovers **−0.0030 dex -- the wrong sign**; "
        "**8 of 9 stacks dead.** Then resolved the standing 1287/1420 tension that I could not: the "
        "rescale is a **sufficient but redundant** cause, costing full price in isolation "
        "(**+0.1836 to −0.0000** on the reference frame) yet recovering nothing stack-wide because "
        "**99.7 %** of frames are already non-integral. **So fact 1287's share is an attribution, not a "
        "budget, and is not recoverable by anyone.** It also **found the provenance defect in facts "
        "1419/1420**: the \"9.4x\" multiplier divides by a quantity measured on an **8-frame quarantined "
        "sidecar**, not the shipped 299-frame solve -- making my conclusion right and *understated*. "
        "**Refused my invitation to re-register its bar** because the invitation arrived after the data "
        "did, and **caught my null as misdesigned in advance** (it fires at +0.1851 dex and would have "
        "voided a correct measurement).",
    ),
    "M113": (
        "**TRY TO KILL FACT 1420, WHICH I HAVE ALREADY ACTED ON.** The kernel A/B is a comparison "
        "between resamplers, and `resampler` is precisely one of the two fields `StackIdentity` fails "
        "to key on (fact 1446) -- **the single most cache-exposed measurement in the project.** Beyond "
        "that: a high-band power statistic **rises with ringing**, Lanczos-3 rings **9.902x** "
        "Catmull-Rom, and twice in one day a sharpness scalar has preferred an image inspection "
        "rejects. **The likeliest refutation is that the metric is rewarding ringing and calling it "
        "sharpness.** Read-only with respect to `crates/`.",
        "`docs/research/M113-kernel-verify.md`, `experiments/M113-kernel-verify/`",
        "dispatched, running (`98b0ec74`, `claude-opus-5`). **Scope extended mid-flight** by M112's "
        "provenance finding: it must now establish **which frame set and `stack-digest` fact 1420's "
        "arms were measured on**, since a kernel gain measured on a quarantined 8-frame sidecar would "
        "describe a stack the owner has never rendered. Given a second discriminator that costs one "
        "pass -- **a real resampler property should be roughly stack-independent, whereas ringing "
        "depends on edge density** and `bee-3-cpl` is wall-to-wall hairs.",
    ),
}


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    def row_index(mid):
        pat = re.compile(r"^\| `" + mid + r"` \|")
        hits = [i for i, l in enumerate(lines) if pat.match(l)]
        return hits[0] if hits else None

    m111 = row_index("M111")
    assert m111 is not None, "M111 row not found -- anchor the insert somewhere real"

    before = ["M107", "M108", "M109", "M110"]
    after = ["M112", "M113"]

    def build(mid):
        brief, arte, status = ROWS[mid]
        r = f"| `{mid}` | {brief} | {arte} | {status} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"{mid}: {k} unescaped pipes, expected 5"
        assert row_index(mid) is None, f"{mid} already has a ledger row"
        return r

    pre = [build(m) for m in before]
    post = [build(m) for m in after]

    out = lines[:]
    out[m111 + 1:m111 + 1] = post
    out[m111:m111] = pre
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"added ledger rows: {', '.join(before + after)}")


if __name__ == "__main__":
    main()
