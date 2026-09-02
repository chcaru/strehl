"""Re-derive every number in M129's PREREGISTRATION.md from first principles.

The values are PARSED OUT OF THE DOCUMENT and compared against independently
recomputed ones. They are deliberately not hard-coded here: a checker that carries
its own copy of the answer tests nothing when the document drifts (M128 paid for
this lesson, and rule 35 names the class -- a test whose subject and object are the
same value has no power to fail).

Exit 0 if every claim reproduces, 1 otherwise.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import predict as P  # noqa: E402

DOC = os.path.join(os.path.dirname(HERE), "PREREGISTRATION.md")

fails = []
checks = 0


def cmp(label, got, want, places):
    """Compare a parsed document value against a recomputed one."""
    global checks
    checks += 1
    if round(float(got), places) != round(float(want), places):
        fails.append(f"{label}: doc {got} != recomputed {want:.{places}f}")


def rows(text, header_frag):
    """Yield the cell lists of the markdown table whose header contains a fragment."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if header_frag in ln and ln.lstrip().startswith("|"):
            j = i + 2  # skip the |---| separator
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                yield [c.strip() for c in lines[j].strip().strip("|").split("|")]
                j += 1
            return


def num(cell):
    """First numeric token in a cell, sign and decimals included."""
    m = re.search(r"-?\d+\.?\d*", cell.replace("**", ""))
    return float(m.group()) if m else None


def main(doc_path=DOC):
    global checks
    with open(doc_path, encoding="utf-8") as fh:
        text = fh.read()

    # --- 2.1 lattice reach -------------------------------------------------
    want_pitch = {"G1 or G2": 2.0 * P.PITCH_UM,
                  "GQ quincunx": P.PITCH_UM * 2.0 ** 0.5,
                  "full sensor": P.PITCH_UM}
    seen = set()
    for r in rows(text, "| lattice | pitch um | Nyquist cy/mm |"):
        name = r[0]
        if name not in want_pitch:
            fails.append(f"2.1 unexpected lattice row {name!r}")
            continue
        seen.add(name)
        cmp(f"2.1 {name} pitch", num(r[1]), want_pitch[name], 4)
        cmp(f"2.1 {name} nyquist", num(r[2]), P.nyquist_cymm(want_pitch[name]), 3)
    missing = set(want_pitch) - seen
    if missing:
        fails.append(f"2.1 missing lattice rows: {sorted(missing)}")

    # --- 2.2 hypotheses ----------------------------------------------------
    doc_fc = {}
    for r in rows(text, "| hypothesis | `f_c` at f/5.6 |"):
        tag = r[0].split()[0].replace("**", "")
        fc = num(r[1])
        doc_fc[tag] = fc
        b, n_eff = P.b_from_fc(fc, P.N_REF)
        cmp(f"2.2 {tag} N_eff", num(r[2]), n_eff, 3)
        cmp(f"2.2 {tag} B", num(r[3]), b, 4)
        cmp(f"2.2 {tag} p", num(r[4]), P.pupil(b), 4)
    for tag in ("H1", "H2", "H3"):
        if tag not in doc_fc:
            fails.append(f"2.2 missing hypothesis row {tag}")

    # The document's f_c values must be the ones predict.py registers.
    for tag, fc in zip(("H1", "H2", "H3"), [h[1] for h in P.HYPOTHESES]):
        if tag in doc_fc:
            cmp(f"2.2 {tag} f_c matches predict.py", doc_fc[tag], fc, 2)

    # --- 2.3 the ladder ----------------------------------------------------
    gq = P.nyquist_cymm(P.PITCH_UM * 2.0 ** 0.5)
    ladder_rows = list(rows(text, "| N | H1 | H2 | H3 | H3 margin under GQ reach |"))
    if len(ladder_rows) != len(P.APERTURES):
        fails.append(f"2.3 expected {len(P.APERTURES)} rows, found {len(ladder_rows)}")
    for r in ladder_rows:
        n = num(r[0])
        for col, tag in ((1, "H1"), (2, "H2"), (3, "H3")):
            fc_doc = num(r[col])
            fc_calc = P.fc_at(doc_fc[tag], n)
            cmp(f"2.3 f/{n} {tag} f_c", fc_doc, fc_calc, 2)
            # the IN / out tag must agree with the arithmetic, not with prose
            checks_tag = "IN" if fc_calc < gq else "out"
            if checks_tag not in r[col]:
                fails.append(f"2.3 f/{n} {tag} band tag {r[col]!r} "
                             f"contradicts f_c {fc_calc:.2f} vs GQ {gq:.2f}")
        cmp(f"2.3 f/{n} H3 margin", num(r[4]), gq - P.fc_at(doc_fc["H3"], n), 2)

    # --- 2.3's registered reading: f/11 is the lowest usable aperture ------
    lowest_in = min(n for n in P.APERTURES
                    if P.fc_at(doc_fc["H3"], n) < gq)
    if lowest_in != 11.0:
        fails.append(f"2.3/2.4 lowest in-band aperture for H3 recomputes to "
                     f"f/{lowest_in}, but the document's retrodiction argument "
                     f"depends on it being f/11")
    checks += 1

    # --- the 28.07% separation, quoted in section 0 and the ledger ---------
    m = re.search(r"a (\d+\.\d+)% separation", text)
    if not m:
        fails.append("section 0: could not find the quoted separation percentage")
    else:
        want = 100.0 * (doc_fc["H3"] - doc_fc["H2"]) / doc_fc["H2"]
        cmp("section 0 separation %", float(m.group(1)), want, 2)
        # and it must be aperture-independent, which is why one number suffices
        for n in P.APERTURES:
            s = 100.0 * (P.fc_at(doc_fc["H3"], n) - P.fc_at(doc_fc["H2"], n)) \
                / P.fc_at(doc_fc["H2"], n)
            cmp(f"separation invariant at f/{n}", s, want, 6)

    # --- T2's light ratio --------------------------------------------------
    m = re.search(r"~1/(\d+\.\d+) the light", text)
    if not m:
        fails.append("T2: could not find the quoted light ratio")
    else:
        cmp("T2 light ratio", float(m.group(1)), (18.0 / 5.6) ** 2, 1)

    # --- T4's wavelength sensitivity --------------------------------------
    m = re.search(r"at 500 nm, `B` at H2/H3 becomes (\d+\.\d+) / (\d+\.\d+); "
                  r"at 600 nm, (\d+\.\d+) /\s*(\d+\.\d+)", text)
    if not m:
        fails.append("T4: could not find the wavelength sensitivity sentence")
    else:
        for lam, g2, g3 in ((0.500, m.group(1), m.group(2)),
                            (0.600, m.group(3), m.group(4))):
            b2, _ = P.b_from_fc(doc_fc["H2"], P.N_REF, lam)
            b3, _ = P.b_from_fc(doc_fc["H3"], P.N_REF, lam)
            cmp(f"T4 B at H2 {lam * 1000:.0f}nm", float(g2), b2, 4)
            cmp(f"T4 B at H3 {lam * 1000:.0f}nm", float(g3), b3, 4)

    # --- DOF growth quoted in T1 ------------------------------------------
    m = re.search(r"grows (\d+\.\d+)x from f/5\.6 to f/18", text)
    if not m:
        fails.append("T1: could not find the quoted DOF growth")
    else:
        cmp("T1 DOF growth", float(m.group(1)), 18.0 / 5.6, 1)

    # --- report ------------------------------------------------------------
    print(f"{checks} claims re-derived from {os.path.basename(doc_path)}")
    if fails:
        print(f"\n{len(fails)} FAILED:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("all claims reproduce")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DOC))
