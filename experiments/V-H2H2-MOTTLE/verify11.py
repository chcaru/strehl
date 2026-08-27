"""Re-derive every number in section 11 from the authoritative logs.

Same construction as verify10.py and same two lessons built in from the start, because
both were found the hard way there:

  SCOPED ANCHORS. Each claim names the region of the document it belongs to and the
  search is scoped before it is anchored. verify10's first version anchored on a row
  pattern alone; after whitespace collapsing, the end of one table row plus the start
  of the next spelled the anchor exactly, so 32 claims were checked against the wrong
  table. A pattern that can match in the wrong section is not an anchor.

  THE CHECK MUST READ THE DOCUMENT. verify10's derived checks compared log arithmetic
  to a constant typed into the verifier and never opened the file; both plants aimed
  at them were MISSED while every table plant was caught. Values here are read out of
  the shipped text and compared to values computed from the logs.

Commissioning plants a defect into a COPY of the document and requires RED each time.
"""
import io
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "docs" / "research" / "V-HEADTOHEAD2.md"
LOGS = pathlib.Path(r"C:\dev\strehl-out\V-H2H2\logs")

SUBJECTS = ["coffee-bubbles", "lead-1-cpl", "113MSDCF", "foam", "119MSDCF"]

SPANS = {
    "dose": (r"`mc=5`, the best dose that is never refused", r"`mc=3` moves nothing"),
    "comp": (r"## 11\.2 The comparators", r"## 11\.3"),
    "orch": (r"# 11\. The operative band", r"Both are true"),
    "repro": (r"The gauge reproduces ORCH's published figures", r"## 11\.2"),
    "cost": (r"\*\*It is not free", r"## 11\.4"),
    "gap": (r"## 11\.4 What this does", r"This does \*\*not\*\*"),
    "profile": (r"it is the\s+band profile", r"\*\*It is not free"),
    "sharpsite": (r"Measuring sharpness only at flat sites", r"`mc=5`, the best dose"),
}


def scope(doc, key):
    a, b = SPANS[key]
    ma = re.search(a, doc)
    if not ma:
        return None
    mb = re.search(b, doc[ma.start():])
    return doc[ma.start(): ma.start() + (mb.start() if mb else len(doc))]


def log_rows(subject):
    """Parse one bandsites log into {(mc, class): {...}}. Refuses a truncated log."""
    p = LOGS / ("band-%s.txt" % subject)
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    if "commissioned 14/14" not in txt:
        raise SystemExit("%s: gauge not commissioned in this log -- refusing" % p.name)
    rows = {}
    pat = re.compile(
        r"mc=(\d+)\s+(flat|detail)\s+([\d.]+) \[\s*([\d.]+),\s*([\d.]+)\]\s+"
        r"([\d.]+)\s+([\d.]+) \[\s*([\d.]+),\s*([\d.]+)\]\s+smoothed (\d+)/(\d+)")
    for m in pat.finditer(txt):
        rows[(int(m.group(1)), m.group(2))] = {
            "mid": m.group(3), "mlo": m.group(4), "mhi": m.group(5),
            "fine": m.group(6), "sharp": m.group(7),
            "slo": m.group(8), "shi": m.group(9),
            "nsm": int(m.group(10)), "n": int(m.group(11))}
    if not rows:
        raise SystemExit("%s: no measurement rows parsed -- refusing" % p.name)
    return rows


def comp_rows():
    """Parse the published-site comparator/dose log."""
    p = LOGS / "band-compare.txt"
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    if "commissioned 14/14" not in txt:
        raise SystemExit("%s: gauge not commissioned in this log -- refusing" % p.name)
    rows = {}
    pat = re.compile(
        r"^  (\S+(?: \(reference\))?)\s+.*?grain\s+([\d.]+)\s+sharp\s+([\d.]+)\s+"
        r"5-15\s+([\d.]+) 10-30\s+([\d.]+) 20-60\s+([\d.]+) 40-120\s+([\d.]+)"
        r" 100-300\s+([\d.]+) 50-400\s+([\d.]+)", re.M)
    for m in pat.finditer(txt):
        rows[m.group(1)] = {
            "grain": m.group(2), "sharp": m.group(3), "5-15": m.group(4),
            "10-30": m.group(5), "20-60": m.group(6), "40-120": m.group(7),
            "100-300": m.group(8), "50-400": m.group(9)}
    for need in ("enfuse", "focus-stack", "mc=5"):
        if need not in rows:
            raise SystemExit("band-compare.txt: %r row missing -- refusing" % need)
    return rows


def build():
    claims = []
    for s in SUBJECTS:
        r = log_rows(s)
        for cls in ("flat", "detail"):
            k = (5, cls)
            if k not in r:
                raise SystemExit("%s: mc=5 %s missing from log" % (s, cls))
            d = r[k]
            anchor = r"\| `%s` \|([^|]*\|){4}" % re.escape(s)
            claims.append(("%s mc5 %s mid" % (s, cls), "dose", anchor, d["mid"]))
            claims.append(("%s mc5 %s ci-lo" % (s, cls), "dose", anchor, d["mlo"]))
            claims.append(("%s mc5 %s ci-hi" % (s, cls), "dose", anchor, d["mhi"]))
            claims.append(("%s mc5 %s sharp" % (s, cls), "dose", anchor, d["sharp"]))
            if cls == "detail":
                # The doc quotes a CI on detail sharpness; without these two claims a
                # plant on the interval passes, which is how this gap was found.
                claims.append(("%s mc5 detail sharp-lo" % s, "dose", anchor, d["slo"]))
                claims.append(("%s mc5 detail sharp-hi" % s, "dose", anchor, d["shi"]))
        # mc=7 must be refused at BOTH classes on every subject; the doc says 8/8.
        for cls in ("flat", "detail"):
            if (7, cls) in r:
                d = r[(7, cls)]
                if d["nsm"] != d["n"]:
                    raise SystemExit("%s mc=7 %s: log says %d/%d smoothed, doc claims all"
                                     % (s, cls, d["nsm"], d["n"]))

    # Section 11.2's comparator table, from the published-site log.
    c = comp_rows()
    for arm, key in (("enfuse", "enfuse"), ("focus-stack", "focus-stack")):
        anchor = r"\| `%s` \|([^|]*\|){5}" % re.escape(arm)
        for field in ("grain", "sharp", "5-15", "20-60", "50-400"):
            claims.append(("%s %s" % (arm, field), "comp", anchor, c[key][field]))

    # Section 11.3's prose band profile and published-site sharpness. These were
    # stated in prose and covered by no claim until a commissioning plant landed on
    # one of them instead of the table row it was aimed at.
    for field, val in (("20-60", c["mc=5"]["20-60"]), ("100-300", c["mc=5"]["100-300"]),
                       ("50-400", c["mc=5"]["50-400"])):
        claims.append(("mc5 published-site %s" % field, "profile",
                       r"`119MSDCF` it takes 20-60 to [\d.]+ while leaving "
                       r"100-300 at [\d.]+ and 50-400 at [\d.]+", val))
    claims.append(("mc5 published-site sharp", "sharpsite",
                   r"published site `mc=5` reads sharp \*\*([\d.]+)\*\*", c["mc=5"]["sharp"]))
    # The prose restates the detail-site figure; a commissioning plant landed here
    # rather than on the table row it named, which is how this gap was found.
    d119 = log_rows("119MSDCF")[(5, "detail")]
    claims.append(("mc5 prose detail sharp", "sharpsite",
                   r"it reads \*\*[\d.]+ \[[\d.]+, [\d.]+\]\*\*",
                   "%s [%s, %s]" % (d119["sharp"], d119["slo"], d119["shi"])))
    return claims


def derived(doc):
    """Percentages stated in prose, recomputed from the logs and READ FROM THE DOC."""
    out = []
    span = scope(doc, "cost")
    want = {}
    for s in SUBJECTS:
        r = log_rows(s)
        want[s] = "%.1f%%" % ((1.0 - float(r[(5, "detail")]["sharp"])) * 100.0)
    if span:
        for s in SUBJECTS:
            m = re.search(r"([\d.]+%%) on `%s`" % re.escape(s), span)
            got = m.group(1) if m else None
            out.append(("detail sharp cost %s" % s, got == want[s],
                        "doc %s, computed %s" % (got, want[s])))
    else:
        out.append(("cost span present", False, "span absent"))

    g = scope(doc, "gap")
    r119 = log_rows("119MSDCF")
    if g:
        m = re.search(r"delivers 0?\.943|delivers \*\*0\.893\*\*", g)
        out.append(("gap span quotes a delivered factor", m is not None, str(bool(m))))
        m2 = re.search(r"it delivers ([\d.]+)", g)
        want2 = r119[(5, "flat")]["mid"]
        out.append(("flat-site delivery matches log",
                    (m2.group(1) if m2 else None) == want2,
                    "doc %s, log %s" % (m2.group(1) if m2 else None, want2)))
    return out


def check(doc, claims):
    ok = bad = 0
    for label, span_key, anchor, value in claims:
        span = scope(doc, span_key)
        if span is None:
            bad += 1
            print("  FAIL  %-42s span %r absent" % (label, span_key))
            continue
        m = re.search(anchor, span)
        if m and value in m.group(0):
            ok += 1
        else:
            bad += 1
            print("  FAIL  %-42s %s" % (label, "anchor absent" if not m
                                        else "value %r not in anchored span" % value))
    return ok, bad


def run(doc, claims):
    ok, bad = check(doc, claims)
    for label, good, detail in derived(doc):
        if good:
            ok += 1
        else:
            bad += 1
            print("  FAIL  %-42s %s" % (label, detail))
    return ok, bad


def main():
    raw = io.open(DOC, encoding="utf-8").read()
    doc = re.sub(r"[ \t]*\r?\n[ \t]*", " ", raw)
    claims = build()

    print("COMMISSIONING the verifier (each planted defect must turn it RED)")
    plants = [
        ("cb flat mid", "| `coffee-bubbles` | 0.791 [0.762, 0.820] |",
         "| `coffee-bubbles` | 0.792 [0.762, 0.820] |"),
        ("foam flat sharp", "| 0.441 [0.430, 0.454] | **0.844** |",
         "| 0.441 [0.430, 0.454] | **0.845** |"),
        ("119 detail sharp", "| 0.922 [0.918, 0.933] | 0.955 [0.944, 0.960] |",
         "| 0.922 [0.918, 0.933] | 0.955 [0.944, 0.961] |"),
        ("119 prose detail sharp", "it reads **0.955 [0.944, 0.960]**.",
         "it reads **0.955 [0.944, 0.961]**."),
        ("enfuse mid", "| `enfuse` | 2.193 | 2.191 | 0.882 | **0.889** |",
         "| `enfuse` | 2.193 | 2.191 | 0.882 | **0.879** |"),
        ("focus-stack sharp", "| `focus-stack` | 0.123 | 0.095 |",
         "| `focus-stack` | 0.123 | 0.096 |"),
        ("published-site sharp", "published site `mc=5` reads sharp **0.981**",
         "published site `mc=5` reads sharp **0.982**"),
        ("band profile 100-300", "while leaving 100-300 at 0.996",
         "while leaving 100-300 at 0.998"),
        ("prose cost foam", "10.6% on `foam`", "10.7% on `foam`"),
        ("prose delivery", "it delivers 0.943", "it delivers 0.941"),
    ]
    caught = void = 0
    for name, old, new in plants:
        # A plant that lands on a different occurrence than the one it names measures
        # nothing. verify11's first run reported MISSED for a table plant whose target
        # string occurred twice; the mutation landed in prose that no claim covered,
        # so the control was void and the MISSED was a statement about the plant.
        n = raw.count(old)
        if n != 1:
            print("  %-22s PLANT TARGET OCCURS %d TIMES -- control is void" % (name, n))
            void += 1
            continue
        mutated = re.sub(r"[ \t]*\r?\n[ \t]*", " ", raw.replace(old, new, 1))
        o, b = run(mutated, claims)
        print("  %-22s planted -> %s" % (name, "CAUGHT" if b else "MISSED"))
        caught += bool(b)
    print("  commissioned %d/%d  (%d void)" % (caught, len(plants), void))

    print("\nVERIFYING the shipped section 11")
    ok, bad = run(doc, claims)
    total = ok + bad
    print("  %d/%d numeric claims verified  %s" % (ok, total, "GREEN" if not bad else "RED"))
    return 0 if (not bad and not void and caught == len(plants)) else 1


if __name__ == "__main__":
    sys.exit(main())
