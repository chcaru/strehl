"""Verifier for docs/research/V-SPEED-HALO.md.

Until now this report had NO verifier. That is the exact shape ORCH flagged in
V-KILLB0: a verdict that lives only in prose, where no mutation can ever catch
it. Six lanes have now found their own harness blind to a reversed conclusion,
so this one is built against that failure specifically:

  * every table row is RE-DERIVED from the committed JSON, not read back from
    the prose;
  * every VERDICT WORD is matched against the verdict the data implies, so
    flipping `specific` to `MANUFACTURED` (or `REFUTED` to `CONFIRMED`) is RED
    even when every digit is left correct;
  * a set of conclusions must be PRESENT (deletion is RED) and a set must be
    ABSENT (re-asserting a visible halo is RED);
  * the commission includes a SPECIFICITY arm -- innocuous prose must score 0.
    Planting a signal and seeing it detected says nothing about whether noise
    is rejected. That was ORCH's lesson and my own detector failed it.

Every claim found is partitioned into certified / reversed / uncertified, and
the three sum to the number found, so a check that was never run cannot be read
as a check that passed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "V-SPEED-HALO.md"
DATA = pathlib.Path(__file__).resolve().parent / "data" / "halo"
if not DATA.exists():  # pre-banking scratch location, kept as a fallback
    DATA = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")

AURA = DATA / "aura-faithful.json"
SPEC = DATA / "plantrim-specificity.json"
PLANT = DATA / "plantrim.json"


def collapse(s: str) -> str:
    """Whitespace-collapse so a claim spanning a line break still matches."""
    return re.sub(r"\s+", " ", s)


def num(s: str) -> float:
    return float(s.replace(",", ""))


# --------------------------------------------------------------------------
# Conclusions that MUST be present. Deleting one is cheaper than stating it
# wrongly, so deletion is commissioned as its own arm.
# --------------------------------------------------------------------------
REQUIRED = [
    ("R1-no-visible-halo",
     r"No \*?\*?visible\*?\*? halo is demonstrated on any of the 26 masters",
     "the corpus-level disposition ORCH established"),
    ("R2-below-floor",
     r"Every excursion this document labels a halo is smaller than\s*that",
     "the amplitudes sit under the ~4500 DN visibility floor"),
    ("R3-arch-confound",
     r"rim_dn.{0,4} \*\*alone is not\s*\*?\*?evidence of a halo",
     "S14.2: the amplitude statistic is arch-confoundable"),
    ("R4-width-saves",
     r"What saves the .4 verdicts is width, and only width",
     "S14.3: the classification survives only because it used width"),
    ("R5-blind-at-ramp",
     r"my own instrument is demonstrably\s*blind",
     "S14.4: the tweezers reading is made where the instrument dies"),
    ("R6-unscored",
     r"UNSCORED rather than clean",
     "residual-risk subjects must never be counted clean"),
    ("R7-no-default",
     r"no surviving\s*justification for a halo fix",
     "S14.6: the fix is not justified and must not ship as a default"),
]

# --------------------------------------------------------------------------
# Conclusions that must be ABSENT. These are the reversals: each one is a
# statement the evidence refutes, and any of them appearing is RED.
# --------------------------------------------------------------------------
FORBIDDEN = [
    ("F1-tweezers-confirmed",
     r"tweezers-cpl[^|\n]*\|\s*\*?\*?CONFIRMED",
     "tweezers was adjudicated a false positive by V-REVIEW"),
    ("F2-dryerase-confirmed",
     r"dry-erase-marker-head-cpl[^|\n]*\|\s*\*?\*?CONFIRMED",
     "dry-erase was adjudicated a false positive by V-REVIEW"),
    ("F3-real-halos",
     r"blind to five real halos|Five real halos",
     "they are sub-visible narrow excursions, not demonstrated halos"),
    ("F4-gradient-manufactures",
     r"monotone gradient (?:does )?manufactures?",
     "measured 0.0 DN at every amplitude; this would reverse S14.1"),
    ("F5-ship-default",
     r"STREHL_HULL[^.]{0,80}(?:as|by) default\b(?![^.]{0,40}not)",
     "the clamp is opt-in and has no surviving justification"),
]


def load(p: pathlib.Path):
    if not p.exists():
        raise SystemExit(f"missing data: {p}")
    return json.loads(p.read_text())


def derive():
    """Re-derive every certifiable row from the JSON the experiments wrote."""
    out = {}

    aura = load(AURA)
    out["aura"] = {r["subject"]: r for r in aura}

    spec = load(SPEC)
    out["spec"] = {}
    for r in spec:
        if r.get("status") != "SCORED":
            continue
        # Re-derive the verdict from the numbers rather than trusting the
        # stored label: an inert plant and a dead instrument look identical.
        if not r["control_live"]:
            v = "VOID"
        elif r["specific"]:
            v = "specific"
        else:
            v = "MANUFACTURED"
        out["spec"][r["bg"]] = dict(r, derived_verdict=v)

    plant = load(PLANT)
    out["hull"] = [r for r in plant.get("hull", []) if r.get("status") == "SCORED"]
    out["sweep"] = [r for r in plant.get("sweep", []) if r.get("status") == "SCORED"]
    return out


def check_spec_table(text: str, d, res):
    """S14's specificity table: numbers AND the verdict word, per row."""
    for bg, r in sorted(d["spec"].items()):
        # e.g. "arch 2879 DN" -> table cell "| arch 2879 |"
        kind, amp, _ = bg.split()
        row = re.search(
            r"\|\s*%s %s\s*\|([^\n]*)\|" % (re.escape(kind), re.escape(amp)),
            text)
        if not row:
            res.append((f"S14-{kind}-{amp}", "uncertified",
                        "row not found in the specificity table"))
            continue
        cells = [c.strip().strip("*") for c in row.group(1).split("|")]
        want_dn = r["false_rim_dn"]
        want_v = r["derived_verdict"]
        got_dn = None
        for c in cells:
            m = re.fullmatch(r"-?[\d.]+", c)
            if m:
                got_dn = num(c)
                break
        if got_dn is None or abs(got_dn - want_dn) > 0.05:
            res.append((f"S14-{kind}-{amp}", "reversed",
                        f"false rim {got_dn} != re-derived {want_dn}"))
            continue
        joined = " ".join(cells)
        if want_v.lower() not in joined.lower():
            res.append((f"S14-{kind}-{amp}", "reversed",
                        f"verdict in doc {joined!r} != re-derived {want_v!r}"))
            continue
        res.append((f"S14-{kind}-{amp}", "certified",
                    f"{want_dn} DN / {want_v}"))


def check_width_separation(text: str, d, res):
    """S14.3's whole argument is a width separation. Certify both ends."""
    manu_w = {r["false_rim_w_px"] for r in d["spec"].values()
              if r["derived_verdict"] == "MANUFACTURED"}
    if len(manu_w) != 1:
        res.append(("S14.3-width", "uncertified",
                    f"manufactured widths not constant: {sorted(manu_w)}"))
        return
    w = manu_w.pop()
    flat = collapse(text)
    if not re.search(r"\*?\*?%s px wide at" % re.escape(f"{w:.1f}"), flat):
        res.append(("S14.3-width", "reversed",
                    f"doc does not state the manufactured width {w:.1f} px"))
        return
    # And the real excursions must be stated as narrower, not wider.
    m = re.search(r"\*?\*?(\d+)[-\u2013](\d+) px wide at", flat)
    if not m or int(m.group(2)) >= w:
        res.append(("S14.3-width", "reversed",
                    "doc does not place the real excursions below the "
                    "manufactured width"))
        return
    res.append(("S14.3-width", "certified",
                f"manufactured {w:.1f} px vs real {m.group(1)}-{m.group(2)} px"))


def check_hull_inert(text: str, d, res):
    rims = [r["rim_dn"] for r in d["hull"]]
    if not rims:
        res.append(("S13-hull", "uncertified", "no scored hull arms"))
        return
    spread = max(rims) - min(rims)
    flat = collapse(text)
    if not re.search(r"hull modes move the rim %s DN" % re.escape(f"{spread:.1f}"), flat):
        res.append(("S13-hull", "reversed",
                    f"doc does not state the re-derived hull spread {spread:.1f} DN"))
        return
    res.append(("S13-hull", "certified", f"hull rim spread {spread:.1f} DN"))


def check_floor(text: str, d, res):
    narrow = [r for r in d["sweep"] if r["shape"] == "narrow" and r["detected"]]
    if not narrow:
        res.append(("S13-floor", "uncertified", "no detected narrow plants"))
        return
    floor = min(r["amp"] for r in narrow)
    flat = collapse(text)
    if not re.search(r"\| \*\*%s DN\*\* \|" % re.escape(f"{floor:.0f}"), flat):
        res.append(("S13-floor", "reversed",
                    f"doc does not state the re-derived narrow floor {floor:.0f} DN"))
        return
    res.append(("S13-floor", "certified", f"narrow detection floor {floor:.0f} DN"))


def check_aura_rows(text: str, d, res):
    """S4's table, re-derived per subject from the faithful scan."""
    for subj, r in sorted(d["aura"].items()):
        if r["verdict"] == "clean":
            continue
        row = re.search(r"\|\s*%s\s*\|([^\n]*)\|" % re.escape(subj), text)
        if not row:
            res.append((f"S4-{subj}", "uncertified", "row not in table"))
            continue
        cells = [c.strip().strip("*") for c in row.group(1).split("|")]
        nums = [num(c) for c in cells if re.fullmatch(r"-?[\d.]+", c)]
        want = [r["aura_dn"], r["rim_dn"]]
        got = [n for n in nums]
        ok = all(any(abs(g - w) <= 0.05 for g in got) for w in want)
        if not ok:
            res.append((f"S4-{subj}", "reversed",
                        f"amplitudes {got} do not contain re-derived {want}"))
            continue
        res.append((f"S4-{subj}", "certified",
                    f"aura {r['aura_dn']} / rim {r['rim_dn']}"))


def verify(doc: pathlib.Path) -> int:
    text = doc.read_text(encoding="utf-8")
    flat = collapse(text)
    d = derive()
    res: list[tuple[str, str, str]] = []

    for cid, pat, why in REQUIRED:
        if re.search(pat, flat, re.I):
            res.append((cid, "certified", why))
        else:
            res.append((cid, "reversed", f"REQUIRED conclusion missing: {why}"))

    for cid, pat, why in FORBIDDEN:
        m = re.search(pat, flat, re.I)
        if m:
            res.append((cid, "reversed",
                        f"FORBIDDEN conclusion present ({m.group(0)[:60]!r}): {why}"))
        else:
            res.append((cid, "certified", f"absent, as required: {why}"))

    check_aura_rows(text, d, res)
    check_spec_table(text, d, res)
    check_width_separation(text, d, res)
    check_hull_inert(text, d, res)
    check_floor(text, d, res)

    cert = [r for r in res if r[1] == "certified"]
    rev = [r for r in res if r[1] == "reversed"]
    unc = [r for r in res if r[1] == "uncertified"]

    for cid, st, msg in res:
        if st != "certified":
            print(f"  [{st.upper():12s}] {cid}: {msg}")

    print(f"\n{len(cert)} certified + {len(rev)} reversed + {len(unc)} uncertified "
          f"= {len(res)} checks")
    if unc:
        print("  (uncertified = the check could not be run; NOT a pass)")

    MIN_CERTIFIED = 30  # measured from the clean document, not guessed
    if rev:
        print("RED: a conclusion in the document contradicts the data.")
        return 1
    if len(cert) < MIN_CERTIFIED:
        print(f"RED: only {len(cert)} certified, need >= {MIN_CERTIFIED}. "
              "The verifier is not seeing the document.")
        return 1
    print("GREEN")
    return 0


# --------------------------------------------------------------------------
# Commission. A verifier nobody has attacked is an assumption.
# --------------------------------------------------------------------------
def commission() -> int:
    """Four arms. Clean must be GREEN, three mutations must be RED, and
    innocuous prose must stay GREEN -- sensitivity AND specificity."""
    text = DOC.read_text(encoding="utf-8")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="haloverify-"))
    backup = tmp / "V-SPEED-HALO.md.orig"
    shutil.copy2(DOC, backup)  # never `git checkout --`
    arms = [
        ("clean", None, 0),
        ("number defect",
         ("| arch 2879 | **2442.2**", "| arch 2879 | **2443.2**"), 1),
        ("conclusion reversal",
         ("gradient 2879 | **0.0** | 0.0 | 36 | 2819.7 | specific",
          "gradient 2879 | **0.0** | 0.0 | 36 | 2819.7 | MANUFACTURED"), 1),
        ("conclusion deletion",
         ("**No *visible* halo is demonstrated on any of the 26 masters.**", ""), 1),
        ("innocuous prose",
         ("## 14. Specificity",
          "## 14. Specificity\n\nThe measurements in this section were run at night.\n"), 0),
    ]
    ok = True
    try:
        for name, mut, want in arms:
            if mut is None:
                body = text
            else:
                old, new = mut
                n = text.count(old)
                if n != 1:
                    print(f"  {name:22s} MUTATION TARGET NOT FOUND "
                          f"(count={n}) -- arm is void, not passing")
                    ok = False
                    continue
                body = text.replace(old, new, 1)
            DOC.write_text(body, encoding="utf-8")
            rc = verify(DOC)
            verdict = "OK" if rc == want else "FAILED"
            if rc != want:
                ok = False
            print(f"  == {name:22s} rc={rc} want={want}  {verdict}\n")
    finally:
        shutil.copy2(backup, DOC)
        shutil.rmtree(tmp, ignore_errors=True)
    restored = DOC.read_text(encoding="utf-8")
    if restored != text:
        print("FATAL: document not restored byte-identically")
        return 1
    print("document restored byte-identically")
    print("COMMISSION PASSED" if ok else "COMMISSION FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()
    if a.commission:
        return commission()
    return verify(DOC)


if __name__ == "__main__":
    sys.exit(main())
