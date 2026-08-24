"""Fold 37 -- mark the completed milestones in the AGENTS.md ledger."""
import io

AG = "AGENTS.md"
ag = io.open(AG, encoding="utf-8").read()

EDITS = [
    # M87 -- shipped and argued against.
    ("**live (`01de8fd8`, `claude-opus-5`)** |",
     "**complete (`01de8fd8`, `claude-opus-5`), folded as facts 1275-1278 and "
     "disciplines 625-627.** Went far past its Python-prototype brief and "
     "**shipped the correction into the product** -- "
     "`crates/strehl-cli/src/merge_cmd/halo.rs`, a third pass reached by "
     "`STREHL_FIX_HALO=1`, leaving the default output byte-for-byte unchanged "
     "-- **and then recommended against enabling it.** On ground truth it cuts "
     "the halo metric **79.8%** and raises RMSE against truth **254.6%**; at "
     "product scale it erases the bee's abdomen hairs while its own metric "
     "reports a **72.9%** improvement. *\"The metric and the eye disagree, and "
     "the eye is right.\"* Its no-occlusion control is what proved it: the "
     "correction moved **85.4%** of pixels at a planted non-occluding disc "
     "against **82.1%** at a real occluding edge. The owner's two-layer "
     "physics is vindicated on a plant (halo -78.8%, band RMSE 3.46% -> 1.82%, "
     "the noise floor) and misses its registered -50% bar on real captures at "
     "**-28.2%**. Also established, quantitatively, that **the halo is not a "
     "misregistration artifact**. |"),

    # M92 -> answered a better question, then audited the blast radius.
    ("**live (`5faca810`, `claude-opus-5`)** |",
     "**complete (`5faca810`, `claude-opus-5`), folded as facts 1239-1249 + "
     "1267-1270 and disciplines 607-609 + 617-620.** Returned NOT ESTABLISHED "
     "on the question asked and answered a better one on the way past: M57's "
     "**0.34310 px** null -- the bound M82 froze and two milestones carried as "
     "the reason this project could not measure sharpness -- is a **single "
     "draw, not a variance**, measured with **1.7587x too much injected "
     "noise** because three scripts set `ISO = 500` on an ISO-160 stack. "
     "Corrected, it is **0.089-0.094 px** and M82's effect is readable at "
     "**N = 1**. Then, as **M92b**, priced the blast radius: of **254** "
     "sensor-constant assignments across 165 files, **31** disagree with EXIF "
     "and **exactly 3** are defects -- 20 feed the deliberately frozen detail "
     "operator where disagreement is rule 15 working, and 4 define synthetic "
     "plants. Shipped an EXIF-reading registration-time guard, RED on exactly "
     "those 3, controls **16/16** including two planted non-defects it "
     "correctly ignored. Reported two defects in its own scanner rather than "
     "fixing them quietly. Reassigned to **M102**. |"),

    # M97 -- the finding of the night.
    ("**live (`798b72bd`, `claude-opus-5`).** The critical path to the owner's "
     "morning. |",
     "**complete on its own lane (`798b72bd`, `claude-opus-5`), folded as "
     "facts 1271-1274 and disciplines 621-624.** Delivered the wiring and then "
     "found something bigger. The **wiring is correct** -- right sign, right "
     "per-CFA-plane handling, surviving an identity placebo, a wrong-stack "
     "control and a whole-frame NaN sweep with an 18-px plant recovered at "
     "0.00000% black. But **the solve behind it applies only 50.2% of the "
     "drift**, leaving **150.2 plane px** of misregistration on `bee-3-cpl`, "
     "which is why wiring alignment in bought only ~3%. Truth measured twice "
     "with no shared code (0.85714 / 0.85715). Also: **M86 §4.2's stated sign "
     "is wrong** (the subject shrinks); its own detail metric was "
     "**disqualified by its own responsiveness control**, the third "
     "independent death of gradient-energy sharpness; coverage is **~13%, not "
     "the 26% I briefed**; and it measured a real **torn sidecar read** with "
     "agents live in one tree. Defect 3 handed to **M103**. |"),
]

for before, after in EDITS:
    n = ag.count(before)
    assert n == 1, "ledger anchor occurs %d times, need 1: %s" % (n, before[:70])
    ag = ag.replace(before, after, 1)

io.open(AG, "w", encoding="utf-8", newline="\n").write(ag)
print("AGENTS.md: M87, M92, M97 marked complete")
