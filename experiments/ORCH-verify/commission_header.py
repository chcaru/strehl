"""Commission the STATUS HEADER pins added for M169's ratification stakes.

WHY THIS EXISTS
---------------
v2954.py could not see the STATUS header at all until this session: SECTIONS
listed only "2.9.54".."2.9.73", so every needle aimed at the standing summary
above section 1 was unreachable. Three things were therefore added at once --
a "HEADER" pseudo-section, a blockquote-aware unquote(), and four new pins for
the numbers the OWNER acts on (1 / 7 / 6 / 0 of 12).

All three are new machinery, and new machinery that reports GREEN has proved
nothing. If section_text(status_raw, "HEADER") silently returned the wrong
slice -- or the whole file -- the four pins would still pass, because the
needles do occur somewhere in STATUS. This harness plants the exact defects
those pins claim to catch and requires each to turn the run RED.

It also plants two things that must NOT trip it:
  - an edit inside the header that no pin covers, and
  - an edit to the SAME numbers in a section OUTSIDE the header bound,
    which is the specific way a mis-drawn HEADER boundary would betray itself.

Nothing is written to the live tree: docs/ and experiments/ are copied to a
scratch root and v2954.py is pointed at the copy via argv[1].
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2954 = ROOT / "experiments" / "ORCH-verify" / "v2954.py"


def build_scratch():
    # docs/ in full, plus ONLY the .md/.json files under experiments/.
    #
    # Two things forced this shape. Copying experiments/ wholesale fails
    # outright: M142's block cache holds filenames long enough that the copy
    # breaches MAX_PATH once re-rooted under %TEMP%. But copying docs/ alone is
    # also wrong -- v2954 resolves ~15 claims against experiment artifacts
    # (M136 analysis.json, M163 commission.json, M175 render-result.json, the
    # ORCH-verify host-load records), and with those absent the UNMUTATED
    # baseline went RED with 'xdoc derived fail: 2'. A red baseline makes every
    # 'CAUGHT' below unreadable, because a plant cannot be distinguished from
    # the copy. Filtering by extension rather than by an enumerated file list
    # keeps this working when a lane adds a new cited artifact.
    scratch = Path(tempfile.mkdtemp(prefix="ohdr-"))
    shutil.copytree(ROOT / "docs", scratch / "docs")
    src_exp = ROOT / "experiments"
    n = 0
    for p in src_exp.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".md", ".json"):
            continue
        rel = p.relative_to(src_exp)
        dst = scratch / "experiments" / rel
        if len(str(dst)) > 240:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        n += 1
    if n == 0:
        raise SystemExit("FATAL: copied 0 experiment artifacts; scratch is not "
                         "a faithful copy and no result from it is meaningful")
    return scratch


def header_bound(text):
    """Independently re-derive the header slice, WITHOUT importing v2954.

    Re-implementing the boundary here rather than calling v2954's own
    section_text is deliberate: a harness that asks the code under test where
    its own boundary is cannot detect a wrong boundary.
    """
    lines = text.splitlines()
    for j, ln in enumerate(lines):
        if ln.startswith("## 1."):
            return j
    raise SystemExit("FATAL: '## 1.' not found; cannot locate header bound")


def apply(path, old, new, *, inside_header, label):
    """Replace `old` with `new`, requiring exactly one match on the right side
    of the header boundary. A control that lands in the wrong place, or lands
    twice, is not a control -- so this hard-errors instead of proceeding."""
    text = path.read_text(encoding="utf-8", errors="replace")
    bound_line = header_bound(text)
    bound_char = len(("\n".join(text.splitlines()[:bound_line])))
    hits = [m.start() for m in re.finditer(re.escape(old), text)]
    if len(hits) != 1:
        raise SystemExit(
            "FATAL [%s]: anchor matched %d times, need exactly 1: %r"
            % (label, len(hits), old))
    where_in_header = hits[0] < bound_char
    if where_in_header != inside_header:
        raise SystemExit(
            "FATAL [%s]: anchor is %s the header, expected %s"
            % (label,
               "inside" if where_in_header else "outside",
               "inside" if inside_header else "outside"))
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def run(scratch):
    p = subprocess.run([sys.executable, "-B", str(V2954), str(scratch)],
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# (label, anchor, replacement, inside_header, must_go_red, expect_regex)
CONTROLS = [
    ("plan licence axes drift",
     "prerequisite for **1 of 12** axes",
     "prerequisite for **4 of 12** axes",
     True, True, "m169 plan licence axes"),
    ("propagated axes drift",
     "arms to **7** more",
     "arms to **9** more",
     True, True, "m169 propagated axes"),
    ("axes shedding d drift",
     "**6** axes shed blocker",
     "**8** axes shed blocker",
     True, True, "m169 axes shedding d"),
    ("newly scoreable drift",
     "**0 of 12** newly scoreable",
     "**3 of 12** newly scoreable",
     True, True, "m169 newly scoreable"),
    # The two-axis score count is the number that was stale for weeks and that
    # propagated into M169's own report. The header must not be able to go
    # stale again silently -- but note it deliberately carries NO M139 memory
    # figure, because M139 withdrew every one of them in an uncommitted rewrite
    # while this pin set was being built. See STATUS 2.9.74.
    ("scored axis count drift",
     "**Current position against that bar: 0 of 12 axes passed.**",
     "**Current position against that bar: 3 of 12 axes passed.**",
     True, True, "header scored axis count"),
    # INERT 1: header prose no pin covers. If this goes RED the suite is
    # reacting to any edit at all, which would make every GREEN meaningless.
    ("inert header prose",
     "The practical consequence is that",
     "The practical upshot is that",
     True, False, None),
]


def red_has(out, label):
    """Did the verifier report this exact claim label as RED?

    Matched on the label itself rather than by splitting the output into
    whitespace columns. The column approach FAILED SILENTLY and in the
    dangerous direction: v2954 pads the label field to a fixed width, so a
    label at or over that width is followed by a single space, a
    '^RED\\s+(\\S.*?)\\s{2,}' parse missed it, and a genuine catch was reported
    as '*** MISSED ***'. A harness that under-reports its own catches is
    worse than one that over-reports them, because it invites 'fixing' a pin
    that was never broken.
    """
    return re.search(r"(?m)^RED\s+" + re.escape(label) + r"(\s|$)",
                     out) is not None


def red_count(out):
    """Total RED claims, read from the verifier's own summary line.

    Used for the inert arm, where the question is 'did anything at all break'
    and no specific label is expected. Reading the printed total rather than
    counting parsed lines means the inert check cannot be fooled by the same
    label-parsing fragility that broke red_has's predecessor.
    """
    m = re.search(r"(?m)^RED\s*:\s*(\d+)\s*$", out)
    if m is None:
        raise SystemExit("FATAL: could not read the verifier's RED total; "
                         "no arm below would be interpretable")
    return int(m.group(1))


def main():
    # AMBIENT FAILURES ARE EXPECTED AND MUST NOT INVALIDATE THE RUN.
    #
    # The naive criterion "unmutated baseline is GREEN, plant turns it RED"
    # is unusable in a shared tree: lane M139 rewrote its own report while this
    # harness was being written, withdrawing thirteen figures that STATUS pins
    # cite, so the live baseline is legitimately RED through no fault of any
    # plant. Waiting for that to clear would mean the header pins go
    # uncommissioned for as long as any other lane has work in flight.
    #
    # The stronger criterion used instead: a plant must turn ITS OWN NAMED
    # CLAIM red, and that claim must be green in the baseline. That isolates
    # the plant's effect from ambient breakage and is strictly harder to
    # satisfy than green-to-red, because a plant can no longer take credit for
    # a failure something else caused.
    scratch = build_scratch()
    rc0, out0 = run(scratch)
    base_n = red_count(out0)
    shutil.rmtree(scratch, ignore_errors=True)
    print("baseline: rc=%d, %d ambient RED claim(s)" % (rc0, base_n))
    for _, _, _, _, must_red, expect in CONTROLS:
        if must_red and red_has(out0, expect):
            raise SystemExit(
                "FATAL: claim %r is ALREADY RED before its plant is applied; "
                "its control would be meaningless" % expect)
    print()

    caught, missed, inert_ok, inert_bad = 0, 0, 0, 0
    for label, old, new, inside, must_red, expect in CONTROLS:
        scratch = build_scratch()
        status = scratch / "docs" / "STATUS.md"
        apply(status, old, new, inside_header=inside, label=label)
        rc, out = run(scratch)
        if must_red:
            hit = red_has(out, expect)
            print("%-28s %-16s [expected claim %r %s]"
                  % (label, "CAUGHT" if hit else "*** MISSED ***",
                     expect, "went RED" if hit else "STAYED GREEN"))
            if hit:
                caught += 1
            else:
                missed += 1
        else:
            n = red_count(out)
            quiet = n == base_n
            print("%-28s %-16s [RED total %d vs baseline %d]"
                  % (label, "inert, survived" if quiet
                     else "*** INERT TRIPPED ***", n, base_n))
            if quiet:
                inert_ok += 1
            else:
                inert_bad += 1
        shutil.rmtree(scratch, ignore_errors=True)

    planted = sum(1 for c in CONTROLS if c[4])
    inert = len(CONTROLS) - planted
    print("\ncaught %d, missed %d  (of %d planted)"
          % (caught, missed, planted))
    print("inert survived %d, inert tripped %d  (of %d inert)"
          % (inert_ok, inert_bad, inert))
    ok = (missed == 0 and inert_bad == 0
          and caught == planted and inert_ok == inert)
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    if base_n:
        print("NOTE: %d ambient RED claim(s) excluded as pre-existing. They "
              "are a real drift alarm (lane M139 withdrew figures that STATUS "
              "pins cite) and remain outstanding." % base_n)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
