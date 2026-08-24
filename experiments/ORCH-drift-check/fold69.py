"""Fold the coffee-bean fixture verification.
Facts 1389-1392, disciplines 692-693.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1389, "**M95'S `coffee-bean` FREEZE IS NOT STALE -- IT IS UNDER-SPECIFIED, AND THE MISSING ELEMENT IS AN "
           "ENVIRONMENT VARIABLE.** MEASURED independently. `strehl stack <dir>\\coffee-bean --limit 20 "
           "--gate 2.0`: under the **default aligned** path it renders `119936E6...` at both `56bd846` (M95's "
           "own commit) and HEAD `14b39dd`; under **`STREHL_ALIGN=0`** it renders "
           "`D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA` at both. **M95's record matches "
           "only the second**, and `STREHL_ALIGN=0` appears nowhere in it. All renders 49 449 626 bytes, exit "
           "0, `20 placed / 0 refused`, `sidecar-override`, A==B determinism across two processes True. M95's "
           "record also omits the byte count, the commit SHAs and the absolute directory, and the full 64-char "
           "hash exists **only in the commit body of `56bd846`** -- no M95 report contains it.",
     "**The renderer never moved; both variants are frozen across the whole range, so no fourth stale freeze "
     "exists.** The finding is about the record, not the code. **And it lands on rule 47 itself:** that rule, "
     "written two hours earlier, required \"directory, `--limit`, and `--gate` by value\" -- **all CLI flags** "
     "-- and would therefore have missed this entirely. **Third false break in one session from one root "
     "cause:** `bee-3-cpl` lost `--gate`, `coffee-bean` lost `STREHL_ALIGN`. Rule 47 amended in the same "
     "commit to bind `STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_FIX_HALO`, thread count, byte count and commit "
     "SHA. **A frozen hash is a claim about a whole pipeline, and an environment variable is as much a part of "
     "that pipeline as an argument is.**",
     "M106-freeze verifier `a7cf3e3e` (MEASURED, turn 5, independent of M108 by construction)"),

    (1390, "**QUARANTINING STRAY SIDECARS IS NOT REMEDIATION; THE FILE RETURNS WITHIN MINUTES.** MEASURED "
           "during a 20-minute independent check: `coffee-bean/warpmap.txt` reappeared at `frames 1` "
           "(`10:27:37`), `frames 20` (`10:31:11`), and `frames 1` again at **`10:33:42`, after the "
           "orchestrator's quarantine**. The verifier wrote none of them -- all its runs targeted a scratch "
           "copy and used the override. Session totals: **14 sidecars quarantined across 3 sweeps, 3 "
           "broadcasts of rule 45, and no measurable fall in the rate.**",
     "**Settles the enforcement question empirically and against the orchestrator's chosen approach.** Fact "
     "1385 recorded that a broadcast did not stop the behaviour; this measures that *sweeping* does not stop "
     "it either. Neither prose nor cleanup is remediation when the tool's default actively recreates the "
     "hazard. **The fix must be in code** -- `align_cmd.rs:376` must not default its sidecar into the stack "
     "directory -- and the fix has been requested of the agent holding that file rather than taken by force. "
     "Note the collateral hazard for anyone reasoning about tonight's numbers: a stack can be repopulated "
     "**between** a clean sweep and a measurement, so 'the library was clean when I started' is not a "
     "guarantee that it was clean when the run read it.",
     "M106-freeze verifier `a7cf3e3e` (MEASURED); ORCH quarantine rounds 1-3"),

    (1391, "**A QUARANTINED SIDECAR CANNOT BE ATTRIBUTED TO THE AGENT THAT WROTE IT FROM ITS CONTENTS.** "
           "MEASURED: a scratch-isolated solve and a library solve of the same bracket were **byte-identical** "
           "(`EF74541395DB1BA6`, `stack-digest 25daf54c45be5446`), because `StackIdentity::from_paths` digests "
           "filenames and sizes only and is **directory-independent**.",
     "**Kills a forensic method before it was relied on.** The natural move on finding a stray sidecar is to "
     "read it and infer which agent produced it; the digest's directory-independence makes that impossible in "
     "principle, not merely difficult. Attribution must come from external evidence -- run logs, timestamps, "
     "dispatch records -- and any claim of the form 'agent X wrote this file' inferred from the file itself is "
     "unfounded. Same root property as fact 1383: **a digest that ignores content and location is a checksum "
     "of the directory listing.**",
     "M106-freeze verifier `a7cf3e3e` (MEASURED)"),

    (1392, "**THE ALIGNED VARIANT OF THE `coffee-bean` FIXTURE RESTS ON A REGISTRATION THE TOOL ITSELF REFUSES "
           "TO CERTIFY.** MEASURED: every aligned run of that stack printed `WARNING: this solve could not "
           "certify itself ... the registration below is UNVERIFIED`. The tool attributes the failure to "
           "insufficient long-span edges; that attribution was **not** independently confirmed.",
     "**Registered before any freeze test enshrines the number.** Pinning `119936E6` means pinning a value the "
     "tool declares unverified -- which may still be correct, since a frozen unverified value at least detects "
     "*change*, but it must be stated in the registry's reason column rather than silently enshrined. "
     "**Consequence for fixture design: one fixture cannot do both jobs.** The `STREHL_ALIGN=0` variant has "
     "zero sidecar dependency and is structurally immune to the shared-state hazard that broke this stack four "
     "times in one session, but exercises none of the alignment path; the aligned variant covers alignment and "
     "inherits both the sidecar fragility and this warning. **Pin both, and state what each does not cover.**",
     "M106-freeze verifier `a7cf3e3e` (MEASURED); routed to M108-freeze-test as evidence, not instruction"),
]

DISCIPLINES = [
    (692, "**A freeze record must bind the environment, not only the command line.** Environment variables "
          "that alter the pipeline -- `STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_FIX_HALO` -- are as much part "
          "of a frozen hash's provenance as any flag, and are **more** dangerous because nothing in the shell "
          "history records them. A freeze that reproduces only under an unrecorded variable looks identical to "
          "a stale freeze from the outside. Fact 1389; rule 47 as amended."),
    (693, "**One fixture cannot cover both an isolated path and an integrated one; pin both and state the "
          "trade.** An isolated fixture (dependencies disabled) is reproducible and blind; an integrated one "
          "covers the real pipeline and inherits its fragility. Choosing only the integrated one buys coverage "
          "at the price of the exact instability the freeze exists to detect; choosing only the isolated one "
          "is safe and tests nothing that matters. Facts 1389, 1392."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1388 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^691\. ", l))
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
    print(f"folded facts 1389-1392 after line {fact_idx}, disciplines 692-693 after line {disc_idx}")


if __name__ == "__main__":
    main()
