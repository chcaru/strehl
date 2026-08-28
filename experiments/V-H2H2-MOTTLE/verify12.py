"""Verify every number in section 12 against the artifacts that produced them.

THE RULE THIS IS BUILT AROUND. A checker that compares the document against
constants written inside the checker is verifying its own copy of the answer.
Another lane passed 37/37 that way and then caught only 5 of 13 planted defects,
because eight of its checks could not fail no matter what the document said. So
every value here is parsed out of TWO independent places -- the document, and the
JSON the measurement wrote -- and neither is typed into this file.

Run with `--plant N` to mutate the document in memory and confirm the check that
covers claim N actually fails. A claim no plant can break is not a check.
"""
import io
import json
import os
import re
import subprocess
import sys

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "docs", "research", "V-HEADTOHEAD2.md")
OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"

FAIL = []
NCHECK = [0]
CONSUMED = set()


def consume(*vals):
    for v in vals:
        s = str(v).strip()
        CONSUMED.add(s)
        CONSUMED.add(s.lstrip("+-"))


def check(name, ok, detail):
    NCHECK[0] += 1
    print("  %-4s %-46s %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        FAIL.append(name)


def close(a, b, tol):
    return abs(a - b) <= tol * max(abs(b), 1e-12)


def section12(text):
    i = text.index("\n## 12 The N ladder")
    return text[i:]


def num(s):
    return float(s.replace(",", ""))


def main():
    plant = None
    if "--plant" in sys.argv:
        plant = int(sys.argv[sys.argv.index("--plant") + 1])

    raw = io.open(DOC, encoding="utf-8").read()
    doc = section12(raw)

    warp = json.load(open(os.path.join(OUT, "warp.json")))
    ladder = json.load(open(os.path.join(OUT, "ladder.json")))

    # --- plants: mutate the DOCUMENT, then require the covering check to fail ---
    plants = [
        ("warp rms cell", "| n37a vs n37b | 20.68 px", "| n37a vs n37b | 20.60 px"),
        ("warp scale cell", "| -1.367% |", "| -1.360% |"),
        ("absorb cell", "| n74a vs n74b | 9.90 px | -0.665% | 90% |",
         "| n74a vs n74b | 9.90 px | -0.665% | 91% |"),
        ("determinism hash", "pass2 AC0DD9E6F9C9FDBD263A309F79AEDBAE",
         "pass2 AC0DD9E6F9C9FDBD263A309F79AEDBAF"),
        ("ladder field rms", "| 18 | 14.69 px |", "| 18 | 14.60 px |"),
        ("ladder scene cell", "| 149 | 9.09 px | 2.6856 |", "| 149 | 9.09 px | 2.6800 |"),
        ("ladder sharpness cell", "| 2.5515 | 2.2158 |", "| 2.5515 | 2.2100 |"),
        ("iqr local sd", "sd **4.30%**", "sd **4.20%**"),
        ("block scatter ladder", "17.50% at k=16", "17.40% at k=16"),
        ("bound cell", "| **0.751%** |", "| **0.750%** |"),
        ("worst-case bias", "**2.03%** at flat sites", "**2.00%** at flat sites"),
        ("display gain", "One display gain, 2.6898,", "One display gain, 2.6890,"),
        ("refusal count", "a scene of zero at 3 of 4", "a scene of zero at 2 of 4"),
        ("census quotation", "70 verified against an artifact",
         "71 verified against an artifact"),
    ]
    if plant is not None:
        nm, old, new = plants[plant]
        n = doc.count(old)
        if n != 1:
            sys.exit("PLANT TARGET OCCURS %d TIMES -- control is void (%r)" % (n, old))
        doc = doc.replace(old, new, 1)
        print("PLANTED [%d] %s: %r -> %r\n" % (plant, nm, old, new))

    # ---- 1. the warp table, every cell, against warp.json ---------------------
    print("1. warp table vs warp.json")
    rows = re.findall(r"^\| (n\w+) vs (n\w+) \| ([\d.]+) px \| ([+-][\d.]+)% \| (\d+)% \|$",
                      doc, re.M)
    check("warp table has a row for every measured pair",
          len(rows) == len(warp["pairs"]),
          "%d rows in the document, %d pairs in the artifact" % (len(rows),
                                                                 len(warp["pairs"])))
    for a, b, rms, sc, ab in rows:
        consume(rms, sc, ab)
        key = "%s|%s" % (a, b)
        if key not in warp["pairs"]:
            check("row %s vs %s" % (a, b), False, "no such pair in the artifact")
            continue
        w = warp["pairs"][key]
        best = max(w["absorb_iso"], w["absorb_aff"])
        # tolerances are the document's own quantisation, not round numbers: it
        # quotes 2dp of px and 3dp of percent, so half an ulp is the honest bar.
        ok = (abs(num(rms) - w["rms_raw"]) <= 0.006
              and abs(num(sc) - 100 * w["iso_scale"]) <= 0.0006
              and abs(num(ab) - round(100 * best)) < 0.51)
        check("row %s vs %s" % (a, b), ok,
              "doc %.2f px / %+.3f%% / %s%%  artifact %.2f px / %+.3f%% / %.0f%%"
              % (num(rms), num(sc), ab, w["rms_raw"], 100 * w["iso_scale"],
                 100 * best))

    # ---- 2. the determinism control, against the rendered files ---------------
    print("\n2. determinism control vs the files on disk")
    hs = re.findall(r"^    pass([12]) ([0-9A-F]{32})$", doc, re.M)
    check("both passes are quoted", len(hs) == 2, "found %d hash lines" % len(hs))
    if len(hs) == 2:
        d = r"C:\dev\strehl-out\V-H2H2\ladder2\determinism"
        real = {}
        for p in ("pass1", "pass2"):
            r = subprocess.run(["certutil", "-hashfile", os.path.join(d, p + ".tiff"),
                                "MD5"], capture_output=True, text=True)
            real[p] = re.search(r"^([0-9a-f ]{32,})$", r.stdout, re.M).group(1) \
                .replace(" ", "").upper()
        for idx, h in hs:
            p = "pass" + idx
            check("%s hash matches the file" % p, real[p] == h,
                  "doc %s...  file %s..." % (h[:16], real[p][:16]))
        check("the control's claim holds", real["pass1"] == real["pass2"],
              "the two passes are %s"
              % ("byte-identical" if real["pass1"] == real["pass2"] else "DIFFERENT"))

    # ---- 3. the ladder table, against ladder.json -----------------------------
    print("\n3. ladder table vs ladder.json")
    rows = ladder["rows"]
    base = rows[0]
    lr = re.findall(r"^\| (\d+) \| ([\d.]+) px \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| "
                    r"([\d.]+) \|$", doc, re.M)
    check("ladder table has a row per rung", len(lr) == len(rows),
          "%d rows in the document, %d rungs in the artifact" % (len(lr), len(rows)))
    for n, fld, fs, ds, fsh, dsh in lr:
        consume(n, fld, fs, ds, fsh, dsh)
        r = next((q for q in rows if q["n"] == int(n)), None)
        if r is None:
            check("rung %s" % n, False, "no such rung in the artifact")
            continue
        want = (r["field_rms"],
                r["flat.20-60.scene"] / base["flat.20-60.scene"],
                r["detail.20-60.scene"] / base["detail.20-60.scene"],
                r["flat.sharp"] / base["flat.sharp"],
                r["detail.sharp"] / base["detail.sharp"])
        got = tuple(num(v) for v in (fld, fs, ds, fsh, dsh))
        ok = all(close(g, w, 0.0006) for g, w in zip(got, want))
        check("rung %s" % n, ok, "doc %s  artifact %s"
              % (" ".join("%.4f" % g for g in got),
                 " ".join("%.4f" % w for w in want)))

    # ---- 4. the refusal, which is the section's actual result ------------------
    print("\n4. the refusal claim vs the artifact")
    m = re.search(r"5-15 px band at\s+detail sites returned a scene of zero at (\d+)\s+"
                  r"of (\d+) rungs", doc)
    check("the refusal is stated with a count", m is not None,
          "found" if m else "the claim is not in the document in the expected form")
    if m:
        zero = sum(1 for r in rows if r["detail.5-15.scene"] <= 0.0)
        ok = int(m.group(1)) == zero and int(m.group(2)) == len(rows)
        check("refusal count matches the artifact", ok,
              "doc %s of %s, artifact %d of %d"
              % (m.group(1), m.group(2), zero, len(rows)))

    # ---- 5. claims quoted from commissioning, re-run rather than trusted -------
    print("\n5. commissioning claims, re-run")
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "commdecomp.py")],
                       capture_output=True, text=True)
    green = r.stdout.strip().splitlines()[-1]
    check("commissioning is green", r.returncode == 0 and green.startswith("GREEN"),
          "commdecomp.py exit %d, last line %r" % (r.returncode, green[:40]))
    narms = len(re.findall(r"^  (?:PASS|FAIL) ", r.stdout, re.M))
    m = re.search(r"GREEN at (\d+) checks", doc)
    check("check count in the document matches the suite",
          m is not None and int(m.group(1)) == narms,
          "document says %s, suite ran %d" % (m.group(1) if m else "?", narms))
    if m:
        consume(m.group(1))

    # the bound table in 12.2 is quoted from 5f's live output, so read that output
    bt = re.findall(r"^\| r = ([\d.]+) \| ([\d.]+)% \| \+([\d.]+)% \| ([\d.]+)% \| "
                    r"\*\*([\d.]+)%\*\* \|$", doc, re.M)
    live = re.findall(r"r\s+([\d.]+), floor ([\d.]+)%: measured bias ([+-][\d.]+)%"
                      r".*?bound ([\d.]+)%", r.stdout)
    check("bound table has a row per 5f draw set", len(bt) == len(live) and bt != [],
          "%d rows in the document, %d in the suite output" % (len(bt), len(live)))
    for (rr, floor, meas, _old, bound), (lr_r, lf, lm, lb) in zip(bt, live):
        consume(rr, floor, meas, _old, bound)
        ok = (abs(num(rr) - num(lr_r)) <= 0.06
              and abs(num(floor) - num(lf)) <= 0.0006
              and abs(num(meas) - abs(num(lm))) <= 0.0006
              and abs(num(bound) - num(lb)) <= 0.0006)
        check("bound row r = %s" % rr, ok,
              "doc r%s/%s/%s/%s  suite r%s/%s/%s/%s"
              % (rr, floor, meas, bound, lr_r, lf, lm, lb))

    # ---- 6. two more claims that ladder.json can settle, so it should settle them
    print("\n6. remaining artifact-backed claims")
    for label, key in (("flat", "flat"), ("detail", "detail")):
        mm = re.search(r"\*\*([\d.]+)%\*\* at " + label + " sites", doc)
        if mm is None:
            check("worst-case bias, %s sites" % label, False, "claim not found")
            continue
        consume(mm.group(1))
        worst = max(r["%s.%s.nbias" % (key, b)] for r in rows
                    for b in ("5-15", "20-60", "40-120"))
        check("worst-case bias, %s sites" % label,
              close(num(mm.group(1)), 100 * worst, 0.01),
              "doc %s%%  artifact %.3f%%" % (mm.group(1), 100 * worst))
    mm = re.search(r"One display gain, ([\d.]+), derived once", doc)
    if mm:
        consume(mm.group(1))
        check("display gain matches the artifact",
              close(num(mm.group(1)), ladder["expo"], 0.0002),
              "doc %s  artifact %.4f" % (mm.group(1), ladder["expo"]))

    # ---- 7. coverage census: an unchecked number must not read as a checked one
    print("\n7. coverage census")
    # Measured over 12.1-12.7 only. 12.8 quotes the census, and a census that
    # counted its own quotation could never be quoted correctly.
    body = doc[:doc.index("## 12.8")]
    body = re.sub(r"`[^`]*`", "", body)
    body = re.sub(r"^#+ [\d.]+", "", body, flags=re.M)          # section numbers
    body = re.sub(r"\b(?:5-15|20-60|40-120|10-90)\b", "", body)  # band names
    lits = re.findall(r"(?<![\w.])(\d+\.\d+|\d+)(?![\w.])", body)
    uncov = {}
    for v in lits:
        if v not in CONSUMED:
            uncov[v] = uncov.get(v, 0) + 1
    nu = sum(uncov.values())
    print("     %d numeric literals in 12.1-12.7: %d verified against an artifact, "
          "%d NOT COVERED" % (len(lits), len(lits) - nu, nu))
    if uncov:
        print("     not covered: " + ", ".join(sorted(uncov, key=lambda k: -uncov[k])))
    print("     Section 12.2's guard-rebuild numbers come from diag_iqr.py and"
          " diag_tol.py, which are committed and re-runnable but are not re-run here."
          " A plant on one of those WILL survive. That is a gap, not a pass.")
    q = re.search(r"(\d+) numeric literals in 12\.1-12\.7: (\d+) verified against an"
                  r"\s+artifact, (\d+) NOT COVERED", doc)
    check("the census quoted in 12.8 is the census", q is not None
          and (int(q.group(1)), int(q.group(2)), int(q.group(3)))
          == (len(lits), len(lits) - nu, nu),
          "doc %s  live %d/%d/%d"
          % ("/".join(q.groups()) if q else "not found", len(lits), len(lits) - nu, nu))

    print("\n%s  %d checks, %d failed, %d literals uncovered"
          % ("GREEN" if not FAIL else "RED: " + ", ".join(FAIL), NCHECK[0], len(FAIL),
             nu))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
