"""Fold: fact 1420 is stale, my clippy misattribution, and the correction to discipline 734."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1453,
     "**FACT 1420 WAS STALE AND I ACTED ON IT FOR HOURS: THE LANCZOS-3 VARIANT WAS ALREADY LANDED.** "
     "Fact 1420 said *\"the blocker is file ownership, not evidence... sequencing it, rather than "
     "measuring it further, is the remaining work.\"* M95 had cleared that blocker itself, in commit "
     "**`843f6e1`** (*\"M95 arm 9: Lanczos-3 lands switchable, default unchanged at catmull-rom\"*). "
     "**Verified by me directly, not relayed:** `git merge-base --is-ancestor 843f6e1 HEAD` returns **0**; "
     "`align.rs` carries `lanczos3_weights` (2728), `sample_lanczos3` (2766), `Resampler::Lanczos3` "
     "(2793, 2803, 2814) and a DC/interpolation unit test (3556); `align_cmd.rs:84` still reads "
     "`default_value = \"catmull-rom\"`. M110 independently reports the byte-freeze suite **5/5** and the "
     "patch's controls **4/4** with C4 at **0.6466 vs 0.4488** — fact 1420's exact digits.",
     "**So the largest measured quality win was never actually blocked; only my picture of it was, and "
     "I dispatched an agent to land something that had been in `HEAD` for hours.** The practical "
     "consequence is the good news: **`--resampler lanczos3` is available to the shipping binary "
     "today**, so fact 1420's **+0.1343 dex** is reachable behind a flag right now, and what remains "
     "gated is only the *default* change — which fact 1374 correctly holds until ringing is measured on "
     "real occluding edges. **A corpus fact naming a blocker is a claim about a moment, and this corpus "
     "is written by a dozen agents editing concurrently; facts about the state of the tree decay in "
     "hours while facts about physics do not.** Fact 1452's CA-before-kernel dependency survives "
     "unchanged, since it governs earning the default rather than landing the variant.",
     "ORCH direct verification (ancestor check, symbol grep, default check) + M110 report"),
    (1454,
     "**I BROADCAST A CLIPPY DIAGNOSIS I HAD NOT RUN, AND IT TOLD TWO AGENTS TO IGNORE FAILURES IN THEIR "
     "OWN LANES.** I told the fleet that `cargo clippy -D warnings` failing *\"at `align.rs:2108` "
     "(`pen_w`)\"* was **\"M110's uncommitted work... not a defect in yours.\"** Measured myself: "
     "`cargo clippy --release --workspace --all-targets -- -D warnings` exits **101** with located "
     "errors **3 in `robust.rs`** (M97's lane) and **1 in `optics.rs`** (M107's lane) and **0 in "
     "`align.rs`**. `pen_w` is at `align.rs:2108` — the line number was real — but it draws no "
     "diagnostic; `79264b6` introduced it already in iterator form.",
     "**What I saw was a transient state of another agent's working tree that never reached a commit, "
     "and I promoted it to a fleet-wide all-clear.** The error survived because it was *plausible*: a "
     "real line number, a file genuinely under edit, and no recipient with a reason to re-check an "
     "attribution about someone else's code. **The cost is asymmetric and silent — a false alarm gets "
     "investigated and dies, a false all-clear is believed and persists** — and it landed on the two "
     "agents holding the two files that actually failed. Corrected to M97 and M107 by direct message. "
     "Note also that M110 reported **27** workspace errors against my **4**; I did not reconcile the "
     "difference and it is most likely in-flight edits by live agents, so **treat any clippy count in "
     "this corpus as valid only for the tree state that produced it.**",
     "ORCH direct measurement (`cargo clippy --release --workspace --all-targets`), correcting my own "
     "earlier broadcast"),
]

DISCIPLINES = [
    (736,
     "**Before acting on a corpus fact that names a blocker, re-verify the blocker still exists.** Fact "
     "1420's *\"the blocker is file ownership\"* was true when written and false when I acted on it "
     "(fact 1453): the author had cleared it in `843f6e1` and the corpus had not caught up. **This "
     "corpus is written concurrently by a dozen agents, so its claims about the state of the tree have "
     "a shelf life measured in hours, while its claims about optics and noise do not.** The check that "
     "would have caught it cost one command. **Facts decay at different rates by kind: a measured MTF "
     "is durable, a statement that a file is unwired or a patch unlanded is perishable** — and the "
     "perishable ones are exactly the ones that trigger dispatch decisions. Compare fact 1449's "
     "unwired-code inventory, which is the same perishable kind and should be re-run rather than cited "
     "once it is more than a few hours old."),
    (737,
     "**Never broadcast a diagnosis you have not run yourself.** I relayed a clippy attribution from a "
     "transient working tree and it told two agents that failures in their own files were someone "
     "else's (fact 1454). **A false all-clear is far more dangerous than a false alarm: the alarm gets "
     "investigated and dies, the all-clear is believed and compounds.** The orchestrator's word carries "
     "further than any subordinate's precisely because recipients cannot see the evidence, which raises "
     "rather than lowers the standard of proof required before speaking. When relaying is genuinely "
     "necessary, **attribute it explicitly as unverified relay** so the recipient knows what standard "
     "it was held to. Ask the fleet to contradict you; being contradicted is cheaper than being "
     "believed while wrong."),
]

# Discipline 734's supporting instance did not occur. Correct it in place rather than
# leaving a materially false entry standing.
OLD_734_TAIL = (
    "Compare discipline 729: **seven unanswered requests for a "
    "`merge.rs` lane produced the same waste by the same mechanism, and I did not recognise the second "
    "instance from the first.**"
)
NEW_734_TAIL = (
    "Compare discipline 729: **seven unanswered requests for a "
    "`merge.rs` lane produced the same waste by the same mechanism, and I did not recognise the second "
    "instance from the first.** **CORRECTED by fact 1453: the second instance never happened.** M95 had "
    "already landed the variant in `843f6e1`; fact 1420 was stale and I did not check it. The general "
    "rule stands on discipline 729's instance, which is real and measured, but **the failure I actually "
    "committed here was not slow sequencing — it was acting on a perishable fact without re-verifying "
    "it (discipline 736), and then dispatching an agent to do work that was already in `HEAD`.** Left "
    "in place rather than deleted, because a discipline derived from an instance that did not occur is "
    "exactly the kind of error this corpus exists to make visible."
)


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    n = text.count(OLD_734_TAIL)
    assert n == 1, f"discipline 734 anchor matched {n} times, expected 1"
    text = text.replace(OLD_734_TAIL, NEW_734_TAIL)

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1452 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^735\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded facts 1453-1454, disciplines 736-737, corrected discipline 734")


if __name__ == "__main__":
    main()
