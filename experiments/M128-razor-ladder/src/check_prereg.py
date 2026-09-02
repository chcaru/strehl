r"""M128 / check_prereg — re-derive PREREGISTRATION.md section 2 and compare.

This does NOT search the document for the presence of a number, which any
duplicate elsewhere would satisfy. It parses the three section-2 tables by
their headers, recomputes every cell from predict.py's functions, and compares
cell by cell at the printed precision. A cell present in the document but not
produced by the recomputation, or vice versa, is a failure.

    python src\check_prereg.py

Exit code 0 = GREEN, 1 = RED.
"""

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
import predict as P  # noqa: E402

DOC = Path(__file__).resolve().parents[1] / "PREREGISTRATION.md"
APS = [5.6, 8.0, 11.0]
NAMES = ["H1", "H2", "H3"]


def tables(text):
    """Split into (heading, rows) for every markdown table, keyed by the line
    of prose immediately preceding the table."""
    out = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("| ") and i + 1 < len(lines) and \
                set(lines[i + 1].replace("|", "").replace(" ", "")) <= set("-:"):
            head = [c.strip() for c in lines[i].strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip("|").split("|")])
                j += 1
            ctx = ""
            k = i - 1
            while k >= 0 and not ctx:
                if lines[k].strip():
                    ctx = lines[k].strip()
                k -= 1
            out.append((ctx, head, rows))
            i = j
        else:
            i += 1
    return out


def num(s):
    s = s.replace("**", "").strip()
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def main():
    text = DOC.read_text(encoding="utf-8")
    tabs = tables(text)
    fails, checks = [], 0

    def cmp(tag, got, want, places):
        nonlocal checks
        checks += 1
        if round(got, places) != round(want, places):
            fails.append(f"{tag}: doc {got} != recomputed {round(want, places)}")

    # --- table 1: hypothesis -> f_c, N_eff, B, p -------------------------
    t = [x for x in tabs if x[1][:2] == ["hypothesis", "`f_c` at f/5.6"]]
    if len(t) != 1:
        fails.append(f"section 2 table 1: found {len(t)} candidates, want 1")
    else:
        rows = t[0][2]
        if len(rows) != 3:
            fails.append(f"table 1 has {len(rows)} rows, want 3")
        for r, (nm, fc_src) in zip(rows, P.HYPOTHESES):
            fc, ne, b, p = (num(r[1]), num(r[2]), num(r[3]), num(r[4]))
            cmp(f"t1 {r[0]} f_c", fc, fc_src, 2)
            n_eff, bb, pp = P.invert(fc_src, P.N_REF)
            cmp(f"t1 {r[0]} N_eff", ne, n_eff, 3)
            cmp(f"t1 {r[0]} B", b, bb, 4)
            cmp(f"t1 {r[0]} p", p, pp, 4)

    # --- tables 2 and 3: rises in um and in green px ---------------------
    for want_head, div, places, label in (
            (["hypothesis", "f/5.6", "f/8", "f/11"], 1.0, 3, "um"),
            (["hypothesis", "f/5.6", "f/8", "f/11"], 2 * P.PITCH_UM, 4, "px")):
        pass
    rise_tabs = [x for x in tabs
                 if x[1] == ["hypothesis", "f/5.6", "f/8", "f/11"]]
    if len(rise_tabs) != 2:
        fails.append(f"rise tables: found {len(rise_tabs)}, want 2 "
                     "(um then green px)")
    else:
        for tab, div, places, label in ((rise_tabs[0], 1.0, 3, "um"),
                                        (rise_tabs[1], 2 * P.PITCH_UM, 4, "px")):
            rows = tab[2]
            if len(rows) != 3:
                fails.append(f"rise table {label} has {len(rows)} rows, want 3")
            for r, (nm, fc_src) in zip(rows, P.HYPOTHESES):
                if not nm.startswith(r[0].replace("**", "").strip()):
                    fails.append(f"rise table {label} row label {r[0]!r} does "
                                 f"not match hypothesis order {nm!r}")
                for j, n in enumerate(APS):
                    want = P.rise_um(fc_src * P.N_REF / n) / div
                    cmp(f"rise[{label}] {r[0]} f/{n:g}", num(r[j + 1]),
                        want, places)

    # --- prose claims that carry a number --------------------------------
    prose = [
        (r"pupil factor `p` = 1\), or in the range \*\*105\.54",
         "the two hypotheses are quoted in section 0"),
        (r"`p` = 1 requires `B` = 3\.7198",
         "the p=1 -> B round trip"),
        (r"`B` ∈ \[2\.412, 3\.064\]",
         "M5's measured bracket"),
        (r"`p` ∈ \[1\.318, 1\.926\]",
         "M5's bracket re-expressed with M84b's m"),
        (r"11\.71% of the largest rise at f/5\.6.*?15\.82% at f/11",
         "the separation trend across apertures"),
    ]
    flat = re.sub(r"\s+", " ", text)
    for pat, why in prose:
        checks += 1
        if not re.search(pat, flat, re.S):
            fails.append(f"prose claim missing or altered ({why}): /{pat}/")

    # independently recompute the two round trips the prose asserts
    checks += 1
    b_for_p1 = 1.0 + P.M_MAG
    if round(b_for_p1, 4) != 3.7198:
        fails.append(f"p=1 implies B={b_for_p1:.4f}, doc says 3.7198")
    for b, want in ((3.064, 1.318), (2.412, 1.926)):
        checks += 1
        p = P.M_MAG / (b - 1.0)
        if round(p, 3) != want:
            fails.append(f"B={b} implies p={p:.4f}, doc says {want}")
    for j, n in enumerate(APS):
        checks += 1
        vals = [P.rise_um(fc * P.N_REF / n) for _, fc in P.HYPOTHESES]
        gaps = [abs(vals[i] - vals[i + 1]) for i in range(2)]
        rel = round(min(gaps) / max(vals) * 100.0, 2)
        want = {0: 11.71, 1: 14.25, 2: 15.82}[j]
        if rel != want:
            fails.append(f"separation at f/{n:g} is {rel}%, doc says {want}%")

    # --- Amendment A2: the jitter correction ------------------------------
    # Every value here is PARSED FROM THE DOCUMENT and then re-derived. The
    # first version of this block compared re-derived values against constants
    # written in this file, so it never read the document at all: the
    # commissioner planted four A2 defects and all four were MISSED. A check
    # that does not read the thing it checks is decoration.
    text = DOC.read_text(encoding="utf-8")
    GREEN_PX_UM = 10.24
    GAUSS_1090 = 2.563

    a2_rows = re.findall(
        r"\|\s*f/([\d.]+)\s*\|\s*([\d.]+) px\s*\|\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|", text)
    checks += 1
    if len(a2_rows) != 3:
        fails.append(f"A2: found {len(a2_rows)} jitter rows, want 3")
        a2_rows = []

    a2_um, a2_smear = {}, {}
    for n_s, px_s, um_s, sm_s in a2_rows:
        n, px = float(n_s), float(px_s)
        checks += 1
        um = px * GREEN_PX_UM
        a2_um[n] = um
        if round(um, 2) != float(um_s):
            fails.append(f"A2: {px} px is {um:.4f} um, doc says {um_s}")
        checks += 1
        sm = GAUSS_1090 * um
        a2_smear[n] = sm
        if round(sm, 2) != float(sm_s):
            fails.append(f"A2: smear at f/{n:g} is {sm:.4f} um, doc says "
                         f"{sm_s}")

    if len(a2_smear) == 3:
        ns = sorted(a2_smear)
        xv = [n ** 2 for n in ns]
        yv = [a2_smear[n] ** 2 for n in ns]
        mx = sum(xv) / len(xv)
        my = sum(yv) / len(yv)
        slope = (sum((x - mx) * (y - my) for x, y in zip(xv, yv))
                 / sum((x - mx) ** 2 for x in xv))

        # s^2 the way the ladder itself obtains it: least-squares slope of
        # rise^2 against N^2 under H2. An earlier version used a hand-copied
        # a*lambda that was wrong by 2.7x and turned a 7.2% bias into 1.0%.
        _, fc_h2 = P.HYPOTHESES[1]
        rv = [P.rise_um(fc_h2 * P.N_REF / n) ** 2 for n in ns]
        mrv = sum(rv) / len(rv)
        s2_h2 = (sum((x - mx) * (y - mrv) for x, y in zip(xv, rv))
                 / sum((x - mx) ** 2 for x in xv))
        bias = ((s2_h2 + slope) ** 0.5 / s2_h2 ** 0.5 - 1.0) * 100.0

        m = re.search(r"([\d.]+) um\^2 into the fitted `s\^2`\. Against "
                      r"`s\^2 = ([\d.]+) um\^2`", text)
        checks += 1
        if not m:
            fails.append("A2: slope/s^2 prose sentence not found")
        else:
            checks += 1
            if round(slope, 4) != float(m.group(1)):
                fails.append(f"A2: slope is {slope:.4f} um^2, doc says "
                             f"{m.group(1)}")
            if round(s2_h2, 3) != float(m.group(2)):
                fails.append(f"A2: H2 s^2 is {s2_h2:.4f} um^2, doc says "
                             f"{m.group(2)}")

        m = re.search(r"\*\*\+([\d.]+)% in `s`, hence \+([\d.]+)% in\s+`B`"
                      r"\*\*: ([\d.]+) becomes ([\d.]+),", text)
        checks += 1
        if not m:
            fails.append("A2: bias prose sentence not found")
        else:
            checks += 2
            for g in (1, 2):
                if round(bias, 1) != float(m.group(g)):
                    fails.append(f"A2: bias is {bias:.3f}%, doc says "
                                 f"{m.group(g)}%")
            b_biased = float(m.group(3)) * (1.0 + bias / 100.0)
            if round(b_biased, 3) != float(m.group(4)):
                fails.append(f"A2: biased B is {b_biased:.4f}, doc says "
                             f"{m.group(4)}")

        # The spread that fails control C7's 20% bar.
        checks += 1
        spread = (max(a2_um.values()) / min(a2_um.values()) - 1.0) * 100.0
        m = re.search(r"The spread is (\d+)%, so \*\*C7 fails", text)
        if not m:
            fails.append("A2: C7-failure sentence not found")
        elif round(spread) != float(m.group(1)):
            fails.append(f"A2: spread is {spread:.1f}%, doc says {m.group(1)}%")
        checks += 1
        if spread <= 20.0:
            fails.append("A2: doc says control C7 fails, but the spread is "
                         f"{spread:.1f}%, inside C7's 20% bar")

    print(f"M128 pre-registration check: {checks} claims re-derived")
    if fails:
        print(f"\nRED  {len(fails)} mismatch(es):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nGREEN  every section-2 cell and numeric prose claim reproduces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
