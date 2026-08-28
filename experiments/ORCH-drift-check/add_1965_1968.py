"""Append facts 1965-1968 to the SYNTHESIS fact table (lanes BUILD-SOFTGATE, V-ADJ13)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1964

ROWS = [
    (1965, "BUILD-SOFTGATE", "MEASURED", (
        "The replacement banking verifier shipped with two defects of its own, both found by "
        "the first lane ordered to use it, and both would have corrupted the corpus in opposite "
        "directions. FALSE NEGATIVES: house style writes large numbers with U+0020 between "
        "digit groups, confirmed by dumping code points on `98 898 048` and `28 754`, so a "
        "plain digit-bounded token search misses every number above 9999 in a prose report -- "
        "a lane certifying against `docs/research/` would have produced a wave of false "
        "EVIDENCE GONE. FALSE POSITIVES: a digit-only boundary is the wrong class for hex, "
        "because the character after a truncated digest is usually a letter, so the 8-character "
        "prefix `742A6331` matched inside `742A6331ABCDEF...` -- measured True under (?![0-9]) "
        "and False under (?![0-9A-Fa-f]) -- meaning every truncated-hash claim certified too "
        "easily. Fixed by making the needle separator-tolerant rather than mutating the "
        "haystack (which would fuse unrelated adjacent numbers), and by selecting the boundary "
        "class from the value's own shape. Re-commissioned 5-of-5: spaced numbers now BANKED "
        "4-of-4, hex prefix rejected, invented value still rc=2, the 1603-versus-16039 boundary "
        "still holds, and the original positive control still passes."
    )),
    (1966, "V-ADJ13", "MEASURED", (
        "The print gate now returns a complete summing partition over every shipping subject "
        "with nothing unresolved: 17 PASS, 0 FAIL, 16 ACQUITTED, 0 ACQUITTAL EXPIRED, 0 REVIEW, "
        "0 NOT EXAMINED, 33 total, found 33 -- re-run independently by the orchestrator against "
        "the lane that produced it, same result. All 13 previously unresolved subjects were "
        "measured against the frames they were built from and NONE is a real defect; the worst "
        "is `dime-flat-narrow-slices-cpl` at 1.257x against a rule admitting 1.3x, and its band "
        "DN is only 1.017x. No threshold or tolerance was touched. The finding that outranks "
        "the sweep concerns the gate itself: five of the six EXPIRED acquittals had not changed "
        "the way the gate said. Four were the statistic being measured at a MOVED WINDOW rather "
        "than a changed render, one had its drift overstated 2.7x by an unreported window move, "
        "and only `113MSDCF` expired on a genuine same-window render change -- which moved in "
        "the IMPROVING direction, -5.64%, and sits in the merge, since the single-frame path "
        "moves chroma only +0.06% between the two binaries."
    )),
    (1967, "V-ADJ13", "MEASURED", (
        "A gate defect that manufactures false expiries: `orch_printready.verdict()` omits "
        "`chroma_window_yx` from `meas`, so the `measured somewhere else` branch of "
        "`check_acquittal` is DEAD for chroma. The consequence is that a window move is printed "
        "as value drift -- `foam` and `112MSDCF` were both reported as large chroma drift when "
        "the real same-window changes were -1.19% and -6.23%, the latter printed as -16.9%, "
        "against an 872-pixel window move. The lane reported this rather than patching the "
        "shared gate other lanes were running against, which is the correct call under "
        "concurrency. UNTIL IT LANDS, every chroma expiry must be re-measured at the RECORDED "
        "window before it is believed. The generalisation is that a drift statistic is "
        "meaningless unless the window it was measured in is carried alongside it and compared, "
        "and a gate that silently re-derives the window will report relocation as change."
    )),
    (1968, "V-ADJ13", "MEASURED", (
        "A shipping CLI flag announces a large effect and does essentially nothing: on pin "
        "`740e7056`, `--auto-exposure` and an explicit `--exposure=2.33` change AT MOST 1 DN on "
        "roughly 0.25% of samples, while the banner announces `+2.42 stops (gain 5.352x), "
        "chosen from the image`. The banner is the product's own voice and it is not telling "
        "the truth about what the code did. Scope is stated rather than buried: one pin, one "
        "subject, one frame, sRGB output -- and the inertness is what makes older records "
        "comparable to current measurements at all, so it is load-bearing for cross-arm "
        "comparison even though it is a defect. Any user-facing claim of the form `chosen from "
        "the image` must be commissioned against a measured pixel delta before it ships, "
        "because a banner is not a measurement."
    )),
]


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))

    n_before = len(ids)
    cur_tail = EXPECTED_TAIL
    for new_id, lane, kind, body in ROWS:
        if new_id in ids:
            raise SystemExit("FATAL: fact %d already present" % new_id)
        if body.count("*") % 2 != 0:
            raise SystemExit("FATAL: odd '*' count in fact %d" % new_id)
        if "|" in body:
            raise SystemExit("FATAL: '|' in body of fact %d" % new_id)
        anchor = None
        for m in re.finditer(r"^\| %d \|.*$" % cur_tail, src, re.M):
            anchor = m
        if anchor is None:
            raise SystemExit("FATAL: could not locate row %d" % cur_tail)
        src = src[: anchor.end()] + "\n" + ("| %d | %s | %s | %s |" % (new_id, lane, kind, body)) + src[anchor.end():]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d" % (n_before, len(ids2)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
