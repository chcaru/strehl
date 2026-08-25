"""fold_check.py -- the mechanical form of discipline 849.

Discipline 849 says my folds are lossy compression with a systematic sign: seven
times in one night a number or qualifier moved toward the claim between the
source report and the SYNTHESIS row. The seventh (fact 1686, "60.9%" folded as a
"MINORITY") happened *while I was writing the discipline about it*, which is
decisive evidence that exhortation does not work here and an instrument is
needed.

    python fold_check.py <fold_script.py> <source_report.md> [more sources...]
    python fold_check.py --commission

  Pass `docs/research/SYNTHESIS.md` as an ADDITIONAL source whenever the fold
  cites numbers from existing facts. Those numbers are legitimately sourced --
  just not from the new report -- and omitting SYNTHESIS makes them read as
  fabrications.

WHAT IT DOES

  1. Parses the fold script with `ast` -- never executes it, because fold scripts
     write to SYNTHESIS.md -- and lifts every string in `NEW_FACTS`,
     `NEW_DISCIPLINES`, and any amendment payload.
  2. Extracts every numeric literal from that prose.
  3. Requires each to appear in at least one source report, and prints the
     surrounding context for each match so the *meaning* can be eyeballed.
  4. Separately flags comparative qualifiers (majority/minority/dominant/only/
     largest/...) next to a number, because those carry the sign and CANNOT be
     checked by presence. Fact 1686's defect was exactly here: the number 60.9
     was present and correct in the fold; the word "minority" was the lie.

WHAT IT IS NOT

  A presence check is satisfied by ANY occurrence of the value, including a
  coincidental one elsewhere in the report. That is a known failure mode of this
  class of verifier. Hence rule (3): it prints context rather than a bare tick,
  and hence rule (4): the qualifier audit is advisory and demands a human read.
  This tool lowers the error rate; it does not certify a fold.
"""
import argparse
import ast
import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Cross-references, not measurements. Stripped before numbers are extracted, or
# every "fact 1678" becomes a spurious unmatched number.
XREF = re.compile(
    r"\b(?:facts?|disciplines?|rules?|questions?|risks?|arms?)\s+\d+(?:\s*[-\u2013]\s*\d+)?"
    r"|\bM\d+[a-z]*\b"
    r"|\bV-[A-Z0-9]+\b"
    r"|\b\d+[A-Z]{2,}\b"          # stack names: 113MSDCF, 109MSDCF
    r"|\u00a7\s*[\d.]+"
    r"|\bfig(?:ure)?\.?\s*\d+",
    re.I,
)

NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)")

QUALIFIERS = [
    "majority", "minority", "dominant", "dominates", "most of", "least",
    "largest", "smallest", "biggest", "only", "merely", "just",
    "more than half", "less than half", "the bulk", "primarily", "chiefly",
    "negligible", "substantial", "entire", "all of", "none of",
]
QUAL_RE = re.compile("|".join(re.escape(q) for q in QUALIFIERS), re.I)

# Small integers are too common to discriminate: "2 of 3", "one of 14".
# They are reported in a separate, quieter bucket.
TRIVIAL_MAX = 12


def lift_strings(path):
    """Pull fact/discipline prose out of a fold script without executing it."""
    with io.open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)

    wanted = {"NEW_FACTS", "NEW_DISCIPLINES", "AMEND_PREFIX", "RIGHT", "AMEND"}
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if not (names & wanted):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, (list, tuple)):
                stack.extend(item)
    if not out:
        raise SystemExit(
            "fold_check: found no NEW_FACTS / NEW_DISCIPLINES / amendment prose in "
            "%s -- is this a fold script?" % path
        )
    return out


def numbers_in(text):
    return [m.group(1) for m in NUM.finditer(XREF.sub(" ", text))]


def variants(tok):
    """A number may be written 166.8 in one place and 166.80 in another."""
    seen = {tok}
    if "." in tok:
        seen.add(tok.rstrip("0").rstrip("."))
    else:
        seen.add(tok + ".0")
    try:
        f = float(tok)
    except ValueError:
        return seen
    if f == int(f):
        seen.add(str(int(f)))
    if abs(f) >= 1000:
        seen.add("{:,}".format(int(f)) if f == int(f) else "{:,}".format(f))
    return seen


def find_context(tok, sources, width=58):
    for name, body in sources:
        for v in variants(tok):
            idx = body.find(v)
            while idx != -1:
                before = body[max(0, idx - width):idx]
                after = body[idx + len(v):idx + len(v) + width]
                if not re.search(r"[\w.]$", before) and not re.match(r"^[\w]", after):
                    ctx = (before + "[" + v + "]" + after).replace("\n", " ")
                    ctx = re.sub(r"\s+", " ", ctx).strip()
                    total = sum(b.count(v) for _, b in sources)
                    return name, ctx, total
                idx = body.find(v, idx + 1)
    return None, None, 0


def qualifier_hits(text):
    hits = []
    for m in QUAL_RE.finditer(text):
        lo = max(0, m.start() - 90)
        hi = min(len(text), m.end() + 90)
        window = text[lo:hi]
        if NUM.search(XREF.sub(" ", window)):
            ctx = re.sub(r"\s+", " ", window).strip()
            hits.append((m.group(0), ctx))
    return hits


def run(fold_path, source_paths):
    prose = lift_strings(fold_path)
    sources = []
    for p in source_paths:
        with io.open(p, "r", encoding="utf-8") as fh:
            sources.append((p, fh.read()))

    all_nums = []
    for chunk in prose:
        all_nums.extend(numbers_in(chunk))

    checked, missing, trivial = [], [], []
    for tok in sorted(set(all_nums), key=lambda t: (-float(t), t)):
        name, ctx, count = find_context(tok, sources)
        if name is None:
            if float(tok) <= TRIVIAL_MAX:
                trivial.append(tok)
            else:
                missing.append(tok)
        else:
            checked.append((tok, name, ctx, count))

    print("=" * 78)
    print("fold_check  %s" % fold_path)
    print("sources     %s" % ", ".join(source_paths))
    print("=" * 78)

    print("\nMATCHED (%d) -- read the context, presence is not correctness:" % len(checked))
    for tok, name, ctx, count in checked:
        dup = "  <-- %d occurrences, presence proves little" % count if count > 1 else ""
        print("  %-10s %s%s" % (tok, ctx, dup))

    if trivial:
        print("\nSMALL INTEGERS NOT FOUND (%d) -- usually prose, check by eye:" % len(trivial))
        print("  " + ", ".join(trivial))

    quals = []
    for chunk in prose:
        quals.extend(qualifier_hits(chunk))
    if quals:
        print("\nQUALIFIERS NEAR NUMBERS (%d) -- NOT machine-checkable, READ THESE:" % len(quals))
        print("  Fact 1686 folded a measured 60.9%% as a 'MINORITY'. The number was")
        print("  right and the word was the lie. This bucket is where that lives.")
        for word, ctx in quals:
            print("    [%s] %s" % (word, ctx[:150]))

    if missing:
        print("\n*** UNMATCHED NUMBERS (%d) -- NOT PRESENT IN ANY SOURCE ***" % len(missing))
        for tok in missing:
            print("    %s" % tok)
        print("\nRED: the fold asserts numbers its sources do not contain.")
        return 1

    print("\nGREEN: every non-trivial number in the fold appears in a source.")
    print("       This is necessary, not sufficient -- read the qualifier bucket.")
    return 0


def commission():
    """Self-test. A checker nobody has tried to fool is not a checker."""
    import tempfile
    import os

    source = (
        "# Fake report\n\n"
        "Per-frame brightness drift explains only 60.9% of the effect; 39.1%\n"
        "survives removing it entirely. The shipped gate averages 166.8 of 299\n"
        "frames per pixel. The bound is 1.284 and the render reads 4.337.\n"
    )

    def fold_with(body):
        return "NEW_FACTS = [\n    (1, 'MEASURED', 'MX', %r),\n]\n" % body

    cases = []

    # POSITIVE: every number is in the source. Must be GREEN.
    cases.append((
        "positive: all numbers present",
        fold_with("Drift explains 60.9% and 39.1% survives; 166.8 of 299 frames; "
                  "bound 1.284 against 4.337."),
        0,
    ))

    # SABOTAGE 1: a transposed digit. Must be RED. This is the potent plant --
    # if presence-checking cannot catch a wrong number, the tool is inert.
    cases.append((
        "sabotage: 60.9 -> 69.0 (transposed)",
        fold_with("Drift explains 69.0% of the effect."),
        1,
    ))

    # SABOTAGE 2: a plausible invented number. Must be RED.
    cases.append((
        "sabotage: invented 88.2%",
        fold_with("The correction accounts for 88.2% of the patchwork."),
        1,
    ))

    # NULL: prose with no measurements must not be convicted.
    cases.append((
        "null: no numbers at all",
        fold_with("The mechanism is confirmed and the fix is refused."),
        0,
    ))

    # XREF NULL: cross-references must not be mistaken for measurements.
    cases.append((
        "null: cross-references only",
        fold_with("See fact 1678 and discipline 849, per M120 and rule 40."),
        0,
    ))

    tmp = tempfile.mkdtemp(prefix="foldcheck-")
    spath = os.path.join(tmp, "source.md")
    with io.open(spath, "w", encoding="utf-8") as fh:
        fh.write(source)

    failures = 0
    for name, body, expect in cases:
        fpath = os.path.join(tmp, "fold_%d.py" % len(name))
        with io.open(fpath, "w", encoding="utf-8") as fh:
            fh.write(body)
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run(fpath, [spath])
        ok = rc == expect
        print("  %-42s expect=%s got=%s  %s"
              % (name, "RED" if expect else "GREEN",
                 "RED" if rc else "GREEN", "ok" if ok else "*** FAIL ***"))
        if not ok:
            failures += 1
            print(buf.getvalue())

    print()
    if failures:
        print("COMMISSION FAILED: %d/%d" % (failures, len(cases)))
        return 1
    print("COMMISSION PASSED: %d/%d, including 2 sabotages that had to read RED."
          % (len(cases), len(cases)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fold", nargs="?")
    ap.add_argument("sources", nargs="*")
    ap.add_argument("--commission", action="store_true")
    args = ap.parse_args()

    if args.commission:
        raise SystemExit(commission())
    if not args.fold or not args.sources:
        ap.error("need a fold script and at least one source report")
    raise SystemExit(run(args.fold, args.sources))


if __name__ == "__main__":
    main()
