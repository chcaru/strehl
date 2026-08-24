"""Fold the manual/automatic reference-frame disagreement.
Fact 1370, discipline 682.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1370, "**`strehl align` AND THE MERGE'S AUTOMATIC PATH DISAGREE ON THE DEFAULT REFERENCE FRAME, AND THE "
           "MANUAL DEFAULT IS THE WORSE ONE.** MEASURED at `865c1ff` by reading both sites: the subcommand "
           "declares `#[arg(long, default_value_t = 0)] pub reference` (`align_cmd.rs:56-57`), while "
           "`load_or_solve` solves against `merge_reference(paths.len())`, which is `n / 2` "
           "(`align_cmd.rs:798-800`). On a 299-frame bracket that is **frame 0 against frame 149**. The "
           "codebase already states which is correct, at `align_cmd.rs:791-795`: the reference is the frame "
           "everything else is resampled onto, so **the uncovered border grows with distance from it**, and "
           "referencing frame 0 maximises that distance over a focus bracket.",
     "**An operator who runs `strehl align` by hand and then `strehl stack` gets a measurably worse "
     "registration than one who simply runs `strehl stack` and lets it solve** -- the manual step, which looks "
     "like taking control, silently degrades the result. Severity is currently *latent* rather than live: "
     "`README.md` does not document `strehl align` anywhere, so no documented workflow walks into it. But the "
     "subcommand is in `--help`, and rule 45 now instructs every agent to invoke it directly with `--out`, "
     "**which converts a latent trap into a live one for exactly the audience most likely to trust the "
     "default**. ORCH's own gallery script hit it and passed `--reference` explicitly only because the "
     "divergence was checked first rather than assumed. The repair is to default the subcommand to "
     "`merge_reference()` too; `align_cmd.rs` is held by M95-sharpness at time of writing, so this is recorded "
     "rather than applied.",
     "ORCH (MEASURED at `865c1ff` at both declaration sites; not yet fixed -- file held by M95)"),
]

DISCIPLINES = [
    (682, "**When one operation has both a manual and an automatic entry point, check that their defaults "
          "agree -- and treat any divergence as a defect in the manual one.** The automatic path is exercised "
          "on every run and its default is therefore continuously tested; the manual path's default is chosen "
          "once, by whoever wrote the flag, and is often the naive value (`0`, `1`, the first element) rather "
          "than the considered one. `strehl align --reference` defaults to frame 0 where the merge uses the "
          "middle frame, so invoking the tool by hand degrades the registration relative to not invoking it at "
          "all. **A new operating rule that tells people to use the manual path inherits every divergence the "
          "manual path has** -- rule 45 did exactly that -- so audit the defaults at the moment you promote a "
          "manual invocation, not afterwards. Fact 1370."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1369 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^681\. ", l))
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
    print(f"folded fact 1370 after line {fact_idx}, discipline 682 after line {disc_idx}")


if __name__ == "__main__":
    main()
