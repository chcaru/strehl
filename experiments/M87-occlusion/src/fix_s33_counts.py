"""M87 -- repair the two checks section 33 legitimately invalidated.

Neither is a defect in section 33 and neither is a defect in the checkers.
Both are checkers correctly noticing that the document changed underneath
them, which is what they are for.

REPAIR 1, verify_s29.  Section 33.7 answers the orchestrator's standing
model-vs-support question by citing six of section 29's figures.  verify_s29
counts those figures across the WHOLE document, deliberately: unlike the other
section checkers it asserts that corrected values PROPAGATED OUT of section 29
into section 0, section 5.1, `P8` and `P110`, and scoping it to section 29
would silently drop those propagation checks.  So the counts are bumped, and
each bump carries the site that caused it so the next one cannot be silent.

Every delta was attributed before being applied.  Counting inside section 33
alone gives exactly 1, 1, 1, 1, 2, 2 -- matching the six shortfalls verify_s29
reported.  No increment is unaccounted for.

REPAIR 2, verify_s32.  Section 32.1 disclosed that my `--limit` audit had
counted the wrong population, and re-grounded the claim on a live census of
the script tree.  verify_s32 re-counts that census from disk rather than
trusting the recorded number -- which is why it caught this -- and section 33
added nine scripts, so 106 -> 115 total and 91 -> 97 measurement.

The claim itself is unchanged and is now checked over a LARGER population:
**zero** measurement scripts invoke the binary and **zero** pass `--limit`.
Six of the nine new scripts are measurement scripts and three (`append_s33`,
`verify_s33`, `control_s33`) are excluded by the same classifier as before,
which is the split the numbers show.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
SRC = pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

S29 = [
    ('        f"{t2[\'n_broad\']:.3f} broad**", D, 3)',
     '        f"{t2[\'n_broad\']:.3f} broad**", D, 4)  # +1: 33.7'),
    ('    chk("local amax thin", f"**{lo[\'amax_thin\']:.4f}**", D, 2)',
     '    chk("local amax thin", f"**{lo[\'amax_thin\']:.4f}**", D, 3)  # +1: 33.7'),
    ('    chk("local amax broad", f"**{lo[\'amax_broad\']:.4f}**", D, 2)',
     '    chk("local amax broad", f"**{lo[\'amax_broad\']:.4f}**", D, 3)  # +1: 33.7'),
    ('    chk("local gate pass thin", f"**{100 * lo[\'pass_thin\']:.2f}%**", D, 4)',
     '    chk("local gate pass thin", f"**{100 * lo[\'pass_thin\']:.2f}%**", D, 5)'
     '  # +1: 33.7'),
    ('    chk("recorded coverage", f"{100 * v[\'C-T3-COVER full\'][\'lo\']:.1f}%", D, 9)',
     '    chk("recorded coverage", f"{100 * v[\'C-T3-COVER full\'][\'lo\']:.1f}%",'
     ' D, 11)  # +2: 33.7, P132'),
    ('    chk("gap in points", f"{t4[\'gap\']:.2f} point", D, 4)',
     '    chk("gap in points", f"{t4[\'gap\']:.2f} point", D, 6)  # +2: 33.7, P132'),
]

DOC_EDITS = [
    ("and `--limit` appears **0** times in the 91 measurement scripts",
     "and `--limit` appears **0** times in the 97 measurement scripts"),
    ("**106** scripts, not 30 \u2014 and, more to the point,",
     "**116** scripts, not 30 \u2014 and, more to the point,"),
]


def edit(path, pairs, label=""):
    s = path.read_bytes().decode("utf-8")
    done = sum(1 for old, _ in pairs if s.count(old) == 0)
    if done == len(pairs):
        print(f"  {path.name}: already applied, skipping")
        return
    if done:
        raise SystemExit(f"{path.name}: {done}/{len(pairs)} already applied")
    for old, new in pairs:
        if s.count(old) != 1:
            raise SystemExit(f"ANCHOR {s.count(old)}x in {path.name}:\n  {old}")
        s = s.replace(old, new, 1)
    path.write_bytes(s.encode("utf-8"))
    print(f"  {path.name}: {len(pairs)} edits applied")


def main():
    before = DOC.read_bytes().decode("utf-8")
    assert before.count("\n") == before.count("\r\n"), "doc not pure CRLF"

    print("repair 1: verify_s29 whole-document counts (+ site annotations)")
    edit(SRC / "verify_s29.py", S29)

    print("repair 2: section 32.1's live script census")
    files = sorted(p for p in SRC.glob("*.py"))
    total = len(files)
    meas = [p for p in files
            if not re.match(r"^(append|verify|control|fix)_", p.name)]
    print(f"  disk: {total} scripts, {len(meas)} measurement")
    # 116 not 115: this repair script is itself on disk now, and its `fix_`
    # prefix excludes it from the measurement population, so the total moved
    # and the measurement count did not.  That is the live census behaving
    # correctly -- verify_s32 recounts from disk at ITS run time, so the two
    # agree.
    assert total == 116, f"expected 116 scripts on disk, found {total}"
    assert len(meas) == 97, f"expected 97 measurement, found {len(meas)}"
    edit(DOC, DOC_EDITS)

    after = DOC.read_bytes().decode("utf-8")
    assert after.count("\n") == after.count("\r\n"), "CRLF broken"
    assert len(after) == len(before), "doc length changed unexpectedly"

    audit = DATA / "93-audit.json"
    d = json.loads(audit.read_text(encoding="utf-8"))
    # Hard-error on a missing key.  The first version of this used
    # `if k in d`, guessed the key names wrong, and silently updated nothing
    # -- the doc moved and its operand did not, which is the exact split a
    # verifier exists to catch and which it did catch.
    for k, v in (("scripts_total", total), ("scripts_measurement", len(meas))):
        if k not in d:
            raise SystemExit(f"93-audit.json has no key {k!r}; keys are "
                             f"{sorted(d)}")
        print(f"  93-audit.json {k}: {d[k]} -> {v}")
        d[k] = v
    audit.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
