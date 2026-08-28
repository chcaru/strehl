"""Re-baseline ONE row of `crates/strehl-cli/tests/byte-freezes.tsv`, by column.

WHY THIS IS A SCRIPT AND NOT A HAND EDIT

The registry is TAB-separated and its two rows are ~7 kB of prose each on a
single physical line. A hand edit there is a search-and-replace over text that
is nearly identical in both rows, on a file whose parser checks the header
VERBATIM and whose columns shift silently if one tab is lost. The failure mode
is not a rejected edit, it is a `why` spliced onto the wrong row -- which is the
shape of SYNTHESIS fact 1379.

So: parse by header name, assert the row is unique, assert every field that must
NOT move actually did not, and rewrite by index. The assertions are the point.

Usage:  python rebaseline_sidecar.py <registry.tsv> <why.txt> --check
        python rebaseline_sidecar.py <registry.tsv> <why.txt> --apply
"""

import pathlib
import sys

ROW_ID = "coffee-bean-20-gate2-sidecar"
NEW_SHA = "E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2"
OLD_SHA = "52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206"
NEW_AT = "6943f04b"
NEW_ON = "2026-08-28"

# Fields that MUST be identical before and after. A re-baseline that also moved
# the invocation would be re-baselining a different measurement, and the hash
# would then be honest about bytes nobody asked for.
FROZEN = ("id", "stack", "frames", "limit", "gate", "srgb", "env_align",
          "env_warpmap", "env_fix_halo", "env_cache_dir", "alignment_mode",
          "bytes", "workers")


def main(argv):
    if len(argv) < 4 or argv[3] not in ("--check", "--apply"):
        raise SystemExit(__doc__)
    reg = pathlib.Path(argv[1])
    why = pathlib.Path(argv[2]).read_text(encoding="utf-8").strip()
    apply_it = argv[3] == "--apply"

    if "\t" in why or "\n" in why:
        raise SystemExit("the `why` text contains a tab or a newline; it is ONE TSV field")
    if len(why) < 60:
        raise SystemExit("byte-freeze.rs requires `why` >= 60 chars; got %d" % len(why))

    raw = reg.read_text(encoding="utf-8")
    lines = raw.split("\n")
    hdr_i = next(i for i, l in enumerate(lines)
                 if l and not l.startswith("#") and l.split("\t")[0] == "id")
    cols = lines[hdr_i].split("\t")

    hits = [i for i, l in enumerate(lines)
            if i > hdr_i and l and not l.startswith("#") and l.split("\t")[0] == ROW_ID]
    if len(hits) != 1:
        raise SystemExit("expected exactly one `%s` row, found %d" % (ROW_ID, len(hits)))
    i = hits[0]
    f = lines[i].split("\t")
    if len(f) != len(cols):
        raise SystemExit("row has %d fields, header has %d" % (len(f), len(cols)))

    before = dict(zip(cols, f))
    if before["sha256"] != OLD_SHA:
        raise SystemExit("row sha256 is %s, expected the superseded %s -- somebody "
                         "else has already moved this row" % (before["sha256"], OLD_SHA))

    f[cols.index("sha256")] = NEW_SHA
    f[cols.index("baselined_at")] = NEW_AT
    f[cols.index("baselined_on")] = NEW_ON
    f[cols.index("why")] = why
    after = dict(zip(cols, f))

    for k in FROZEN:
        if before[k] != after[k]:
            raise SystemExit("field `%s` moved (%r -> %r); it must not" % (k, before[k], after[k]))

    print("row      : %s (line %d)" % (ROW_ID, i + 1))
    for k in ("sha256", "baselined_at", "baselined_on"):
        print("%-13s: %s -> %s" % (k, before[k], after[k]))
    print("why      : %d chars -> %d chars" % (len(before["why"]), len(after["why"])))
    print("unchanged: %s" % ", ".join("%s=%s" % (k, before[k]) for k in FROZEN))

    # The OTHER row must be byte-identical afterwards. The control row's value is
    # the whole specificity argument; a re-baseline that silently touched it would
    # destroy the evidence and leave a green test behind.
    lines[i] = "\t".join(f)
    out = "\n".join(lines)
    other = [l for l in lines if l.startswith("coffee-bean-20-gate2-unaligned\t")]
    orig_other = [l for l in raw.split("\n") if l.startswith("coffee-bean-20-gate2-unaligned\t")]
    if other != orig_other:
        raise SystemExit("the unaligned control row changed; refusing")
    print("control  : coffee-bean-20-gate2-unaligned byte-identical (%d chars)" % len(other[0]))

    if apply_it:
        with open(reg, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
        print("APPLIED to %s" % reg)
    else:
        print("CHECK ONLY -- nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
