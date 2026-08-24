"""Fold the enforcement finding: a broadcast is not enforcement.
Facts 1385-1386, discipline 690.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1385, "**A RULE BROADCAST TO SEVEN AGENTS DID NOT STOP THE BEHAVIOUR IT FORBADE.** MEASURED at `d0dbe67`: "
           "within minutes of quarantining 11 stray sidecars out of `D:\\personal\\macro` and broadcasting rule "
           "45 to all 7 running agents, **two more appeared** -- `coffee-bean\\warpmap.txt` at `10:17:17` and "
           "`flat-on-ruler-cpl\\warpmap.txt` at `10:17:38`, both **8-frame solves with reference 4**. Both "
           "quarantined (round 2). Whether those writes began before the broadcast landed is not "
           "determinable from the timestamps alone.",
     "**The same lesson as fact 1381, in a different medium: prose does not enforce.** A milestone report's "
     "frozen hash went stale for weeks while being cited in source; a rule in `AGENTS.md` did not stop a write "
     "it explicitly forbids. **Registered as an open question rather than acted on:** the tool's own behaviour "
     "makes mechanical enforcement viable -- see fact 1386 -- but a deny-write ACL on the capture drive would "
     "fail confusingly the next time the owner copies new captures in, which he does regularly. The narrower "
     "and correct fix is in the code: `align_cmd.rs:376` should not default its sidecar into the stack "
     "directory at all. **Deferred on file contention, not on merit.**",
     "ORCH (MEASURED at `d0dbe67`; routed to M108-freeze-test, whose fixture was the affected stack)"),

    (1386, "**A READ-ONLY CAPTURE DIRECTORY DOES NOT BREAK THE TOOL; THE SIDECAR CACHE WRITE IS A SOFT "
           "FAILURE.** MEASURED by source read at `d0dbe67` (`align_cmd.rs`, `load_or_solve`): "
           "`if let Err(e) = map.save(&side) { eprintln!(\"alignment      : could not cache sidecar ({e}); "
           "continuing\"); }` followed by `Ok(Some((map, \"solved\")))`. The solve already computed is "
           "returned regardless.",
     "**Removes the objection that would otherwise block mechanical enforcement of the read-only contract.** "
     "Denying write on the capture library costs only a re-solve per run -- slower and correct -- rather than "
     "failing the pipeline, so the choice between enforcement and convenience is not the tradeoff it appeared "
     "to be. Recorded so the next agent to consider hardening this does not have to re-derive it, and so the "
     "decision rests on the owner's workflow (he adds captures to that drive) rather than on a fear about tool "
     "behaviour that turns out to be unfounded.",
     "ORCH (MEASURED source read at `d0dbe67`)"),
]

DISCIPLINES = [
    (690, "**A convention announced is not a convention enforced; if it matters, make the wrong thing "
          "impossible rather than forbidden.** Two independent instances in one session: a frozen hash held "
          "only in prose went stale for weeks while being cited in source, and a rule broadcast to seven "
          "agents was violated within minutes. Before relying on a written rule, ask what mechanism would "
          "make its violation fail loudly -- a test, a validation, a permission -- and cost that mechanism "
          "out. Where enforcement is genuinely blocked (file contention, an owner's workflow), **record the "
          "blocker explicitly** so the deferral is a decision rather than an omission. Facts 1381, 1385, "
          "1386."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1384 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^689\. ", l))
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
    print(f"folded facts 1385-1386 after line {fact_idx}, discipline 690 after line {disc_idx}")


if __name__ == "__main__":
    main()
