"""Verify section 13 against coh.json and a live run of commcoh.py.

Same rule as verify12.py: this file holds no expected values. Every number is
parsed out of the document on one side and out of an artifact or a subprocess on
the other. Run with `--plant N` to mutate the document and confirm the covering
check fails.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "..", "..", "docs", "research", "V-HEADTOHEAD2.md")
OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"
PROV = r"C:\dev\strehl-out\V-H2H2\ladder\prov"
BANDS = ["5-15", "20-60", "40-120"]

FAIL = []
NCHECK = [0]
CONSUMED = set()


def consume(*vals):
    for v in vals:
        s = str(v).strip().replace(",", "")
        CONSUMED.add(s)
        CONSUMED.add(s.lstrip("+-"))


def check(name, ok, detail):
    NCHECK[0] += 1
    print("  %-4s %-48s %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        FAIL.append(name)


def section(doc, tag):
    """Slice one section, bounded by the NEXT heading.

    Slicing to the end of the document instead lets a later section satisfy a
    check about an earlier one.  Commissioning plant [24] proved it: it changed
    `reference frame 9` in 13.5, and the check still passed because 13.6 quotes
    the same string while describing the check itself.  A presence test is
    satisfied by any duplicate of the value, so each test needs its own anchor.
    """
    start = doc.index("## " + tag)
    nxt = doc.find("\n## ", start + 1)
    return doc[start:nxt if nxt != -1 else len(doc)]


def read_text(path):
    """Read a file whose encoding is not under my control.

    The render logs are written by PowerShell's `*>` redirect, which emits
    UTF-16LE with a BOM.  Reading one as UTF-8 with errors="replace" does not
    raise -- it silently yields a string of replacement characters in which no
    search term is ever found, so an encoding fault presents as a false claim.
    This check caught exactly that.
    """
    raw = io.open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def num(s):
    return float(s)


def quoted(s, value):
    """A quoted number is right iff re-formatting the artifact at the document's
    own precision reproduces the document's string exactly.

    A *tolerance* cannot do this job.  When the true value lands near the
    midpoint between two quotable strings, a half-ulp tolerance admits both
    neighbours; a tolerance tight enough to exclude the wrong one also excludes
    the right one.  Commissioning plant [2] walked straight through that hole:
    recover = 89.555228, the document quotes 89.6, and the planted 89.5 was
    0.0552 away against a 0.06 bar, so both passed.  Re-formatting has no slack
    to tune -- it either reproduces the glyphs or it does not.
    """
    s = s.strip().replace(",", "")
    body = s.lstrip("+-")
    dp = len(body.split(".")[1]) if "." in body else 0
    fmt = "%+.*f" if s.startswith("+") else "%.*f"
    return fmt % (dp, value) == s


def main():
    plant = None
    if "--plant" in sys.argv:
        plant = int(sys.argv[sys.argv.index("--plant") + 1])

    raw = io.open(DOC, encoding="utf-8").read()
    doc = raw[raw.index("\n## 13 Coherence between half-stacks"):]
    coh = json.load(open(os.path.join(OUT, "coh.json")))
    rows = coh["rows"]

    plants = [
        ("measure cell raw", "| 37 | 20.81 px | 20-60 | 0.2201 |",
         "| 37 | 20.81 px | 20-60 | 0.2301 |"),
        ("measure cell field", "| 74 | 10.46 px | 5-15 |", "| 74 | 10.40 px | 5-15 |"),
        ("measure cell recover", "| 0.0115 | 0.8968 | 89.6% |",
         "| 0.0115 | 0.8968 | 89.5% |"),
        ("rho field cell", "| 5-15 | **-1.000** | -0.200 |",
         "| 5-15 | **-0.900** | -0.200 |"),
        ("rho N cell", "| 20-60 | -0.800 | -0.400 |", "| 20-60 | -0.800 | -0.500 |"),
        ("total ratio", "2.5955 -> 5.2111 (**2.01x**)",
         "2.5955 -> 5.2111 (**2.11x**)"),
        ("closed form noise", "| 0.90 | 0.5564 | 0.5525 |",
         "| 0.90 | 0.5564 | 0.5535 |"),
        ("closed form selection", "| 1.00 | 0.7498 | 0.7500 |",
         "| 1.00 | 0.7488 | 0.7500 |"),
        ("shift table", "| **3 px shift** | **0.5085** |",
         "| **3 px shift** | **0.5185** |"),
        ("total unmoved", "untouched to 0.29%", "untouched to 0.39%"),
        ("hostile noise", "yields **gamma = 0.0038**", "yields **gamma = 0.0138**"),
        ("hostile closed form", "returns **0.1012** against a\nclosed form of 0.1000",
         "returns **0.1012** against a\nclosed form of 0.1200"),
        ("check count", "GREEN at 16 checks", "GREEN at 17 checks"),
        ("shift recovery", "gamma -0.1292 recovers to **0.9822**",
         "gamma -0.1292 recovers to **0.9922**"),
        ("magnification unrecovered", "size measured in 12.4: 0.8785",
         "size measured in 12.4: 0.8685"),
        ("prov band gamma", "| 20-60 | 5336.017993 | 5338.234590 | 0.999585 | "
                            "0.999998042 |",
         "| 20-60 | 5336.017993 | 5338.234590 | 0.999585 | 0.999998043 |"),
        ("prov pixels differing", "| pixels differing | 77,495,786 of 98,898,048 "
                                  "(78.36%) |",
         "| pixels differing | 77,495,786 of 98,898,048 (78.37%) |"),
        ("prov drift fraction", "**drift as a fraction of the image** | **1.04%**",
         "**drift as a fraction of the image** | **1.05%**"),
        ("prov frame-set contrast", "changing the frame set moves it by up to\n0.6125**",
         "changing the frame set moves it by up to\n0.8600**"),
        ("prov coherence floor", "coherent with each other at gamma > 0.99999",
         "coherent with each other at gamma > 0.999999"),
        ("m103 row", "| `deep()`, as shipped | 150.3 px | **36.4 px** |",
         "| `deep()`, as shipped | 150.3 px | **36.5 px** |"),
        ("m103 fix row", "| `iterated_wide()`, M103's fix | 2.9 px | **37.5 px** |",
         "| `iterated_wide()`, M103's fix | 2.9 px | **37.6 px** |"),
        ("m103 quotation", "It gathers each frame at its own `a_k`.",
         "It gathers each frame at its own `a_j`."),
        ("m103 warpmap reference", "`bee-3-cpl/warpmap.txt` says\n`reference 149`",
         "`bee-3-cpl/warpmap.txt` says\n`reference 148`"),
        ("my log reference", "logs `reference frame 9` of 19",
         "logs `reference frame 8` of 19"),
        ("13.6 check count", "**State: GREEN at 60 checks, 0 failed",
         "**State: GREEN at 61 checks, 0 failed"),
        ("13.6 census", "161 of 199 numeric literals verified",
         "162 of 199 numeric literals verified"),
        ("13.6 plant count", "Commissioning GREEN at 28 plants, 28 caught",
         "Commissioning GREEN at 29 plants, 29 caught"),
    ]
    if plant is not None:
        nm, old, new = plants[plant]
        n = doc.count(old)
        if n != 1:
            sys.exit("PLANT TARGET OCCURS %d TIMES -- control is void (%r)" % (n, old))
        doc = doc.replace(old, new, 1)
        print("PLANTED [%d] %s: %r -> %r\n" % (plant, nm, old, new))

    print("1. the measurement table vs coh.json")
    mrows = re.findall(r"^\| (\d+) \| ([\d.]+) px \| ([\d-]+) \| ([-\d.]+) \| "
                       r"([-\d.]+) \| ([\d.]+)% \| ([\d.]+) \|$", doc, re.M)
    check("a row for every rung and band", len(mrows) == len(rows) * len(BANDS),
          "%d rows in the document, %d expected from the artifact"
          % (len(mrows), len(rows) * len(BANDS)))
    for n, fld, band, gr, gg, rec, tot in mrows:
        consume(n, fld, gr, gg, rec, tot)
        r = rows.get(n)
        if r is None or band not in r:
            check("rung %s %s" % (n, band), False, "not in the artifact")
            continue
        c = r[band]
        ok = (quoted(fld, r["field"])
              and quoted(gr, c["raw"])
              and quoted(gg, c["reg"])
              and quoted(rec, 100 * c["recover"])
              and quoted(tot, c["total_a"]))
        check("rung %s %s" % (n, band), ok,
              "doc %s/%s/%s/%s/%s  artifact %.2f/%.4f/%.4f/%.1f/%.4f"
              % (fld, gr, gg, rec, tot, r["field"], c["raw"], c["reg"],
                 100 * c["recover"], c["total_a"]))

    print("\n2. the rank-correlation table vs coh.json")
    rr = re.findall(r"^\| ([\d-]+) \| \*{0,2}([-\d.]+)\*{0,2} \| \*{0,2}([-\d.]+)"
                    r"\*{0,2} \|$", doc, re.M)
    rr = [t for t in rr if t[0] in BANDS]
    check("a rho row per band", len(rr) == len(BANDS),
          "%d rows, %d bands" % (len(rr), len(BANDS)))
    for band, rf, rn in rr:
        consume(rf, rn)
        a = coh["rho"][band]
        ok = quoted(rf, a["field"]) and quoted(rn, a["N"])
        check("rho %s" % band, ok, "doc %s/%s  artifact %+.3f/%+.3f"
              % (rf, rn, a["field"], a["N"]))

    print("\n3. the coherence-immune table vs coh.json")
    tr = re.findall(r"^\| ([\d-]+) \| ([\d.]+) -> ([\d.]+) \(\*{0,2}([\d.]+)x\*{0,2}\)"
                    r" \| \*\*([+\d.]+)\*\* \|$", doc, re.M)
    check("a total-detail row per band", len(tr) == len(BANDS),
          "%d rows, %d bands" % (len(tr), len(BANDS)))
    for band, lo, hi, ratio, rho in tr:
        consume(lo, hi, ratio, rho)
        a_lo = rows["18"][band]["total_a"]
        a_hi = rows["149"][band]["total_a"]
        ok = (quoted(lo, a_lo) and quoted(hi, a_hi)
              and quoted(ratio, a_hi / a_lo)
              and quoted(rho, coh["rho"][band]["total_N"]))
        check("total %s" % band, ok, "doc %s->%s %sx rho %s  artifact %.4f->%.4f "
              "%.3fx rho %+.3f" % (lo, hi, ratio, rho, a_lo, a_hi, a_hi / a_lo,
                                   coh["rho"][band]["total_N"]))

    print("\n4. commissioning claims, re-run live")
    r = subprocess.run([sys.executable, os.path.join(HERE, "commcoh.py")],
                       capture_output=True, text=True)
    so = r.stdout
    last = so.strip().splitlines()[-1]
    check("commissioning is green", r.returncode == 0 and last.startswith("GREEN"),
          "commcoh.py exit %d, last line %r" % (r.returncode, last[:32]))
    nck = len(re.findall(r"^  (?:PASS|FAIL) ", so, re.M))
    m = re.search(r"GREEN at (\d+) checks", doc)
    if m:
        consume(m.group(1))
    check("check count in the document matches the suite",
          m is not None and int(m.group(1)) == nck,
          "document says %s, suite ran %d" % (m.group(1) if m else "?", nck))

    # the two closed-form tables are quoted from the suite, so read the suite
    lines = {"noise": re.search(r"three noise levels\s+(r=.*)$", so, re.M),
             "selection": re.search(r"per-pixel selection (r=.*)$", so, re.M)}
    for label in ("noise", "selection"):
        live = re.findall(r"r=([\d.]+) ([-\d.]+) vs ([-\d.]+)",
                          lines[label].group(1) if lines[label] else "")
        docrows = [t for t in re.findall(r"^\| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$",
                                         doc, re.M)]
        # the two tables are consecutive; match each live row to a doc row by r
        okall, det = True, []
        for rr_, mv, pv in live:
            hit = [d for d in docrows if abs(num(d[0]) - num(rr_)) < 1e-9
                   and abs(num(d[1]) - num(mv)) < 1e-9]
            if not hit:
                hit2 = [d for d in docrows if abs(num(d[0]) - num(rr_)) < 1e-9]
                okall = False
                det.append("r=%s live %s/%s doc %s" % (rr_, mv, pv,
                                                       hit2[0] if hit2 else "missing"))
                continue
            consume(*hit[0])
            if not quoted(hit[0][2], num(pv)):
                okall = False
                det.append("r=%s closed form doc %s live %s" % (rr_, hit[0][2], pv))
        check("closed-form table (%s) matches the suite" % label, okall and live != [],
              "; ".join(det) if det else "%d rows agree" % len(live))

    sh = re.search(r"d=1 -> ([-\d.]+), d=3 -> ([-\d.]+), d=10 -> ([-\d.]+)", so)
    docsh = re.findall(r"^\| \*{0,2}(\d+) px shift\*{0,2} \| \*{0,2}([-\d.]+)"
                       r"\*{0,2} \|", doc, re.M)
    ok, det = sh is not None and len(docsh) == 3, []
    if ok:
        for (d, v), lv in zip(docsh, sh.groups()):
            consume(d, v)
            if not quoted(v, num(lv)):
                ok = False
                det.append("d=%s doc %s live %s" % (d, v, lv))
    check("the shift table matches the suite", ok,
          "; ".join(det) if det else "3 rows agree")

    tu = re.search(r"total [\d.]+ -> [\d.]+ \(([\d.]+)%\)", so)
    dtu = re.search(r"untouched to ([\d.]+)%", doc)
    if dtu:
        consume(dtu.group(1))
    check("total-energy-unmoved figure matches the suite",
          tu is not None and dtu is not None
          and quoted(dtu.group(1), num(tu.group(1))),
          "doc %s%%  suite %s%%" % (dtu.group(1) if dtu else "?",
                                    tu.group(1) if tu else "?"))

    hb = re.search(r"best-shift ([-\d.]+) at", so)
    dhb = re.search(r"yields \*\*gamma = ([-\d.]+)\*\*", doc)
    if dhb:
        consume(dhb.group(1))
    check("hostile best-shift figure matches the suite",
          hb is not None and dhb is not None
          and quoted(dhb.group(1), num(hb.group(1))),
          "doc %s  suite %s" % (dhb.group(1) if dhb else "?",
                                hb.group(1) if hb else "?"))
    hc = re.search(r"registered ([\d.]+) against 1/\(1\+r\^2\) = ([\d.]+)", so)
    dhc = re.search(r"returns \*\*(\d+\.\d+)\*\* against a\s+closed form of (\d+\.\d+)",
                    doc)
    if dhc:
        consume(*dhc.groups())
    check("hostile closed-form figures match the suite",
          hc is not None and dhc is not None
          and quoted(dhc.group(1), num(hc.group(1)))
          and quoted(dhc.group(2), num(hc.group(2))),
          "doc %s/%s  suite %s/%s" % (dhc.groups() + hc.groups() if dhc and hc
                                      else ("?", "?", "?", "?")))

    # the registration-recovery bullets in 13.1 are the load-bearing claim that
    # separates displacement from selection, so they are parsed too
    lsh = re.search(r"registration recovers a pure shift\s+raw ([-\d.]+) -> "
                    r"registered ([\d.]+)", so)
    dsh = re.search(r"gamma ([-\d.]+) recovers to \*\*([\d.]+)\*\*", doc)
    if dsh:
        consume(*dsh.groups())
    check("the pure-shift recovery matches the suite",
          lsh is not None and dsh is not None
          and quoted(dsh.group(1), num(lsh.group(1)))
          and quoted(dsh.group(2), num(lsh.group(2))),
          "doc %s->%s  suite %s->%s"
          % ((dsh.groups() + lsh.groups()) if dsh and lsh else ("?",) * 4))
    lmg = re.search(r"NOT fully recovered by an integer shift raw ([\d.]+) -> "
                    r"registered ([\d.]+)", so)
    dmg = re.search(r"which is the size measured in 12\.4: \*{0,2}([\d.]+)", doc)
    if dmg:
        consume(dmg.group(1))
    check("the magnification case matches the suite",
          lmg is not None and dmg is not None
          and quoted(dmg.group(1), num(lmg.group(1)))
          and abs(num(lmg.group(1)) - num(lmg.group(2))) <= 1e-9,
          "doc %s  suite %s -> %s (unrecovered)"
          % (dmg.group(1) if dmg else "?",
             lmg.group(1) if lmg else "?", lmg.group(2) if lmg else "?"))

    print("\n5. section 13.4 provenance vs provdiff.json")
    pv = json.load(open(os.path.join(PROV, "provdiff.json")))
    s4 = section(doc, "13.4") if "## 13.4" in doc else ""
    check("13.4 exists", s4 != "", "%d chars" % len(s4))
    # derived quantities the prose quotes, computed from the two artifacts rather
    # than read out of the document
    dv = {"drift_e6": 1e6 * max(abs(1.0 - v["gamma"]) for v in pv["bands"].values()),
          "span": max(abs(rows[a][b]["raw"] - rows[c][b]["raw"])
                      for b in BANDS for a in rows for c in rows),
          "agree_pct": 100 * max(abs(1.0 - v["ratio"]) for v in pv["bands"].values()),
          "min_gamma": min(v["gamma"] for v in pv["bands"].values())}
    scalars = [
        ("pixels differing", r"pixels differing \| ([\d,]+) of ([\d,]+) \(([\d.]+)%\)",
         (pv["n_diff"], pv["n_px"], pv["pct_diff"])),
        ("max abs difference", r"max abs difference \| ([\d,]+) DN", (pv["max_abs"],)),
        ("rms difference", r"rms difference \| ([\d.]+) DN", (pv["rms_diff"],)),
        ("image rms", r"image rms \| ([\d.]+) DN", (pv["image_rms"],)),
        ("drift fraction", r"drift as a fraction of the image\*\* \| \*\*([\d.]+)%",
         (pv["drift_frac_pct"],)),
        ("file size and delta",
         r"([\d,]+)\s+bytes apart in ([\d,]+)", (pv["size_delta"], pv["size_mine"])),
        ("frame-set contrast",
         r"moves gamma by ([\d.]+)e-6; changing the frame set moves it by up to\s+"
         r"([\d.]+)\*\*", (dv["drift_e6"], dv["span"])),
        ("band agreement", r"Band energy agrees to ([\d.]+)% in every",
         (dv["agree_pct"],)),
        ("perturbation gamma", r"A perturbation at gamma = ([\d.]+)",
         (dv["min_gamma"],)),
    ]
    for label, pat, vals in scalars:
        m = re.search(pat, s4)
        if m is None:
            check("13.4 %s" % label, False, "no match for %r" % pat)
            continue
        consume(*m.groups())
        bad = [(g, v) for g, v in zip(m.groups(), vals) if not quoted(g, v)]
        check("13.4 %s" % label, not bad,
              "; ".join("doc %s artifact %r" % (g, v) for g, v in bad) or "matches")

    # "gamma > 0.99999" is a BOUND, not a quotation -- re-formatting the artifact
    # at 5 dp gives 1.00000, so requiring it to reproduce the glyphs would be
    # wrong.  It is checked as the inequality it claims to be.
    mfl = re.search(r"coherent with each other at gamma > ([\d.]+)", s4)
    if mfl:
        consume(mfl.group(1))
    check("13.4 the stated coherence floor is a true bound",
          mfl is not None and dv["min_gamma"] > num(mfl.group(1)),
          "claims > %s, worst measured gamma %.9f"
          % (mfl.group(1) if mfl else "?", dv["min_gamma"]))

    brows = re.findall(r"^\| ([\d-]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| "
                       r"([\d.]+) \|$", s4, re.M)
    brows = [t for t in brows if t[0] in BANDS]
    check("13.4 a drift row per band", len(brows) == len(BANDS),
          "%d rows, %d bands" % (len(brows), len(BANDS)))
    for band, mn, pn, ra, gm in brows:
        consume(mn, pn, ra, gm)
        c = pv["bands"][band]
        check("13.4 drift %s" % band,
              quoted(mn, c["mine"]) and quoted(pn, c["pin"])
              and quoted(ra, c["ratio"]) and quoted(gm, c["gamma"]),
              "doc %s/%s/%s/%s  artifact %.6f/%.6f/%.6f/%.9f"
              % (mn, pn, ra, gm, c["mine"], c["pin"], c["ratio"], c["gamma"]))

    # the section's load-bearing claim is a COMPARISON of two magnitudes, so it is
    # checked as an inequality against both artifacts rather than as a quotation
    best_g = max(abs(1.0 - v["gamma"]) for v in pv["bands"].values())
    span = dv["span"]
    check("13.4 binary drift is orders of magnitude below frame-set effect",
          best_g < 1e-4 and span > 0.5 and span / best_g > 1e4,
          "worst 1-gamma %.3g, largest frame-set gamma span %.4f, ratio %.3g"
          % (best_g, span, span / best_g))
    check("13.4 every band agrees to better than 0.1%%",
          all(abs(1.0 - v["ratio"]) < 1e-3 for v in pv["bands"].values()),
          "worst band ratio %.6f"
          % max(pv["bands"].values(), key=lambda v: abs(1.0 - v["ratio"]))["ratio"])
    check("13.4 the renders are not pixel-identical, as the section states",
          pv["pixel_identical"] is False and pv["n_diff"] > 0,
          "pixel_identical=%r n_diff=%d" % (pv["pixel_identical"], pv["n_diff"]))

    print("\n6. section 13.5 quotations, checked at the primary source")
    m103 = io.open(os.path.join(HERE, "..", "..", "docs", "research",
                                "M103-halfdrift.md"), encoding="utf-8").read()
    # quotations are checked against whitespace-collapsed text: this document and
    # that one wrap at different columns, so a phrase that is contiguous in one is
    # split across a line break in the other and a literal search returns a false
    # negative
    flat103 = re.sub(r"\s+", " ", m103)
    s5 = section(doc, "13.5") if "## 13.5" in doc else ""
    check("13.5 exists", s5 != "", "%d chars" % len(s5))
    q = re.search(r"> (But the merge does not gather frames end to end\..*?`a_k`\.)", s5)
    check("13.5 the quoted sentence is in M103",
          q is not None and re.sub(r"\s+", " ", q.group(1)) in flat103,
          "quoted %r" % (q.group(1)[:48] if q else "no quote found"))
    m103rows = re.findall(r"\| `(deep\(\)|iterated_wide\(\))`[^|]*\| ([\d.]+) px \| "
                          r"\*\*([\d.]+) px\*\* \|", s5)
    check("13.5 both solve rows are quoted", len(m103rows) == 2,
          "%d rows found" % len(m103rows))
    for solve, e2e, perframe in m103rows:
        consume(e2e, perframe)
        row = re.search(r"\| `%s`[^|]*\| ([\d.]+) px \| \*\*([\d.]+) px\*\* \|"
                        % re.escape(solve), flat103)
        check("13.5 %s row matches M103" % solve,
              row is not None and row.group(1) == e2e and row.group(2) == perframe,
              "mine %s/%s  M103 %s" % (e2e, perframe,
                                       "/".join(row.groups()) if row else "not found"))
    for lit, src, where in ((r"reference 149", flat103, "M103"),
                            (r"reference frame 9", None, "my render log")):
        dm = re.search(r"`%s`" % lit, s5)
        if src is None:
            log = read_text(os.path.join(PROV, "mine.log"))
            src = re.sub(r"\s+", " ", log)
        check("13.5 %r appears in %s" % (lit, where),
              dm is not None and lit in src,
              "in document: %s; in source: %s" % (dm is not None, lit in src))
    # the consistency argument is an inequality between two measurements, so it is
    # checked as one rather than asserted in prose
    pf = float(m103rows[0][2]) if m103rows else 0.0
    worst_field = max(r["field"] for r in rows.values())
    check("13.5 my fields are below M103's per-frame placement, as argued",
          0 < worst_field < pf,
          "largest field %.2f px, M103 per-frame placement %.1f px"
          % (worst_field, pf))

    print("\n7. coverage census")
    # Measured over 13.1-13.2, 13.4 and 13.5 only.  13.6 quotes the census, and a
    # census that counted its own quotation could never be quoted correctly.
    body = doc[:doc.index("## 13.3")] if "## 13.3" in doc else doc
    if "## 13.4" in doc:
        end = doc.index("## 13.6") if "## 13.6" in doc else len(doc)
        body += doc[doc.index("## 13.4"):end]
    body = body.replace(",", "")
    body = re.sub(r"`[^`]*`", "", body)
    body = re.sub(r"^#+ [\d.]+", "", body, flags=re.M)
    body = re.sub(r"\b(?:5-15|20-60|40-120)\b", "", body)
    lits = re.findall(r"(?<![\w.])(\d+\.\d+|\d+)(?![\w.])", body)
    uncov = {}
    for v in lits:
        if v not in CONSUMED:
            uncov[v] = uncov.get(v, 0) + 1
    nu = sum(uncov.values())
    print("     %d numeric literals in 13.1-13.2, 13.4 and 13.5: %d verified against "
          "an artifact, %d NOT COVERED" % (len(lits), len(lits) - nu, nu))
    if uncov:
        print("     not covered: " + ", ".join(sorted(uncov, key=lambda k: -uncov[k])))

    print("\n8. 13.6's account of this suite, checked against this suite")
    s6 = section(doc, "13.6") if "## 13.6" in doc else ""
    qc = re.search(r"GREEN at (\d+) checks, 0 failed, (\d+) of (\d+) numeric literals "
                   r"verified against an\s+artifact and (\d+) declared uncovered", s6)
    # NCHECK is read while this check's own arguments are being evaluated, so it
    # does not yet include the three checks in this block.  The document quotes
    # the final total, which is why the three are added back.
    REMAINING = 3
    check("the check count quoted in 13.6 is this suite's own",
          qc is not None and int(qc.group(1)) == NCHECK[0] + REMAINING,
          "document says %s, suite will finish at %d"
          % (qc.group(1) if qc else "?", NCHECK[0] + REMAINING))
    check("the census quoted in 13.6 is this census",
          qc is not None and (int(qc.group(2)), int(qc.group(3)), int(qc.group(4)))
          == (len(lits) - nu, len(lits), nu),
          "document says %s of %s verified, %s uncovered; census says %d of %d, %d"
          % (((qc.group(2), qc.group(3), qc.group(4)) if qc else ("?", "?", "?"))
             + (len(lits) - nu, len(lits), nu)))
    qp = re.search(r"Commissioning GREEN at (\d+) plants, (\d+) caught by a new\s+"
                   r"failure, (\d+) unaccounted", s6)
    check("the plant count quoted in 13.6 is the number of plants defined",
          qp is not None and int(qp.group(1)) == len(plants)
          and int(qp.group(2)) == len(plants) and int(qp.group(3)) == 0,
          "document says %s plants / %s caught / %s unaccounted, file defines %d"
          % (((qp.group(1), qp.group(2), qp.group(3)) if qp else ("?", "?", "?"))
             + (len(plants),)))

    print("\n%s  %d checks, %d failed, %d literals uncovered"
          % ("GREEN" if not FAIL else "RED: " + ", ".join(FAIL), NCHECK[0], len(FAIL),
             nu))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())


