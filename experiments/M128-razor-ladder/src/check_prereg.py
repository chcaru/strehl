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
