"""Fold the coverage-upsample finding. Facts 1400-1402, discipline 697."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1400, "**EVERY ALIGNED RENDER IS UPSAMPLED, AND ON `bee-3-cpl` THE FACTOR IS 1.0735x.** The tool prints "
           "`coverage : field of view scaled to 0.9315 so that EVERY frame covers every pixel (6.9% of width "
           "dropped, then upsampled to keep the output dimensions)`, and `--help` states `the field of view "
           "shrinks ~7-10%`. `align_cmd.rs:1339` documents the mechanism in its own words: *\"the field of "
           "view shrinks by `k`, and because the output keeps its pixel dimensions the result is upsampled by "
           "`1/k`. The alternative -- cropping the output -- keeps every pixel real but changes the image "
           "dimensions, which would break the byte-frozen measurement path.\"* So a `7032x4688` render "
           "carries about **6547x4365** of real sampling.",
     "**Known, deliberate, documented, and recorded as M86 follow-up work -- this is not a discovery of a "
     "hidden defect but of an unpaid bill.** Its practical weight is larger than 7% suggests, for a reason "
     "the code does not state (ARGUED): a global non-integer scale means **no output pixel is ever a "
     "pass-through**, so the resampler kernel is applied continuously to every pixel of every frame. That "
     "couples this directly to facts 1373-1374, where the kernel was measured at **-0.2360 dex** of "
     "high-band loss and confirmed by eye. **The upsample is part of what makes the kernel choice bite.** "
     "The owner pixel-peeps at 100%, and at 100% they are looking at a 107% view of the real data.",
     "`crates/strehl-cli/src/align_cmd.rs:1339` (source); `merge_cmd.rs:1261`; tool output on bee-3-cpl (MEASURED)"),

    (1401, "**MY SPECTRAL TEST FOR THE UPSAMPLE WAS INCONCLUSIVE, NOT CONFIRMING.** I predicted a break in the "
           "radial power spectrum at exactly `f = 0.9315` of the output Nyquist, above which only "
           "interpolation leakage should survive. MEASURED on two 1024 px sites: **no break at the predicted "
           "frequency**. The profile is flat from 0.80 to 1.00 Nyquist, and the steepest log-slope lands at "
           "`0.865`/`0.875` (gate 4.00) and `0.915`/`0.885` (gate 0.00) -- moving **with the gate**, which a "
           "genuine resampling cutoff cannot do.",
     "**The band where the signature should live is noise-dominated, so the test had no power.** The built-in "
     "control proved it: the gate-0.00 arm carries 3-4x the power of gate-4.00 at every frequency above 0.80 "
     "(`8.75e-08` against `2.20e-08` at the hair site), and the gate provably does not change detailed "
     "content (fact 1393), so that excess is noise filling exactly the band the cutoff should occupy. "
     "**Reported as a null-power test, not as evidence against fact 1400**, whose source is the "
     "implementation itself. A plausible additional filler is demosaic-generated high-frequency content: the "
     "warp acts on CFA planes at 3516x2344 and Malvar-He-Cutler reconstructs at 7032x4688, so the "
     "reconstruction's own broadband error lands above the source Nyquist -- which would also bear on M107.",
     "ORCH `upsample_probe.py` (MEASURED, INCONCLUSIVE -- the control is in the script)"),

    (1402, "**THE STATED BLOCKER ON CROPPING DOES NOT APPLY TO THE VIEWING RENDER.** `align_cmd.rs:1339` "
           "declines to crop because it *\"would break the byte-frozen measurement path\"*. But "
           "`merge_cmd.rs:2750` scopes that freeze precisely: keeping the colour matrix and transfer curve on "
           "one switch *\"is what leaves **the default linear path** byte-frozen for the corpus (M85)\"*. The "
           "`--srgb` path is documented as *\"for looking at, NOT for measuring\"* and **has already been "
           "changed once** -- M95 moved it from binned to full resolution.",
     "**So a crop-to-cover on the `--srgb` render breaks no freeze, and is the cheapest real sharpness gain "
     "currently identified.** It recovers ~7% of linear resolution by *not* interpolating, costs nothing but "
     "a dimension change on an output that is explicitly not measured, and leaves the frozen linear path "
     "textually untouched. Routed to the agent holding `align_cmd.rs`. **Caveat to check before building: "
     "the crop must be applied to the viewing output only, not to the warp map**, because the warp map feeds "
     "both paths and changing it would move the frozen one.",
     "`align_cmd.rs:1339` and `merge_cmd.rs:2750` (source, read directly); `--binned` help text"),
]

DISCIPLINES = [
    (697, "**A predicted structural signature is only a falsifiable test if the band it lives in is "
          "signal-dominated; check that first, with a control that can show the band is full of something "
          "else.** Predicting a resampling cutoff at a named frequency is exactly the right shape of test -- "
          "it can only pass at one place -- but it has no power where noise already fills the band. The "
          "control that revealed this was free: an arm known to change noise but not detail showed 3-4x the "
          "power at the same frequencies, and the apparent 'cutoff' moved with it. Fact 1401."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1399 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^696\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} present"
        rows.append(row)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1400-1402 after line {fact_idx}, discipline 697 after line {disc_idx}")


if __name__ == "__main__":
    main()
