"""Repair the AGENTS.md milestone ledger: M101-M104 were dispatched and never recorded.

Rule 41 violation, the orchestrator's. M101 reported it in its own section 0.2
after finding its brief also violated rules 40 and 43.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\AGENTS.md"

ROWS = [
    ("`M101`",
     "**THE SENSOR HAS PERMANENT DEFECTS AND THE FOCUS MEASURE LOVES THEM.** `box_mean_27` of the Sobel magnitude "
     "over sigma is a local energy detector and a hot pixel is a local maximum of gradient energy, so the election "
     "has a systematic reason to prefer whichever frame puts a defect on the pixel being decided; defects are fixed "
     "in **sensor** coordinates while the scene translates up to **232.7 plane px** under breathing, so a single "
     "hot pixel is a candidate to produce a **trail**, not a dot. Build the map, run the deciding measurement, and "
     "build the correction **only if** the deciding measurement justifies it.",
     "`docs/research/M101-defect.md`, `experiments/M101-defect/`",
     "**complete (`60d14fb`, `claude-opus-5`), folded as facts 1313-1322 and disciplines 647-654. NEGATIVE RESULT; "
     "NO CORRECTION SHIPPED and `defect.rs` was not written.** The election lands on defects at **exactly chance** "
     "(z = 0.24, enrichment **0.987x** against a 1.5x bar, flat across five brightness decades), and **the trail "
     "does not exist**: the geometric drag is real at 97.7 px median, but alignment *reduces* a defect's deposit "
     "(0.931 px against a 0.937 shift null, 1.000 on an identity arm) rather than smearing it -- **the opposite of "
     "what M22 section 7 and M48c fact 30 both pre-registered.** The bridge: planting 320 synthetic hot pixels shows "
     "the election turns on between **100 and 250 DN**, predicted in advance from the shipped arithmetic, and real "
     "defects are **1.5 DN = 0.0084 sigma** of the focus noise floor. It also **corrected two published censuses** "
     "-- R and G1 defect detections do not reproduce at all (split-half Jaccard 0.077 / 0.074 against a placebo of "
     "0.000) -- and settled a fork the calibration set could not: what the darks measure is a **fixed per-site "
     "offset**, not dark current. **Its brief was mine and it was defective**: it named none of M22, M48c, M29 or "
     "M48, in violation of rules 40 and 43, and asserted a read-noise constant that is not shipped. M101 caught "
     "both by searching `docs/research/` on its own initiative before measuring. Fact 1322."),

    ("`M102`",
     "**BUILD THE CALIBRATED SIMULATOR** -- the one artifact that compounds with everything else. Four plants have "
     "been caught by author vigilance in a week (disciplines 611, 615, 616, 620), which is *luck with good habits, "
     "not a system*, and does not scale to contributors. Generate synthetic focus stacks physically faithful to this "
     "rig from constants the corpus has already measured: latent scene with known depth including a genuine "
     "occlusion and a smooth low-texture region, the measured breathing warp, defocus composed with diffraction at "
     "the measured `N_eff`, **CFA sampling not RGB**, the calibrated signal-dependent noise read from EXIF via its "
     "own guard, and the measured photometric drift. Told that **a simulator nobody can falsify is a random number "
     "generator with good manners**, and that a section titled *where this simulator lies* is a required deliverable "
     "I would judge it on more than the agreement figures.",
     "`experiments/M102-simulator/`, `docs/research/M102-simulator.md`, `C:\\dev\\strehl-out\\M102\\`",
     "**complete (`28e0b35`, `claude-opus-5`), folded as facts 1329-1332 and disciplines 656-658. VERDICT: NOT "
     "ESTABLISHED, on its own registration.** It had registered that if a defect plant fails to redden the "
     "round-trip is not a check -- **both plants failed, and neither failure was the instrument's.** D1's bar "
     "**equalled the plant it was meant to detect** (recovered -1.0000 exactly against a bar of 1.0). D2 sized a "
     "geometric plant against the **sensor** rather than the scene and was therefore below the depth "
     "autocorrelation length; swept, it reddens at 2.91 depth-slab widths. Everything else is green: round-trip "
     "median error **0.0000**, 97.94% within +/-2, all three realism bars, index map bit-identical under a no-op. "
     "**Two results beyond the brief:** the calibrated noise model predicts real `bee-3-cpl` per-frame noise to "
     "**0.54%**, and the aligner was scored against truth for the first time at **96.96%** recovery -- which the "
     "orchestrator suspects is circular, since M102's own section 6 records that it planted a **linear** breathing "
     "track and section 7 names the track's curvature as the missing capture. It chose out-of-tree DNG generation "
     "and justified it by measurement: its first synthetic file decoded **exit 0, \"3 ok, 0 failed\"** while "
     "reporting an active area of 3737911296 x 646971392. Its noise estimator returned **exactly 0.000** on all 32 "
     "synthetic frames and was caught only because the same function returned 0.9946 on the real stack in the same "
     "run."),

    ("`M103`",
     "**THE SOLVE APPLIES ROUGHLY HALF THE DRIFT, AND THAT DEFECT IS NOW CONFIRMED BY FOUR INDEPENDENT ROUTES** -- "
     "M97 by rendering, the orchestrator against ground truth, M87 by decoding the f64 warps to a span of 0.922414, "
     "and M97b by an arm ladder. Handed down as M97's defect 3. Ship the gain correction in the solver.",
     "`crates/strehl-core/src/align.rs`, `docs/research/M103-halfdrift.md`, `experiments/M103-halfdrift/`",
     "**dispatched, running (`ef314fb4`, `claude-opus-5`).** Re-briefed once M97b priced the payoff: gain-correcting "
     "the solve is a **19-32% sharpness win** with the seam confound planted and running against the result, making "
     "it a lower bound (fact 1325). Given two constraints from the same night: M102's 96.96% synthetic recovery may "
     "be circular on a linear planted track, so **the fix may need to be per-frame rather than a scalar**, and "
     "**cycle consistency under-states real alignment error by ~6x**, so any bar resting on it is six times looser "
     "than it reads. Told to design against the **waxy smeared blobs** M97b saw in bright low-texture regions of the "
     "gain-corrected render. Barred from verifying its own fix."),

    ("`M104` / `M104b`",
     "**VERIFY THE SHARPNESS FIXES SOMEONE ELSE BUILT.** Stem yielded from `M101` mid-flight rather than argued "
     "(discipline 644), then suffixed to `M104b` for the demosaic arm rather than risk a third numeric collision. "
     "Phase 1: price the `fit_to_cover` rescale by planting the actual factor. M104b: register a bar for the "
     "demosaic lever before any arm is decoded.",
     "`docs/research/M104-resample-verify.md`, `docs/research/M104b-demosaic-lever.md`, `experiments/M104-resample-verify/`, `experiments/M104b-demosaic/`",
     "**live (`bc09057a`, `claude-opus-5`); Phase 1 folded as facts 1305-1309, M104b's pre-registration as fact "
     "1336.** Phase 1 **corrected the orchestrator's headline number**: planting the real factor on the *render* "
     "reads **+0.1789 dex** where the orchestrator's proxy, gathered on a single rawpy frame, read +0.2392 -- over "
     "by 34%, because a resample costs more on sharper input. It also measured that the cost **does not scale with "
     "enlargement** (flat over a 15x dose range), so reducing the stretch is worth almost nothing and it must be "
     "removed; and that the cost is **entirely high-frequency**, null at the comb and +0.1623 dex near Nyquist, "
     "which is how a +7.35% enlargement of every pixel survived in a shipped pipeline. M104b then **refused the "
     "orchestrator's framing** of the demosaic spread as a free win, on the ground that six of the candidates are "
     "content-adaptive so a band-power ranking rewards hallucination as resolution. Now also holds the independent "
     "verification of M95's default-resolution patch, which the orchestrator applied and must not be the sole check "
     "on."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    idx = max(i for i, l in enumerate(lines) if l.startswith("| `M100` |"))
    header = max(i for i, l in enumerate(lines) if l.startswith("| stem | dispatched to do |"))
    assert header < idx, "header must precede the M100 row"

    rows = []
    for stem, brief, files, state in ROWS:
        row = f"| {stem} | {brief} | {files} | {state} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"{stem}: {n} unescaped pipes, need 5"
        assert not re.search(rf"^\| {re.escape(stem)} \|", text, re.M), f"{stem} already in the ledger"
        rows.append(row)

    out = lines[:]
    out[idx + 1:idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"added {len(rows)} ledger rows after line {idx}")


if __name__ == "__main__":
    main()
