"""Append fact 1952 to the SYNTHESIS fact table (lane BUILD-PLUGIN)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1951
NEW_ID = 1952

BODY = (
    "Pluggability against the brief, stated exactly: ONE of the five plugin kinds the owner "
    "asked for is a genuine dispatch boundary, and it is refused on the shipping default. "
    "Focus measures are a real trait seam -- `FocusMeasure` at `strehl-core/src/focus.rs:619`, "
    "`Registry` at `strehl-plugin/src/registry.rs:216`, CLI adapter `focus_plugin.rs:62` -- and "
    "it is demonstrated rather than merely compiled: `strehl focus list` host-measures seven "
    "operators live over 12 seeds at 512x512, spanning 10.27x in noise sd with `sml-w13` at "
    "6.61x the default, and swapping the operator on identical input moves 24,702,381 of "
    "24,724,512 samples (99.9105%) between two named hashes while the default output stays "
    "byte-identical across three runs and both byte-freezes hold. The noise sd is MEASURED by "
    "the host, not declared by the operator, because the trait has no method that could declare "
    "it. Against that, merge strategies are an enum match in core (`MergeBackend`, "
    "`merge_cmd.rs:271`), and alignment models, optical profiles and output stages have no "
    "trait at all. The load-bearing caveat: `--focus` is REFUSED on `MergeBackend::Pyramid` "
    "(`main.rs:973-976`), which is `DEFAULT_MERGE_BACKEND`, because the pyramid elects per-band "
    "coefficients from band energy and computes no focus field for an operator to replace. "
    "Refusing is the right failure over silently ignoring, but it means the plugin surface and "
    "the shipping path do not currently intersect. The registry is also in-tree, so a third "
    "party cannot contribute a focus measure without patching this repository."
)


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))
    if NEW_ID in ids:
        raise SystemExit("FATAL: fact %d already present" % NEW_ID)
    if BODY.count("*") % 2 != 0:
        raise SystemExit("FATAL: odd '*' count in body")
    if "|" in BODY:
        raise SystemExit("FATAL: '|' in body")

    anchor = None
    for m in re.finditer(r"^\| %d \|.*$" % EXPECTED_TAIL, src, re.M):
        anchor = m
    if anchor is None:
        raise SystemExit("FATAL: could not locate row %d" % EXPECTED_TAIL)

    row = "| %d | BUILD-PLUGIN | MEASURED | %s |" % (NEW_ID, BODY)
    out = src[: anchor.end()] + "\n" + row + src[anchor.end():]
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != NEW_ID:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != len(ids) + 1:
        raise SystemExit("FATAL: row count went %d -> %d" % (len(ids), len(ids2)))
    print("OK fact %d appended  rows %d -> %d" % (NEW_ID, len(ids), len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
