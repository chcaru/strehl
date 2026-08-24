"""Correct fact 1469 in place: the kernel is hard-coded, not cache-determined. ORCH self-catch."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1476,
     "**`strehl stack` DOES NOT INHERIT ITS KERNEL FROM THE CACHE -- IT HARD-CODES ONE, AND THE CACHE IS "
     "CORRECTLY KEYED AGAINST IT.** Read at `ef730ce`: `align_cmd.rs::merge_config` returns "
     "`Resampler::CatmullRom` as a literal, with no argument and no environment read; "
     "`solve_config_key(reference, spans, resampler)` **hashes the resampler** and every variable in "
     "`SOLVE_ENV` into the sidecar path; and a sidecar whose recorded resampler differs from the wanted "
     "one triggers an explicit **re-solve** with a printed message rather than being silently consumed. "
     "**So the kernel of a `strehl stack` render is a compile-time constant, and there is no argument, "
     "flag or environment variable by which a user can change it.** M113's contrary measurement was "
     "taken at `e924229`, which **does not contain `solve_config_key` at all** (0 occurrences); the fix "
     "landed at `69f7b4c` (\"key the warp cache on the solve configuration, not just the path\"), and "
     "both are ancestors of `HEAD`.",
     "**I folded fact 1469 roughly twenty minutes before reading the source that refutes half of it, and "
     "I caught it only because I went looking for who owned `StackIdentity` in order to plan a default "
     "change.** The measurement was honest and reproducible on the commit it was taken at; it simply "
     "described a tree that no longer existed. **Crucially, the correction does not touch M113's or "
     "M110's kernel numbers**: both pinned their warp maps explicitly (`STREHL_WARPMAP`, explicit "
     "`--out`), which bypasses `merge_config` entirely, so facts 1465-1467 stand unaltered. What changes "
     "is the *product* conclusion, and it gets sharper rather than weaker: the objection is no longer "
     "\"the kernel can be contaminated\" but **\"the kernel cannot be chosen at all\"**. Shipping "
     "Lanczos-3 is therefore a one-line change to a literal plus a user-facing flag -- small, "
     "well-evidenced, and currently blocked on nothing but lane ownership. **`StackIdentity` itself is "
     "not at fault and should not be changed**: it identifies the *input bracket* by name, per-frame "
     "`(filename, size)` and frame count, exactly as its documentation states, and processing settings "
     "belong in the config key where they now are.",
     "ORCH direct source read at `ef730ce`: `align_cmd.rs` merge_config, solve_config_key, sidecar "
     "mismatch branch; `git merge-base --is-ancestor 69f7b4c HEAD` = 0"),
]

DISCIPLINES = [
    (754,
     "**Verify a subordinate's claims about the tree against the tree at the moment you fold them, not "
     "at the moment they were reported.** Discipline 736 tells me to re-verify a named blocker before "
     "*acting*; this is the stricter obligation, because **folding launders a perishable measurement "
     "into a durable claim that everyone downstream will read as current**. Fact 1469 was measured "
     "honestly at `e924229` and was false at `HEAD` before I ever wrote it down. The check is cheap and "
     "mechanical: **any claim of the form \"the code does X\" gets one grep at fold time**, and any "
     "claim carrying a commit hash gets `git merge-base --is-ancestor`. This is now the third stale-tree "
     "incident tonight (facts 1453, 1460, 1476) and the only one caught before it did damage -- by "
     "accident, while planning something else. **Optical facts keep; tree facts rot, and the corpus does "
     "not distinguish them unless the author does.**"),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1475 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^753\. ", l))
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
    text2 = "\n".join(out)

    note = (" **CORRECTED (fact 1476): measured at `e924229`, which predates the cache-key fix "
            "`69f7b4c`. At HEAD the resampler IS in the sidecar key and a mismatch forces a re-solve. "
            "The surviving -- and stronger -- half is that `strehl stack` hard-codes "
            "`Resampler::CatmullRom` and exposes no way to change it.**")
    m = re.search(r"^\| 1469 \| ", text2, re.M)
    assert m, "fact 1469 row not found"
    eol = text2.index("\n", m.start())
    row = text2[m.start():eol]
    assert note not in row, "fact 1469 already corrected"
    cells = row.split(" | ")
    assert len(cells) >= 3, "fact 1469: unexpected row shape"
    cells[1] = cells[1] + note
    text2 = text2[:m.start()] + " | ".join(cells) + text2[eol:]

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    print("folded fact 1476, discipline 754; corrected fact 1469 in place")


if __name__ == "__main__":
    main()
