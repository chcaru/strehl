"""Fold the HEAD inertness measurement. Fact 1424, discipline 707."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1424, "**THE RENDER HAS NOT MOVED ONE BYTE TONIGHT.** Re-run at HEAD `d42fac4`, the pinned baseline "
           "reproduces **`E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112`**, "
           "197,797,874 bytes, identical to the hash frozen at `d23148c`. **14 commits have landed in "
           "between, 3 of them touching `crates/`** (`36d7c64` M97g, `2a4ebac` M95 arm 7, `7396b25` M108). "
           "Full invocation per rule 47: `strehl stack D:\\personal\\macro\\bee-3-cpl --gate 4 --srgb "
           "--exposure=1.54 --out <tif>`, `STREHL_WARPMAP` at the ORCH-kernel catmull-rom sidecar, "
           "`STREHL_ALIGN` and `STREHL_FIX_HALO` unset, HEAD `d42fac4`. `cargo check --workspace "
           "--all-targets` is clean at the same commit.",
     "**Two readings, both true, and the project should hold both.** (a) **The freeze is real and the three "
     "code commits were correctly inert** -- a rejected demosaic, an already-applied patch, and test "
     "infrastructure. That is a fourth independent session of reproduction and it is exactly what the "
     "registry exists to prove: no unintended drift, on a night when eight agents wrote to the tree. "
     "(b) **Tonight has produced diagnosis, attribution, retraction and instrumentation, and zero bytes of "
     "image improvement** -- while the owner's standing instruction is to tip toward building because the "
     "stacks do not look good yet. **Every identified quality lever is still unbuilt**: the kernel "
     "(+0.1343 dex, patch written, fact 1420), lateral CA (~3 output px, fact 1414), the crop (+0.0143 dex, "
     "fact 1419). The measurement discipline is working; the shipping binary is unchanged.",
     "ORCH, re-render at HEAD `d42fac4` against the `d23148c` freeze (MEASURED, rule 47 complete)"),
]

DISCIPLINES = [
    (707, "**Periodically re-render the pinned baseline and check whether the product actually moved, "
          "because a night of commits is not a night of progress.** 14 commits and 3 changes to `crates/` "
          "produced a byte-identical image. That is simultaneously a clean freeze result and an "
          "uncomfortable one, and only the re-render distinguishes 'correctly inert' from 'busy'. **The "
          "cheapest honest status report is the hash of the output**, not a count of commits or facts. "
          "Fact 1424."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1423 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^706\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        n = r.count("|") - r.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
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
    print(f"folded fact 1424, discipline 707")


if __name__ == "__main__":
    main()
