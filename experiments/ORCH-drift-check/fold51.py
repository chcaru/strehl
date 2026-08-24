"""Fold the orchestrator's stale-plan catch and the exposure gap. Facts 1338-1340,
disciplines 663-665.

The night's orchestration lesson: my own carry-forward plan named a milestone to
dispatch on data that had already been consumed, and prescribed a change that a
later milestone had measured to be harmful. Both halves wrong. Caught only by
reading the shipped source before writing the brief.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1338, "**THE ORCHESTRATOR'S OWN CARRY-FORWARD PLAN WENT STALE IN BOTH HALVES, AND WOULD HAVE DISPATCHED A "
           "DUPLICATE MILESTONE ONTO ALREADY-CONSUMED DATA.** The plan item read *dispatch the flat-fields "
           "milestone; PRNU kappa must enter `PlaneNoise::variance`, not just a report*. **(a)** The 484 flats were "
           "already consumed -- M71 measured `kappa` from exactly that campaign (fact 1062) and M90 shipped it as "
           "`Prnu::A7C2_MEASURED` with the per-plane table R 0.3102% / greens 0.3096% / B 0.2528%. **(b)** The "
           "prescription was already refuted: `noise.rs:29-40` documents that adding the term to `PlaneNoise::"
           "variance` degrades the prediction to **-12.8% at S = 8000** (fact 1064), which is why it is opt-in via "
           "`variance_with_fixed_pattern` and deliberately excluded from the shared normaliser.",
     "**A carry-forward plan is a memory artifact and decays exactly like a brief written from memory.** Rules 40 "
     "and 43 were written for briefs; this is the same failure one level up, in the document that generates briefs. "
     "It was caught for the same reason M101's defective brief was caught -- the shipped source was read before the "
     "brief was written, not after -- and the cost of missing it would have been an entire milestone re-measuring a "
     "settled constant and then shipping a change measured to be harmful. Compare fact 1322, where the orchestrator "
     "made the mirror-image error and the subordinate caught it.",
     "ORCH (MEASURED against `noise.rs:29-40,132-135,168-174,268-271` and facts 1062/1064); self-disclosed"),

    (1339, "**THE MEASURED EXPOSURE CORRECTION IS NOT IN THE BINARY; IT LIVES ONLY IN AN EXPERIMENT SCRIPT.** A grep "
           "of `crates/strehl-cli/src` for `exposure\\|ev_\\|auto_ev\\|percentile\\|stops` returns **two unrelated "
           "doc comments and no logic**. The correction M100 measured at **+1.54 stops on `bee-3-cpl` and +3.74 on "
           "`lead-1-cpl`** (fact 1293) is applied as a numpy post-process in `experiments/ORCH-drift-check/"
           "gallery.py`, which linearises the emitted TIF, gains `p99.9` to a target of **0.92**, and bisects the "
           "gain down whenever more than **0.5%** of pixels clip.",
     "**`strehl stack --srgb` therefore emits a render 1.5-3.7 stops dark to anyone who is not running the "
     "orchestrator's gallery script.** Fact 1293 called this *almost certainly a larger share of the owner's "
     "verdict than anything in the top octave*, and it was described as already implemented and tested when found "
     "-- but implemented in an experiment is not shipped in a tool. Dispatched as **M105** onto `stack.rs` / "
     "`image_out.rs` / a new `exposure.rs`, which is the path `gallery.py` actually invokes and which touches no "
     "contended file.",
     "ORCH (MEASURED, grep of the shipped CLI + read of `gallery.py`); dispatched to M105"),

    (1340, "**THE OWNER DELIVERED A MATCHED POLARISER PAIR AND A TWO-PASS EXPOSURE RAMP, AND THE PAIR IS "
           "UNCONSUMED.** `D:\\personal\\macro\\flat-fields` holds **484 ARW** in three subdirectories: 360 flats "
           "at ISO 100, f/5.6, 200 mm on an exposure ladder from 1/250 s to 1/5 s run as **two passes** 72 s apart, "
           "plus **`subject-focus-sweep-no-cpl` and `subject-focus-sweep-with-cpl` at 62 frames each** -- same "
           "subject, same ISO, same aperture, same 1/5 s exposure, shot 19 minutes apart. `subject-focus-sweep` "
           "appears nowhere in `docs/research/`; it is named only in `captures-needed.md`.",
     "**This makes open question 193 measurable rather than probable.** That question asks whether `foam` was shot "
     "with the polariser and has stood at *probably* on the owner's own hedged recollection (fact 849); question "
     "193 itself notes that flats shot both with and without the filter give the polariser's transmission in stops, "
     "after which any stack whose exposure is inconsistent with its session neighbours becomes diagnosable. The "
     "matched 62-frame sweeps additionally give the first controlled measurement of what the CPL does to the "
     "*transfer*, not merely to exposure -- no such pair existed when every `-cpl` stack in the corpus was "
     "labelled. Not yet dispatched.",
     "ORCH (MEASURED, EXIF inventory of 484 files, read-only); routed to `captures-needed.md`"),
]

DISCIPLINES = [
    (663, "**Re-read the shipped source before dispatching from your own plan, not merely before writing a brief "
          "from memory.** The orchestrator's carry-forward next-steps list named a milestone to dispatch on the 484 "
          "flat fields and prescribed moving PRNU into `PlaneNoise::variance`. The data had been consumed by M71 "
          "and the prescription refuted by M90, whose reasoning is written in the module header of the exact file "
          "the change would have touched. **A plan written at time T is a claim about the repository at time T, and "
          "it expires.** Rules 40 and 43 bind the brief; this binds the plan that produces briefs. Fact 1338."),
    (664, "**\"Measured and implemented\" is not \"shipped\" -- check which binary path the owner actually "
          "invokes.** The exposure correction was recorded in fact 1293 as *already implemented and tested when "
          "found*, and it was: in `gallery.py`, in numpy, outside the binary. The corpus carried it as solved for "
          "long enough that two subsequent milestones chased sharpness instead. **Before ranking a defect as "
          "addressed, name the executable and the flag the owner runs and confirm the fix is on that path.** This "
          "is the same class as fact 1324, where a real fix was confirmed in general and never checked against the "
          "artefact in hand. Fact 1339."),
    (665, "**Open the render before you describe it to the owner.** The orchestrator opened M97b's side-by-side "
          "rather than relaying its prose, and the bright low-texture regions of the gain-corrected arm show smooth "
          "waxy blobs with hard boundaries occupying a large fraction of one panel -- an artefact M97b reported "
          "honestly but which reads in text as a caveat and on screen as disqualifying. The owner photographs "
          "insects and flowers, which are bright and smooth exactly where this fails. **A sharpness win that melts "
          "highlights is a net loss, and only the image says so.** Routed to M103 as a gate on shipping, with three "
          "candidate mechanisms to separate."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1337 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^662\. ", l))
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
    print(f"folded facts 1338-1340 after line {fact_idx}, disciplines 663-665 after line {disc_idx}")


if __name__ == "__main__":
    main()
